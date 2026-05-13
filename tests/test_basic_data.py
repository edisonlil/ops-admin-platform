from __future__ import annotations

import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx


class BasicDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ops-admin-basic-data-test.db"
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
        self.current_user = {
            "id": 1,
            "username": "admin",
            "tenant_id": 1,
            "current_tenant": {"id": 1, "tenant_key": "platform"},
            "is_platform_admin": True,
            "permissions": ["basic-data:dictionary:read", "basic-data:dictionary:manage"],
        }
        self.access_token: str | None = None
        self.initialize_identity_db()
        self.initialize_basic_data_db()
        self.configure_basic_data_repository()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize_identity_db(self) -> None:
        from identity_access.infrastructure.persistence.common import auth_database_target, connect, initialize_auth_storage

        with connect(auth_database_target(), readonly=False) as conn:
            initialize_auth_storage(conn)

    def initialize_basic_data_db(self) -> None:
        from basic_data.infrastructure.persistence.bootstrap import ensure_basic_data_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_basic_data_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def configure_basic_data_repository(self) -> None:
        from basic_data.application.services import configure_repository
        from basic_data.infrastructure.persistence import repositories

        configure_repository(repositories)

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

    def test_dictionary_service_crud_and_active_lookup(self) -> None:
        from basic_data.application import services

        saved_type = services.save_dictionary_type(
            {
                "code": "customer_level",
                "name": "客户等级",
                "category": "crm",
                "description": "客户等级字典",
                "sort_order": 10,
            },
            self.current_user,
        )["item"]
        self.assertEqual(saved_type["code"], "customer_level")
        child_type = services.save_dictionary_type(
            {
                "parent_id": int(saved_type["id"]),
                "code": "customer_level_child",
                "name": "客户等级子分类",
                "category": "crm",
            },
            self.current_user,
        )["item"]
        self.assertEqual(child_type["parent_id"], saved_type["id"])

        gold = services.save_dictionary_item(
            int(saved_type["id"]),
            {
                "code": "gold",
                "value": "G",
                "label": "金牌",
                "color": "success",
                "extra": {"score": 90},
                "sort_order": 1,
            },
            self.current_user,
        )["item"]
        silver = services.save_dictionary_item(
            int(saved_type["id"]),
            {
                "code": "silver",
                "value": "S",
                "label": "银牌",
                "status": "disabled",
                "sort_order": 2,
            },
            self.current_user,
        )["item"]

        page = services.list_dictionary_types(page=1, page_size=20, keyword="客户", status=None, category="", current_user=self.current_user)
        self.assertEqual(page["pagination"]["total"], 2)
        items = services.list_dictionary_items(type_id=int(saved_type["id"]), page=1, page_size=20, keyword="", status=None, current_user=self.current_user)
        self.assertEqual(items["pagination"]["total"], 2)
        silver_item = next(item for item in items["items"] if item["code"] == "silver")
        self.assertNotIn("parent_id", silver_item)

        active = services.list_items_by_type_code(type_code="customer_level", active_only=True, current_user=self.current_user)
        self.assertEqual([item["code"] for item in active["items"]], ["gold"])
        self.assertEqual(gold["extra"], {"score": 90})

        deleted = services.delete_dictionary_item(item_id=int(silver["id"]), current_user=self.current_user)
        self.assertTrue(deleted["deleted"])
        recreated_silver = services.save_dictionary_item(
            int(saved_type["id"]),
            {
                "code": "silver",
                "value": "S2",
                "label": "银牌复建",
                "sort_order": 3,
            },
            self.current_user,
        )["item"]
        deleted_recreated = services.delete_dictionary_item(item_id=int(recreated_silver["id"]), current_user=self.current_user)
        self.assertTrue(deleted_recreated["deleted"])

        services.save_dictionary_item(
            int(child_type["id"]),
            {"code": "child", "value": "C", "label": "子分类项"},
            self.current_user,
        )
        deleted_type = services.delete_dictionary_type(type_id=int(saved_type["id"]), current_user=self.current_user)
        self.assertTrue(deleted_type["deleted"])
        remaining_types = services.list_dictionary_types(page=1, page_size=20, keyword="", status=None, category="", current_user=self.current_user)
        self.assertEqual(remaining_types["pagination"]["total"], 0)
        recreated_type = services.save_dictionary_type(
            {
                "code": "customer_level",
                "name": "Customer Level Recreated",
                "category": "crm",
            },
            self.current_user,
        )["item"]
        deleted_recreated_type = services.delete_dictionary_type(type_id=int(recreated_type["id"]), current_user=self.current_user)
        self.assertTrue(deleted_recreated_type["deleted"])

    def test_dictionary_service_filters_by_tenant(self) -> None:
        from basic_data.application import services

        services.save_dictionary_type({"code": "order_status", "name": "订单状态"}, self.current_user)
        other_user = {**self.current_user, "tenant_id": 2, "current_tenant": {"id": 2, "tenant_key": "demo"}}
        page = services.list_dictionary_types(page=1, page_size=20, keyword="", status=None, category="", current_user=other_user)

        self.assertEqual(page["pagination"]["total"], 0)

    def test_http_envelope_and_pagination(self) -> None:
        create_response = self.request(
            "POST",
            "/api/basic-data/dictionary-types",
            json={"code": "invoice_status", "name": "发票状态"},
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertTrue(create_response.json()["success"])

        list_response = self.request("GET", "/api/basic-data/dictionary-types?page=1&page_size=20")
        payload = list_response.json()
        self.assertTrue(payload["success"])
        self.assertIn("items", payload["data"])
        self.assertEqual(payload["data"]["pagination"]["total"], 1)

        null_status_response = self.request("GET", "/api/basic-data/dictionary-types?page=1&page_size=20&status=null")
        null_status_payload = null_status_response.json()
        self.assertTrue(null_status_payload["success"])
        self.assertEqual(null_status_payload["data"]["pagination"]["total"], 1)

        duplicate_response = self.request(
            "POST",
            "/api/basic-data/dictionary-types",
            json={"code": "invoice_status", "name": "Invoice Status Duplicate"},
        )
        self.assertEqual(duplicate_response.status_code, 400)
        duplicate_payload = duplicate_response.json()
        self.assertFalse(duplicate_payload["success"])
        self.assertEqual(duplicate_payload["code"], "BASIC_DATA_VALIDATION_ERROR")

    def test_missing_schema_returns_operational_error(self) -> None:
        from basic_data.infrastructure.persistence.bootstrap import require_basic_data_schema

        conn = sqlite3.connect(":memory:")
        try:
            with self.assertRaisesRegex(RuntimeError, "init_basic_data.py"):
                require_basic_data_schema(conn)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
