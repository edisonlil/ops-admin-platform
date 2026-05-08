from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ops-admin-test.db"
        self.access_token: str | None = None
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
                "FG_AGENT_DB_PATH": str(self.db_path),
                "FG_AGENT_AUTH_SECRET": "test-secret",
                "FG_AGENT_ADMIN_USERNAME": "admin",
                "FG_AGENT_ADMIN_PASSWORD": "edc3000",
            },
            clear=False,
        )
        self.env_patch.start()

        from identity_access.infrastructure.persistence.common import (
            auth_database_target,
            connect,
            initialize_auth_storage,
        )

        with connect(auth_database_target(), readonly=False) as conn:
            initialize_auth_storage(conn)

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def request(self, method: str, path: str, auth: bool = True, **kwargs: object) -> httpx.Response:
        from api.main import app

        if auth:
            headers = dict(kwargs.pop("headers", {}) or {})
            headers.update(self.auth_headers())
            kwargs["headers"] = headers

        transport = httpx.ASGITransport(app=app)

        async def run_request() -> httpx.Response:
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(run_request())

    def auth_headers(self) -> dict[str, str]:
        if not self.access_token:
            response = self.request(
                "POST",
                "/api/login",
                json={"params": {"tenant_key": "platform", "username": "admin", "password": "edc3000"}},
                auth=False,
            )
            self.assertEqual(response.status_code, 200)
            self.access_token = str(response.json()["data"]["token"])
        return {"Authorization": f"Bearer {self.access_token}"}

    def menu_keys(self, menus: list[dict[str, object]]) -> set[str]:
        keys: set[str] = set()
        for menu in menus:
            keys.add(str(menu.get("key", "")))
            children = menu.get("children")
            if isinstance(children, list):
                keys.update(self.menu_keys(children))
        return keys

    def initialize_llm_db(self) -> None:
        from llm_runtime.infrastructure.persistence.bootstrap import ensure_llm_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_llm_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def initialize_appearance_db(self) -> None:
        from appearance.infrastructure.persistence.bootstrap import ensure_appearance_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_appearance_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def test_database_url_can_come_from_config_file(self) -> None:
        from api.config import resolve_database_url

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "database.json"
            config_path.write_text(
                json.dumps({"database_url": "postgresql://user:pass@example.supabase.co:6543/postgres"}),
                encoding="utf-8",
            )
            with mock.patch.dict(
                "os.environ",
                {
                    "FG_AGENT_DATABASE_CONFIG": str(config_path),
                    "FG_AGENT_DATABASE_URL": "",
                    "SUPABASE_DB_URL": "",
                    "DATABASE_URL": "",
                },
                clear=False,
            ):
                self.assertEqual(
                    resolve_database_url(),
                    "postgresql://user:pass@example.supabase.co:6543/postgres",
                )

    def test_db_path_can_come_from_config_file(self) -> None:
        from api.config import resolve_db_path

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "configured.db"
            config_path = Path(temp_dir) / "database.json"
            config_path.write_text(json.dumps({"db_path": str(db_path)}), encoding="utf-8")
            with mock.patch.dict(
                "os.environ",
                {
                    "FG_AGENT_DATABASE_CONFIG": str(config_path),
                    "FG_AGENT_DB_PATH": "",
                },
                clear=False,
            ):
                self.assertEqual(resolve_db_path(), db_path)

    def test_health_is_public(self) -> None:
        response = self.request("GET", "/api/health", auth=False)

        self.assertIn(response.status_code, {200, 503})

    def test_platform_admin_can_login_and_read_current_user(self) -> None:
        response = self.request(
            "POST",
            "/api/login",
            json={"params": {"tenant_key": "platform", "username": "admin", "password": "edc3000"}},
            auth=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["username"], "admin")
        self.assertEqual(response.json()["data"]["auth_scope"], "platform")
        self.assertIn("tenant-management", self.menu_keys(response.json()["data"]["menus"]))
        self.assertNotIn("function-points", self.menu_keys(response.json()["data"]["menus"]))

        token = response.json()["data"]["token"]
        me_response = self.request("GET", "/api/auth/me", headers={"Authorization": f"Bearer {token}"}, auth=False)

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["username"], "admin")
        self.assertTrue(me_response.json()["is_platform_admin"])

    def test_business_endpoints_require_auth(self) -> None:
        response = self.request("GET", "/api/tenants", auth=False)

        self.assertEqual(response.status_code, 401)

    def test_login_does_not_initialize_identity_storage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            uninitialized_db = Path(temp_dir) / "auth.db"
            with mock.patch.dict("os.environ", {"FG_AGENT_DB_PATH": str(uninitialized_db)}, clear=False):
                response = self.request(
                    "POST",
                    "/api/login",
                    json={"params": {"tenant_key": "platform", "username": "admin", "password": "edc3000"}},
                    auth=False,
                )

        self.assertEqual(response.status_code, 503)
        self.assertIn("identity storage is not initialized", response.json()["message"])

    def test_admin_can_read_seeded_rbac_catalogs(self) -> None:
        menu_response = self.request("GET", "/api/rbac/menus")
        role_response = self.request("GET", "/api/rbac/roles")
        permission_response = self.request("GET", "/api/rbac/permissions")

        self.assertEqual(menu_response.status_code, 200)
        self.assertEqual(role_response.status_code, 200)
        self.assertEqual(permission_response.status_code, 200)

        menu_keys = {item["key"] for item in menu_response.json()["items"]}
        self.assertIn("tenant-management", menu_keys)
        self.assertIn("appearance-studio", menu_keys)
        self.assertIn("llm-debug", menu_keys)
        self.assertNotIn("recommend", menu_keys)
        self.assertNotIn("function-points", menu_keys)

        self.assertTrue(any(item["key"] == "admin" for item in role_response.json()["items"]))
        self.assertTrue(any(item["code"] == "system:menu:access" for item in permission_response.json()["items"]))

    def test_tenant_admin_sees_only_tenant_menus(self) -> None:
        tenant_response = self.request("POST", "/api/tenants", json={"key": "tenant-c", "name": "Tenant C"})
        self.assertEqual(tenant_response.status_code, 200)
        tenant_id = int(tenant_response.json()["data"]["item"]["id"])

        create_response = self.request(
            "POST",
            f"/api/tenants/{tenant_id}/users",
            json={
                "username": "owner",
                "password": "tenant-c-pass",
                "role_keys": ["tenant-admin"],
                "is_active": True,
                "is_superuser": False,
                "is_tenant_admin": True,
            },
        )
        self.assertEqual(create_response.status_code, 200)

        login_response = self.request(
            "POST",
            "/api/login",
            json={"params": {"tenant_key": "tenant-c", "username": "owner", "password": "tenant-c-pass"}},
            auth=False,
        )

        self.assertEqual(login_response.status_code, 200)
        keys = self.menu_keys(login_response.json()["data"]["menus"])
        self.assertIn("tenant-settings", keys)
        self.assertIn("tenant-api-keys", keys)
        self.assertIn("llm-config", keys)
        self.assertNotIn("tenant-management", keys)
        self.assertNotIn("rbac", keys)
        self.assertNotIn("function-points", keys)

    def test_admin_can_create_update_and_delete_menu(self) -> None:
        create_response = self.request(
            "POST",
            "/api/rbac/menus",
            json={
                "key": "reports",
                "label": "Reports",
                "menu_type": "page",
                "path": "/reports",
                "route_name": "reports",
                "component": "/platform/index",
                "icon": "DashboardOutlined",
                "parent_key": "",
                "permission_code": "reports:access",
                "sort_order": 200,
                "is_visible": True,
            },
        )
        self.assertEqual(create_response.status_code, 200)
        menu_id = create_response.json()["item"]["id"]

        update_response = self.request(
            "PUT",
            f"/api/rbac/menus/{menu_id}",
            json={
                "key": "reports",
                "label": "Reports Updated",
                "menu_type": "page",
                "path": "/reports",
                "route_name": "reports",
                "component": "/platform/index",
                "icon": "DashboardOutlined",
                "parent_key": "",
                "permission_code": "reports:access",
                "sort_order": 201,
                "is_visible": True,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["item"]["label"], "Reports Updated")

        delete_response = self.request("DELETE", f"/api/rbac/menus/{menu_id}")
        self.assertEqual(delete_response.status_code, 200)

    def test_llm_config_requires_explicit_schema_initialization(self) -> None:
        uninitialized_response = self.request("GET", "/api/llm/providers")
        self.assertEqual(uninitialized_response.status_code, 503)

        self.initialize_llm_db()
        initialized_response = self.request("GET", "/api/llm/providers")
        self.assertEqual(initialized_response.status_code, 200)

    def test_appearance_requires_explicit_schema_initialization(self) -> None:
        uninitialized_response = self.request("GET", "/api/appearance/platform-branding")
        self.assertEqual(uninitialized_response.status_code, 503)

        self.initialize_appearance_db()
        initialized_response = self.request("GET", "/api/appearance/platform-branding")
        self.assertEqual(initialized_response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
