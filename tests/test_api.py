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

    def initialize_messaging_db(self) -> None:
        from messaging.infrastructure.persistence.bootstrap import ensure_messaging_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_messaging_schema(conn)
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

    def test_default_database_path_resolves_to_project_root(self) -> None:
        from api.config import resolve_db_path as resolve_system_db_path
        from identity_access.infrastructure.config import resolve_db_path as resolve_identity_db_path

        with mock.patch.dict(
            "os.environ",
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "FG_AGENT_DB_PATH": "",
            },
            clear=False,
        ):
            self.assertEqual(resolve_system_db_path(), Path.cwd() / "ops_admin.db")
            self.assertEqual(resolve_identity_db_path(), Path.cwd() / "ops_admin.db")

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
        self.assertEqual(me_response.json()["data"]["username"], "admin")
        self.assertTrue(me_response.json()["data"]["is_platform_admin"])

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

        menu_keys = {item["key"] for item in menu_response.json()["data"]["items"]}
        self.assertIn("tenant-management", menu_keys)
        self.assertIn("appearance-studio", menu_keys)
        self.assertIn("llm-debug", menu_keys)
        self.assertNotIn("recommend", menu_keys)
        self.assertNotIn("function-points", menu_keys)

        self.assertTrue(any(item["key"] == "admin" for item in role_response.json()["data"]["items"]))
        self.assertTrue(any(item["code"] == "system:menu:access" for item in permission_response.json()["data"]["items"]))

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
        self.assertIn("message-templates", keys)
        self.assertIn("message-channels", keys)
        self.assertNotIn("message-templates-enable", keys)
        permissions = {item["value"] for item in login_response.json()["data"]["permissions"]}
        self.assertIn("messaging:templates:enable", permissions)
        self.assertIn("messaging:channels:test", permissions)
        self.assertIn("llm-config", keys)
        self.assertNotIn("tenant-management", keys)
        self.assertNotIn("rbac", keys)
        self.assertNotIn("function-points", keys)

    def test_tenant_admin_can_revoke_current_tenant_api_key(self) -> None:
        tenant_response = self.request("POST", "/api/tenants", json={"key": "tenant-key", "name": "Tenant Key"})
        self.assertEqual(tenant_response.status_code, 200)
        tenant_id = int(tenant_response.json()["data"]["item"]["id"])

        create_user_response = self.request(
            "POST",
            f"/api/tenants/{tenant_id}/users",
            json={
                "username": "key-owner",
                "password": "tenant-key-pass",
                "role_keys": ["tenant-admin"],
                "is_active": True,
                "is_superuser": False,
            },
        )
        self.assertEqual(create_user_response.status_code, 200)

        login_response = self.request(
            "POST",
            "/api/login",
            json={"params": {"tenant_key": "tenant-key", "username": "key-owner", "password": "tenant-key-pass"}},
            auth=False,
        )
        self.assertEqual(login_response.status_code, 200)
        tenant_headers = {"Authorization": f"Bearer {login_response.json()['data']['token']}"}

        create_key_response = self.request(
            "POST",
            "/api/tenant/api-keys",
            json={"name": "test-key"},
            headers=tenant_headers,
            auth=False,
        )
        self.assertEqual(create_key_response.status_code, 200)
        key_id = int(create_key_response.json()["data"]["item"]["id"])

        revoke_response = self.request(
            "DELETE",
            f"/api/tenant/api-keys/{key_id}",
            headers=tenant_headers,
            auth=False,
        )

        self.assertEqual(revoke_response.status_code, 200)
        self.assertTrue(revoke_response.json()["success"])
        self.assertEqual(revoke_response.json()["data"]["id"], key_id)
        self.assertFalse(revoke_response.json()["data"]["is_active"])

        list_response = self.request("GET", "/api/tenant/api-keys", headers=tenant_headers, auth=False)
        self.assertEqual(list_response.status_code, 200)
        self.assertNotIn(key_id, {int(item["id"]) for item in list_response.json()["data"]["items"]})

    def test_tenant_admin_flag_follows_tenant_admin_role(self) -> None:
        tenant_response = self.request("POST", "/api/tenants", json={"key": "role-derived", "name": "Role Derived"})
        self.assertEqual(tenant_response.status_code, 200)
        tenant_id = int(tenant_response.json()["data"]["item"]["id"])

        create_user_response = self.request(
            "POST",
            f"/api/tenants/{tenant_id}/users",
            json={
                "username": "role-owner",
                "password": "role-owner-pass",
                "role_keys": ["tenant-admin"],
                "is_active": True,
                "is_superuser": False,
            },
        )
        self.assertEqual(create_user_response.status_code, 200)
        created_user = create_user_response.json()["data"]["item"]
        self.assertTrue(created_user["is_tenant_admin"])

        update_user_response = self.request(
            "PUT",
            f"/api/tenants/{tenant_id}/users/{created_user['id']}",
            json={
                "username": "role-owner",
                "password": "",
                "role_keys": [],
                "is_active": True,
                "is_superuser": False,
            },
        )
        self.assertEqual(update_user_response.status_code, 200)
        self.assertFalse(update_user_response.json()["data"]["item"]["is_tenant_admin"])

    def test_identity_initialization_repairs_tenant_admin_llm_update_permission(self) -> None:
        from identity_access.infrastructure.persistence.common import auth_database_target, connect, initialize_auth_storage

        with connect(auth_database_target(), readonly=False) as conn:
            conn.execute(
                """
                DELETE FROM role_permissions
                WHERE role_id = (SELECT id FROM roles WHERE role_key = ?)
                  AND permission_id = (SELECT id FROM permissions WHERE code = ?)
                """,
                ("tenant-admin", "llm_config:update"),
            )

            missing = conn.execute(
                """
                SELECT 1
                FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.role_key = ? AND p.code = ?
                """,
                ("tenant-admin", "llm_config:update"),
            ).fetchone()
            self.assertIsNone(missing)

            initialize_auth_storage(conn)

            repaired = conn.execute(
                """
                SELECT 1
                FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.role_key = ? AND p.code = ?
                """,
                ("tenant-admin", "llm_config:update"),
            ).fetchone()

        self.assertIsNotNone(repaired)

    def test_identity_initialization_repairs_tenant_admin_messaging_menus(self) -> None:
        from identity_access.infrastructure.persistence.common import auth_database_target, connect, initialize_auth_storage

        with connect(auth_database_target(), readonly=False) as conn:
            conn.execute(
                """
                DELETE FROM role_menus
                WHERE role_id = (SELECT id FROM roles WHERE role_key = ?)
                  AND menu_id IN (
                      SELECT id FROM menus WHERE menu_key IN (?, ?)
                  )
                """,
                ("tenant-admin", "message-templates", "message-channels"),
            )

            missing = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM role_menus rm
                JOIN roles r ON r.id = rm.role_id
                JOIN menus m ON m.id = rm.menu_id
                WHERE r.role_key = ?
                  AND m.menu_key IN (?, ?)
                """,
                ("tenant-admin", "message-templates", "message-channels"),
            ).fetchone()
            self.assertEqual(int(missing["total"]), 0)

            initialize_auth_storage(conn)

            repaired = conn.execute(
                """
                SELECT m.menu_key
                FROM role_menus rm
                JOIN roles r ON r.id = rm.role_id
                JOIN menus m ON m.id = rm.menu_id
                WHERE r.role_key = ?
                  AND m.menu_key IN (?, ?)
                ORDER BY m.menu_key
                """,
                ("tenant-admin", "message-templates", "message-channels"),
            ).fetchall()

        self.assertEqual({row["menu_key"] for row in repaired}, {"message-channels", "message-templates"})

    def test_identity_initialization_repairs_tenant_admin_messaging_action_permissions(self) -> None:
        from identity_access.infrastructure.persistence.common import auth_database_target, connect, initialize_auth_storage

        with connect(auth_database_target(), readonly=False) as conn:
            conn.execute(
                """
                DELETE FROM role_permissions
                WHERE role_id = (SELECT id FROM roles WHERE role_key = ?)
                  AND permission_id = (SELECT id FROM permissions WHERE code = ?)
                """,
                ("tenant-admin", "messaging:templates:enable"),
            )

            missing = conn.execute(
                """
                SELECT 1
                FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.role_key = ? AND p.code = ?
                """,
                ("tenant-admin", "messaging:templates:enable"),
            ).fetchone()
            self.assertIsNone(missing)

            initialize_auth_storage(conn)

            repaired = conn.execute(
                """
                SELECT 1
                FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.role_key = ? AND p.code = ?
                """,
                ("tenant-admin", "messaging:templates:enable"),
            ).fetchone()

        self.assertIsNotNone(repaired)

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
        menu_id = create_response.json()["data"]["item"]["id"]

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
        self.assertEqual(update_response.json()["data"]["item"]["label"], "Reports Updated")

        delete_response = self.request("DELETE", f"/api/rbac/menus/{menu_id}")
        self.assertEqual(delete_response.status_code, 200)

    def test_admin_can_create_action_permission_under_page(self) -> None:
        page_response = self.request(
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
                "permission_code": "reports:view",
                "sort_order": 200,
                "is_visible": True,
            },
        )
        self.assertEqual(page_response.status_code, 200)

        action_response = self.request(
            "POST",
            "/api/rbac/menus",
            json={
                "key": "reports-export",
                "label": "Export reports",
                "menu_type": "action",
                "path": "",
                "route_name": "",
                "component": "",
                "icon": "",
                "parent_key": "reports",
                "permission_code": "reports:export",
                "sort_order": 201,
                "is_visible": True,
            },
        )
        self.assertEqual(action_response.status_code, 200)
        item = action_response.json()["data"]["item"]
        self.assertEqual(item["menu_type"], "action")
        self.assertEqual(item["permission_code"], "reports:export")

        role_response = self.request(
            "POST",
            "/api/rbac/roles",
            json={
                "key": "report-exporter",
                "name": "Report Exporter",
                "description": "",
                "menu_keys": ["reports-export"],
            },
        )
        self.assertEqual(role_response.status_code, 200)
        role = role_response.json()["data"]["item"]
        menu_keys = {item["key"] for item in role["menus"]}
        permission_codes = {item["code"] for item in role["permissions"]}
        self.assertIn("reports", menu_keys)
        self.assertIn("reports-export", menu_keys)
        self.assertIn("reports:view", permission_codes)
        self.assertIn("reports:export", permission_codes)

    def test_admin_can_create_tenant_role_with_tenant_action_permissions(self) -> None:
        role_response = self.request(
            "POST",
            "/api/rbac/roles",
            json={
                "key": "tenant-member-operator",
                "name": "Tenant Member Operator",
                "description": "",
                "role_scope": "tenant",
                "menu_keys": ["tenant-users-create"],
            },
        )

        self.assertEqual(role_response.status_code, 200)
        role = role_response.json()["data"]["item"]
        self.assertEqual(role["role_scope"], "tenant")
        menu_keys = {item["key"] for item in role["menus"]}
        permission_codes = {item["code"] for item in role["permissions"]}
        self.assertIn("tenant-settings", menu_keys)
        self.assertIn("tenant-user-management", menu_keys)
        self.assertIn("tenant-users-create", menu_keys)
        self.assertIn("tenant:user:manage", permission_codes)
        self.assertIn("tenant:users:create", permission_codes)

    def test_llm_config_requires_explicit_schema_initialization(self) -> None:
        uninitialized_response = self.request("GET", "/api/llm/providers")
        self.assertEqual(uninitialized_response.status_code, 503)

        self.initialize_llm_db()
        initialized_response = self.request("GET", "/api/llm/providers")
        self.assertEqual(initialized_response.status_code, 200)

    def test_appearance_requires_explicit_schema_initialization(self) -> None:
        uninitialized_response = self.request("GET", "/api/appearance/platform-branding")
        self.assertEqual(uninitialized_response.status_code, 503)
        uninitialized_theme_response = self.request("GET", "/api/appearance/platform-theme", auth=False)
        self.assertEqual(uninitialized_theme_response.status_code, 503)

        self.initialize_appearance_db()
        initialized_response = self.request("GET", "/api/appearance/platform-branding")
        self.assertEqual(initialized_response.status_code, 200)
        initialized_theme_response = self.request("GET", "/api/appearance/platform-theme", auth=False)
        self.assertEqual(initialized_theme_response.status_code, 200)
        self.assertEqual(initialized_theme_response.json()["data"]["source"], "builtin")

    def test_messaging_requires_explicit_schema_initialization(self) -> None:
        uninitialized_response = self.request("GET", "/api/messaging/inbox")

        self.assertEqual(uninitialized_response.status_code, 503)
        self.assertIn("messaging storage is not initialized", uninitialized_response.json()["message"])

    def test_admin_can_send_and_read_in_app_message(self) -> None:
        self.initialize_messaging_db()
        me_response = self.request("GET", "/api/auth/me")
        self.assertEqual(me_response.status_code, 200)
        user_id = int(me_response.json()["data"]["id"])

        send_response = self.request(
            "POST",
            "/api/messaging/messages/send",
            json={
                "title": "Maintenance notice",
                "content": "The platform will be updated tonight.",
                "recipient_user_ids": [user_id],
                "message_type": "system",
                "priority": "normal",
            },
        )
        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(send_response.json()["data"]["item"]["title"], "Maintenance notice")

        unread_response = self.request("GET", "/api/messaging/inbox/unread-count")
        self.assertEqual(unread_response.status_code, 200)
        self.assertEqual(unread_response.json()["data"]["count"], 1)

        inbox_response = self.request("GET", "/api/messaging/inbox")
        self.assertEqual(inbox_response.status_code, 200)
        items = inbox_response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Maintenance notice")
        self.assertEqual(items[0]["read_status"], "unread")

        mark_response = self.request("POST", f"/api/messaging/inbox/{items[0]['id']}/read")
        self.assertEqual(mark_response.status_code, 200)
        self.assertEqual(mark_response.json()["data"]["item"]["read_status"], "read")

        unread_after_response = self.request("GET", "/api/messaging/inbox/unread-count")
        self.assertEqual(unread_after_response.status_code, 200)
        self.assertEqual(unread_after_response.json()["data"]["count"], 0)

    def test_admin_can_manage_message_templates_and_channels(self) -> None:
        self.initialize_messaging_db()

        template_response = self.request(
            "POST",
            "/api/messaging/templates",
            json={
                "template_key": "maintenance_notice",
                "name": "Maintenance notice",
                "description": "Planned maintenance notification",
                "channels": ["in_app"],
                "title_template": "Maintenance: {{window}}",
                "content_template": "The platform will be updated at {{window}}.",
                "variables_schema": {"window": {"type": "string"}},
                "status": "draft",
            },
        )
        self.assertEqual(template_response.status_code, 200)
        template = template_response.json()["data"]["item"]
        self.assertEqual(template["template_key"], "maintenance_notice")

        enable_response = self.request("POST", f"/api/messaging/templates/{template['id']}/enable")
        self.assertEqual(enable_response.status_code, 200)
        self.assertEqual(enable_response.json()["data"]["item"]["status"], "enabled")

        templates_response = self.request("GET", "/api/messaging/templates")
        self.assertEqual(templates_response.status_code, 200)
        self.assertEqual(len(templates_response.json()["data"]["items"]), 1)

        account_response = self.request(
            "POST",
            "/api/messaging/channel-accounts",
            json={
                "channel": "in_app",
                "name": "Default in-app channel",
                "config": {"visible": True},
                "enabled": True,
                "is_default": True,
            },
        )
        self.assertEqual(account_response.status_code, 200)
        account = account_response.json()["data"]["item"]
        self.assertEqual(account["channel"], "in_app")

        test_response = self.request("POST", f"/api/messaging/channel-accounts/{account['id']}/test")
        self.assertEqual(test_response.status_code, 200)
        self.assertTrue(test_response.json()["data"]["ok"])

        preferences_response = self.request(
            "PUT",
            "/api/messaging/preferences",
            json={"items": [{"message_type": "system", "channels": ["in_app"], "enabled": True}]},
        )
        self.assertEqual(preferences_response.status_code, 200)
        self.assertEqual(preferences_response.json()["data"]["items"][0]["message_type"], "system")

    def test_message_template_enable_requires_action_permission(self) -> None:
        self.initialize_messaging_db()

        template_response = self.request(
            "POST",
            "/api/messaging/templates",
            json={
                "template_key": "readonly_notice",
                "name": "Readonly notice",
                "description": "",
                "channels": ["in_app"],
                "title_template": "Notice",
                "content_template": "Content",
                "variables_schema": {},
                "status": "draft",
            },
        )
        self.assertEqual(template_response.status_code, 200)
        template_id = int(template_response.json()["data"]["item"]["id"])

        from identity_access.infrastructure.persistence.common import auth_database_target, connect
        from identity_access.infrastructure.persistence.rbac_repository import sync_role_access

        with connect(auth_database_target(), readonly=False) as conn:
            cursor = conn.execute(
                """
                INSERT INTO roles (role_key, name, description, is_system, role_scope)
                VALUES (?, ?, ?, FALSE, 'tenant')
                """,
                ("template-reader", "Template Reader", ""),
            )
            role_id = int(getattr(cursor, "lastrowid", 0) or 0)
            sync_role_access(conn, role_id, ["message-templates"])

        tenant_response = self.request("POST", "/api/tenants", json={"key": "template-read", "name": "Template Read"})
        self.assertEqual(tenant_response.status_code, 200)
        tenant_id = int(tenant_response.json()["data"]["item"]["id"])

        create_user_response = self.request(
            "POST",
            f"/api/tenants/{tenant_id}/users",
            json={
                "username": "reader",
                "password": "reader-pass",
                "role_keys": ["template-reader"],
                "is_active": True,
                "is_superuser": False,
                "is_tenant_admin": False,
            },
        )
        self.assertEqual(create_user_response.status_code, 200)

        login_response = self.request(
            "POST",
            "/api/login",
            json={"params": {"tenant_key": "template-read", "username": "reader", "password": "reader-pass"}},
            auth=False,
        )
        self.assertEqual(login_response.status_code, 200)
        headers = {"Authorization": f"Bearer {login_response.json()['data']['token']}"}

        list_response = self.request("GET", "/api/messaging/templates", headers=headers, auth=False)
        self.assertEqual(list_response.status_code, 200)

        enable_response = self.request(
            "POST",
            f"/api/messaging/templates/{template_id}/enable",
            headers=headers,
            auth=False,
        )
        self.assertEqual(enable_response.status_code, 403)

    def test_admin_can_render_and_send_message_template(self) -> None:
        self.initialize_messaging_db()
        me_response = self.request("GET", "/api/auth/me")
        self.assertEqual(me_response.status_code, 200)
        user_id = int(me_response.json()["data"]["id"])

        template_response = self.request(
            "POST",
            "/api/messaging/templates",
            json={
                "template_key": "release_notice",
                "name": "发布通知",
                "description": "版本发布消息",
                "channels": ["in_app", "email"],
                "title_template": "{{version}} 发布完成",
                "content_template": "版本 {{version}} 已在 {{time}} 发布。",
                "variables_schema": {"version": {"type": "string"}, "time": {"type": "string"}},
                "status": "enabled",
            },
        )
        self.assertEqual(template_response.status_code, 200)

        render_response = self.request(
            "POST",
            "/api/messaging/templates/render",
            json={"template_key": "release_notice", "variables": {"version": "v1.2.0", "time": "今晚 20:00"}},
        )
        self.assertEqual(render_response.status_code, 200)
        self.assertEqual(render_response.json()["data"]["rendered"]["title"], "v1.2.0 发布完成")
        self.assertEqual(render_response.json()["data"]["missing_variables"], [])

        send_response = self.request(
            "POST",
            "/api/messaging/messages/send-template",
            json={
                "template_key": "release_notice",
                "variables": {"version": "v1.2.0", "time": "今晚 20:00"},
                "recipient_user_ids": [user_id],
                "message_type": "system",
                "priority": "high",
            },
        )
        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(send_response.json()["data"]["item"]["title"], "v1.2.0 发布完成")
        self.assertEqual(send_response.json()["data"]["channels"], ["in_app", "email"])

        inbox_response = self.request("GET", "/api/messaging/inbox")
        self.assertEqual(inbox_response.status_code, 200)
        item = inbox_response.json()["data"]["items"][0]
        self.assertEqual(item["title"], "v1.2.0 发布完成")
        self.assertEqual(item["delivery_summary"]["in_app"], "sent")
        self.assertEqual(item["delivery_summary"]["email"], "pending")


if __name__ == "__main__":
    unittest.main()
