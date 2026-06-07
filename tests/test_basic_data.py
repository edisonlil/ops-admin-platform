from __future__ import annotations

import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from authorization.domain.models import DataAccessPolicy

from system.application.data_access import (
    DataAccessPredicate,
    ResourceDescriptor,
    TenantOnlyDataAccessFilterProvider,
    configure_data_access_filter_provider,
)


class SelfOnlyProvider:
    def resolve_filter(self, *, current_user: dict[str, object], resource: ResourceDescriptor, action: str) -> DataAccessPredicate:
        current = current_user.get("current_tenant") if isinstance(current_user.get("current_tenant"), dict) else {}
        tenant_id = int((current or {}).get("id") or current_user.get("tenant_id") or 0)
        return DataAccessPredicate(tenant_id=tenant_id, scope="self", user_id=int(current_user.get("id") or 0))


class EmptyAuthorizationRepository:
    def list_data_access_policies(self, **_kwargs: object) -> list[object]:
        return []


class StaticAuthorizationRepository:
    def __init__(self, policies: list[DataAccessPolicy]) -> None:
        self.policies = policies

    def list_data_access_policies(self, *, tenant_id: int, resource_key: str | None = None, **_kwargs: object) -> list[DataAccessPolicy]:
        return [
            item
            for item in self.policies
            if item.tenant_id == tenant_id and (resource_key is None or item.resource_key == resource_key)
        ]


class BasicDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ops-admin-basic-data-test.db"
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "OPS_ADMIN_APPLICATION_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-application.json"),
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
            "permissions": [
                "basic-data:dictionary:read",
                "basic-data:dictionary:manage",
                "basic-data:dictionary:import",
                "basic-data:dictionary:export",
                "basic-data:region:read",
                "basic-data:region:manage",
                "basic-data:region:import",
            ],
        }
        self.access_token: str | None = None
        self.initialize_identity_db()
        self.initialize_basic_data_db()
        self.configure_basic_data_repository()

    def tearDown(self) -> None:
        configure_data_access_filter_provider(TenantOnlyDataAccessFilterProvider())
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

        sorted_items = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            status=None,
            sort_by="code",
            sort_dir="desc",
            current_user=self.current_user,
        )
        self.assertEqual([item["code"] for item in sorted_items["items"]], ["silver", "gold"])

        deleted = services.delete_dictionary_item(item_id=int(silver["id"]), current_user=self.current_user)
        self.assertTrue(deleted["deleted"])
        recreated_silver = services.save_dictionary_item(
            int(saved_type["id"]),
            {
                "code": "silver",
                "value": "S2",
                "sort_order": 3,
            },
            self.current_user,
        )["item"]
        deleted_recreated = services.delete_dictionary_item(item_id=int(recreated_silver["id"]), current_user=self.current_user)
        self.assertTrue(deleted_recreated["deleted"])

        services.save_dictionary_item(
            int(child_type["id"]),
            {"code": "child", "value": "C"},
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

    def test_dictionary_item_import_export_supports_dry_run_upsert_and_validation(self) -> None:
        from basic_data.application import services

        saved_type = services.save_dictionary_type(
            {"code": "customer_level", "name": "客户等级"},
            self.current_user,
        )["item"]
        csv_content = (
            "字典项编码,字典项名称,标签颜色,显示顺序,状态,备注,扩展信息(JSON)\n"
            'gold,金牌客户,#D97706,1,启用,高价值客户,"{""score"":90}"\n'
            "silver,银牌客户,#94A3B8,2,停用,普通客户,\n"
        ).encode("utf-8")

        dry_run = services.import_dictionary_items(
            type_id=int(saved_type["id"]),
            content=csv_content,
            filename="dictionary-items.csv",
            dry_run=True,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertEqual(dry_run["created_count"], 2)
        self.assertEqual(dry_run["error_count"], 0)
        empty_items = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            status=None,
            current_user=self.current_user,
        )
        self.assertEqual(empty_items["pagination"]["total"], 0)

        imported = services.import_dictionary_items(
            type_id=int(saved_type["id"]),
            content=csv_content,
            filename="dictionary-items.csv",
            dry_run=False,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertEqual(imported["created_count"], 2)
        items = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            status=None,
            current_user=self.current_user,
        )
        self.assertEqual([item["code"] for item in items["items"]], ["gold", "silver"])
        self.assertEqual(items["items"][0]["extra"], {"score": 90})
        self.assertEqual(items["items"][1]["status"], "disabled")

        update_content = (
            "字典项编码,字典项名称,标签颜色,显示顺序,状态,备注,扩展信息(JSON)\n"
            "gold,VIP客户,#059669,3,启用,已升级,\n"
        ).encode("utf-8")
        updated = services.import_dictionary_items(
            type_id=int(saved_type["id"]),
            content=update_content,
            filename="dictionary-items.csv",
            dry_run=False,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertEqual(updated["updated_count"], 1)
        gold = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="VIP",
            status=None,
            current_user=self.current_user,
        )["items"][0]
        self.assertEqual(gold["code"], "gold")
        self.assertEqual(gold["value"], "VIP客户")

        stream, filename = services.export_dictionary_items(type_id=int(saved_type["id"]), current_user=self.current_user)
        exported_text = stream.read().decode("utf-8-sig")
        self.assertEqual(filename, "customer_level-dictionary-items.csv")
        self.assertIn("字典项编码,字典项名称,标签颜色,显示顺序,状态,备注,扩展信息(JSON)", exported_text)
        self.assertIn("gold,VIP客户,#059669,3,启用,已升级,", exported_text)

        template_stream, template_filename = services.dictionary_item_import_template(type_id=int(saved_type["id"]), current_user=self.current_user)
        template_text = template_stream.read().decode("utf-8-sig")
        self.assertEqual(template_filename, "customer_level-字典项导入模板.csv")
        self.assertIn("字典项编码,字典项名称,标签颜色,显示顺序,状态,备注,扩展信息(JSON)", template_text)
        self.assertIn("gold,金牌客户,#D97706,1,启用,用于标识高价值客户", template_text)

        invalid = services.import_dictionary_items(
            type_id=int(saved_type["id"]),
            content=b"code,value,status,extra_json\nbad,,inactive,[]\nbad,duplicate,active,{}\n",
            filename="dictionary-items.csv",
            dry_run=True,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertGreaterEqual(invalid["error_count"], 3)

    def test_dictionary_item_import_decodes_gb18030_csv(self) -> None:
        from basic_data.application import services

        saved_type = services.save_dictionary_type(
            {"code": "customer_level_gbk", "name": "客户等级GBK"},
            self.current_user,
        )["item"]
        csv_content = (
            "字典项编码,字典项名称,标签颜色,显示顺序,状态,备注,扩展信息(JSON)\n"
            "gold,金牌客户,#D97706,1,启用,高价值客户,\n"
            "silver,银牌客户,#94A3B8,2,停用,普通客户,\n"
        ).encode("gb18030")
        self.assertNotIn(b"customer_level", csv_content)

        summary = services.import_dictionary_items(
            type_id=int(saved_type["id"]),
            content=csv_content,
            filename="dictionary-items.csv",
            dry_run=False,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertEqual(summary["created_count"], 2)
        self.assertEqual(summary["error_count"], 0)

        items = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            status=None,
            current_user=self.current_user,
        )["items"]
        self.assertEqual([item["code"] for item in items], ["gold", "silver"])
        self.assertEqual(items[0]["value"], "金牌客户")
        self.assertEqual(items[1]["description"], "普通客户")

    def test_region_import_decodes_gb18030_csv(self) -> None:
        from basic_data.application import services

        csv_content = (
            "code,parent_code,name,short_name,level,sort_order,status\n"
            "310000,,上海市,上海,省,1,active\n"
            "310100,310000,市辖区,辖区,市,2,active\n"
        ).encode("gb18030")

        summary = services.import_regions(
            content=csv_content,
            filename="regions.csv",
            dry_run=False,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertEqual(summary["created_count"], 2)
        self.assertEqual(summary["error_count"], 0)

        tree = services.list_region_tree(include_disabled=True, current_user=self.current_user)["items"]
        self.assertEqual(tree[0]["name"], "上海市")
        self.assertEqual(tree[0]["children"][0]["name"], "市辖区")

    def test_dictionary_item_list_filters_by_code_and_value(self) -> None:
        from basic_data.application import services

        saved_type = services.save_dictionary_type(
            {"code": "customer_level_filter", "name": "客户等级筛选"},
            self.current_user,
        )["item"]
        for code, value, status in [
            ("gold", "金牌客户", "active"),
            ("silver", "银牌客户", "active"),
            ("bronze", "铜牌客户", "disabled"),
            ("platinum", "白金客户", "active"),
        ]:
            services.save_dictionary_item(
                int(saved_type["id"]),
                {"code": code, "value": value, "status": status},
                self.current_user,
            )

        all_items = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            status=None,
            current_user=self.current_user,
        )
        self.assertEqual(all_items["pagination"]["total"], 4)

        only_silver = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            code="silver",
            status=None,
            current_user=self.current_user,
        )
        self.assertEqual(only_silver["pagination"]["total"], 1)
        self.assertEqual(only_silver["items"][0]["code"], "silver")

        gold_value = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            value="金牌",
            status=None,
            current_user=self.current_user,
        )
        self.assertEqual(gold_value["pagination"]["total"], 1)
        self.assertEqual(gold_value["items"][0]["value"], "金牌客户")

        metal_value = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            value="牌",
            status=None,
            current_user=self.current_user,
        )
        self.assertEqual(metal_value["pagination"]["total"], 3)

        code_and_value = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            code="gold",
            value="银",
            status=None,
            current_user=self.current_user,
        )
        self.assertEqual(code_and_value["pagination"]["total"], 0)

        code_with_status = services.list_dictionary_items(
            type_id=int(saved_type["id"]),
            page=1,
            page_size=20,
            keyword="",
            value="牌",
            status="disabled",
            current_user=self.current_user,
        )
        self.assertEqual(code_with_status["pagination"]["total"], 1)
        self.assertEqual(code_with_status["items"][0]["code"], "bronze")

    def test_dictionary_service_without_data_policy_uses_tenant_scope(self) -> None:
        from authorization.application import services as authorization_services
        from basic_data.application import services
        from system.application.data_access import configure_data_access_filter_provider

        previous_authorization_repository = authorization_services.repository
        try:
            authorization_services.configure_repository(EmptyAuthorizationRepository())
            configure_data_access_filter_provider(authorization_services.BuiltinDataAccessFilterProvider())
            owner = {**self.current_user, "id": 7, "is_platform_admin": False, "is_tenant_admin": False}
            other = {**self.current_user, "id": 8, "is_platform_admin": False, "is_tenant_admin": False}
            saved_type = services.save_dictionary_type({"code": "ticket_status", "name": "工单状态"}, owner)["item"]
            services.save_dictionary_item(int(saved_type["id"]), {"code": "open", "value": "待处理"}, owner)

            type_page = services.list_dictionary_types(page=1, page_size=20, keyword="", status=None, category="", current_user=other)
            item_page = services.list_dictionary_items(type_id=int(saved_type["id"]), page=1, page_size=20, keyword="", status=None, current_user=other)

            self.assertEqual(type_page["pagination"]["total"], 1)
            self.assertEqual(item_page["pagination"]["total"], 1)
        finally:
            authorization_services.repository = previous_authorization_repository

    def test_dictionary_service_with_self_data_policy_filters_owner(self) -> None:
        from authorization.application import services as authorization_services
        from basic_data.application import services
        from system.application.data_access import configure_data_access_filter_provider

        previous_authorization_repository = authorization_services.repository
        try:
            authorization_services.configure_repository(
                StaticAuthorizationRepository(
                    [
                        DataAccessPolicy(
                            id=1,
                            tenant_id=1,
                            subject_type="user",
                            subject_id=8,
                            resource_key="basic-data.dictionary",
                            action="read",
                            scope="self",
                            department_ids=(),
                            priority=100,
                            create_time="",
                            update_time="",
                        )
                    ]
                )
            )
            configure_data_access_filter_provider(authorization_services.BuiltinDataAccessFilterProvider())
            owner = {**self.current_user, "id": 7, "is_platform_admin": False, "is_tenant_admin": False}
            other = {**self.current_user, "id": 8, "is_platform_admin": False, "is_tenant_admin": False}
            saved_type = services.save_dictionary_type({"code": "ticket_priority", "name": "工单优先级"}, owner)["item"]
            services.save_dictionary_item(int(saved_type["id"]), {"code": "high", "value": "高"}, owner)

            type_page = services.list_dictionary_types(page=1, page_size=20, keyword="", status=None, category="", current_user=other)
            item_page = services.list_dictionary_items(type_id=int(saved_type["id"]), page=1, page_size=20, keyword="", status=None, current_user=other)

            self.assertEqual(type_page["pagination"]["total"], 0)
            self.assertEqual(item_page["pagination"]["total"], 0)
        finally:
            authorization_services.repository = previous_authorization_repository

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

        sorted_response = self.request("GET", "/api/basic-data/dictionary-types?page=1&page_size=20&sort_by=code&sort_dir=desc")
        self.assertEqual(sorted_response.status_code, 200)
        self.assertEqual(sorted_response.json()["data"]["items"][0]["code"], "invoice_status")

        invalid_sort_response = self.request("GET", "/api/basic-data/dictionary-types?page=1&page_size=20&sort_by=bad_field&sort_dir=asc")
        self.assertEqual(invalid_sort_response.status_code, 400)
        self.assertFalse(invalid_sort_response.json()["success"])

        duplicate_response = self.request(
            "POST",
            "/api/basic-data/dictionary-types",
            json={"code": "invoice_status", "name": "Invoice Status Duplicate"},
        )
        self.assertEqual(duplicate_response.status_code, 400)
        duplicate_payload = duplicate_response.json()
        self.assertFalse(duplicate_payload["success"])
        self.assertEqual(duplicate_payload["code"], "BASIC_DATA_VALIDATION_ERROR")

    def test_region_service_crud_generates_path_and_tree(self) -> None:
        from basic_data.application import services

        province = services.save_region(
            {"code": "110000", "name": "北京市", "short_name": "北京", "level": "省"},
            self.current_user,
        )["item"]
        self.assertEqual(province["level"], "province")
        self.assertEqual(province["path"], "/110000/")

        city = services.save_region(
            {"code": "110100", "name": "北京市", "level": "市", "parent_id": province["id"], "path": "/bad/"},
            self.current_user,
        )["item"]
        self.assertEqual(city["path"], "/110000/110100/")

        district = services.save_region(
            {"code": "110101", "name": "东城区", "level": "区县", "parent_id": city["id"]},
            self.current_user,
        )["item"]
        self.assertEqual(district["level"], "district")
        self.assertEqual(district["path"], "/110000/110100/110101/")

        tree = services.list_region_tree(include_disabled=True, current_user=self.current_user)
        self.assertEqual(tree["items"][0]["children"][0]["children"][0]["code"], "110101")

        with self.assertRaisesRegex(Exception, "parent must be city"):
            services.save_region({"code": "120101", "name": "非法区", "level": "区", "parent_id": province["id"]}, self.current_user)

    def test_region_self_data_scope_uses_owner_columns(self) -> None:
        from basic_data.application import services

        configure_data_access_filter_provider(SelfOnlyProvider())
        owner = {**self.current_user, "id": 7, "is_platform_admin": False}
        other = {**self.current_user, "id": 8, "is_platform_admin": False}
        services.save_region({"code": "330000", "name": "Zhejiang", "level": "province"}, owner)

        owner_page = services.list_regions(page=1, page_size=20, keyword="", status=None, level=None, parent_id=None, current_user=owner)
        other_page = services.list_regions(page=1, page_size=20, keyword="", status=None, level=None, parent_id=None, current_user=other)

        self.assertEqual(owner_page["pagination"]["total"], 1)
        self.assertEqual(other_page["pagination"]["total"], 0)

    def test_region_import_supports_chinese_level_dry_run_and_ignores_path(self) -> None:
        from basic_data.application import services

        csv_content = (
            "code,parent_code,name,short_name,level,sort_order,status,path\n"
            "110101,110100,东城区,东城,区,3,active,/bad/path/\n"
            "110100,110000,北京市,北京,市,2,active,/bad/path/\n"
            "110000,,北京市,北京,省,1,active,/bad/path/\n"
        ).encode("utf-8")

        dry_run = services.import_regions(
            content=csv_content,
            filename="regions.csv",
            dry_run=True,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertEqual(dry_run["created_count"], 3)
        self.assertEqual(dry_run["error_count"], 0)
        self.assertEqual(len(dry_run["warnings"]), 3)
        self.assertEqual(services.list_region_tree(include_disabled=True, current_user=self.current_user)["items"], [])

        imported = services.import_regions(
            content=csv_content,
            filename="regions.csv",
            dry_run=False,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertEqual(imported["created_count"], 3)
        districts = services.list_regions(page=1, page_size=20, keyword="东城", status=None, level="区县", parent_id=None, current_user=self.current_user)
        self.assertEqual(districts["items"][0]["path"], "/110000/110100/110101/")

        repeated = services.import_regions(
            content=csv_content,
            filename="regions.csv",
            dry_run=False,
            mode="upsert",
            current_user=self.current_user,
        )
        self.assertEqual(repeated["updated_count"], 3)

    def test_region_http_import_endpoint(self) -> None:
        content = "code,parent_code,name,short_name,level\n310000,,上海市,上海,省份\n".encode("utf-8")
        response = self.request(
            "POST",
            "/api/basic-data/regions/import?dry_run=false",
            files={"upload": ("regions.csv", content, "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["created_count"], 1)

        tree_response = self.request("GET", "/api/basic-data/regions/tree")
        self.assertEqual(tree_response.json()["data"]["items"][0]["path"], "/310000/")

    def test_dictionary_item_http_import_and_export_endpoints(self) -> None:
        type_response = self.request(
            "POST",
            "/api/basic-data/dictionary-types",
            json={"code": "ticket_status", "name": "工单状态"},
        )
        self.assertEqual(type_response.status_code, 200)
        type_id = int(type_response.json()["data"]["item"]["id"])
        content = "字典项编码,字典项名称,标签颜色,显示顺序,状态,备注,扩展信息(JSON)\nopen,待处理,#2563EB,1,启用,待处理工单,{}\n".encode("utf-8")

        template_response = self.request("GET", f"/api/basic-data/dictionary-types/{type_id}/items/import-template")
        self.assertEqual(template_response.status_code, 200)
        self.assertIn("attachment", template_response.headers.get("content-disposition", ""))
        template_text = template_response.content.decode("utf-8-sig")
        self.assertIn("字典项编码,字典项名称,标签颜色,显示顺序,状态,备注,扩展信息(JSON)", template_text)

        dry_run_response = self.request(
            "POST",
            f"/api/basic-data/dictionary-types/{type_id}/items/import?dry_run=true",
            files={"upload": ("dictionary-items.csv", content, "text/csv")},
        )
        self.assertEqual(dry_run_response.status_code, 200)
        self.assertEqual(dry_run_response.json()["data"]["created_count"], 1)

        import_response = self.request(
            "POST",
            f"/api/basic-data/dictionary-types/{type_id}/items/import?dry_run=false",
            files={"upload": ("dictionary-items.csv", content, "text/csv")},
        )
        self.assertEqual(import_response.status_code, 200)
        self.assertEqual(import_response.json()["data"]["created_count"], 1)

        export_response = self.request("GET", f"/api/basic-data/dictionary-types/{type_id}/items/export")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("attachment", export_response.headers.get("content-disposition", ""))
        exported_text = export_response.content.decode("utf-8-sig")
        self.assertIn("字典项编码,字典项名称,标签颜色,显示顺序,状态,备注,扩展信息(JSON)", exported_text)
        self.assertIn("open,待处理,#2563EB,1,启用,待处理工单,{}", exported_text)

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
