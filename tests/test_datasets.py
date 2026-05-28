from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python" / "ops-admin-datasets" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "python" / "ops-admin-system" / "src"))

from datasets.application import services
from system.application.data_access import (
    DataAccessPredicate,
    TenantOnlyDataAccessFilterProvider,
    configure_data_access_filter_provider,
)


class SelfOnlyProvider:
    def resolve_filter(self, *, current_user: dict[str, object], resource: object, action: str) -> DataAccessPredicate:
        tenant = current_user.get("current_tenant") or {}
        return DataAccessPredicate(
            tenant_id=int(tenant.get("id") or current_user.get("tenant_id") or 0),
            scope="self",
            user_id=int(current_user.get("id") or 0),
        )


class NativeValueExecutor:
    def execute_preview(
        self,
        *,
        dataset: object,
        fields: list[object],
        page: int,
        page_size: int,
        variables: dict[str, object],
        current_user: dict[str, object],
        apply_data_access: bool = True,
    ) -> tuple[list[dict[str, object]], int, dict[str, object]]:
        return [
            {
                "created_at": datetime(2026, 5, 28, 12, 30, 45),
                "business_date": date(2026, 5, 28),
                "run_time": time(9, 15, 30),
                "amount": Decimal("19.99"),
            }
        ], 1, {"runtime": "source_query"}


class DatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "datasets.db"
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
                "FG_AGENT_DB_PATH": str(self.db_path),
                "OPS_ADMIN_APPLICATION_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-application.json"),
            },
            clear=False,
        )
        self.env_patch.start()
        from datasets.infrastructure.persistence import repositories
        from datasets.infrastructure.query_executor import SqlDatasetExecutor
        from datasets.infrastructure.schema_introspection import DatabaseSourceSchemaInspector

        services.configure_repository(repositories)
        services.configure_external_executor(SqlDatasetExecutor())
        services.configure_source_schema_inspector(DatabaseSourceSchemaInspector())
        self.user = {
            "id": 10,
            "username": "owner",
            "current_tenant": {"id": 7, "tenant_key": "tenant-a", "name": "Tenant A"},
            "tenant_id": 7,
        }
        self.other_user = {
            "id": 11,
            "username": "other",
            "current_tenant": {"id": 8, "tenant_key": "tenant-b", "name": "Tenant B"},
            "tenant_id": 8,
        }
        self.initialize_db()

    def tearDown(self) -> None:
        configure_data_access_filter_provider(TenantOnlyDataAccessFilterProvider())
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize_db(self) -> None:
        from datasets.infrastructure.persistence.bootstrap import ensure_datasets_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_datasets_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def test_manual_dataset_publish_and_preview(self) -> None:
        created = services.save_dataset(
            {
                "key": "sales_daily",
                "name": "每日销售",
                "description": "仪表盘销售趋势数据集",
                "dataset_type": "manual",
            },
            self.user,
        )["item"]

        services.save_manual_rows(
            int(created["id"]),
            {
                "rows": [
                    {"date": "2026-05-01", "amount": 100},
                    {"date": "2026-05-02", "amount": 150},
                ]
            },
            self.user,
        )

        version = services.publish_dataset(int(created["id"]), self.user)["item"]
        self.assertEqual(version["version_no"], 1)

        preview = services.preview_dataset(dataset_id=int(created["id"]), page=1, page_size=1, current_user=self.user)
        self.assertEqual(preview["pagination"]["total"], 2)
        self.assertEqual(len(preview["items"]), 1)
        self.assertEqual([field["field_key"] for field in preview["fields"]], ["date", "amount"])
        self.assertEqual(preview["fields"][1]["data_type"], "number")
        self.assertEqual(preview["meta"]["runtime"], "manual")

        listed = services.list_datasets(page=1, page_size=20, current_user=self.user)
        self.assertEqual(listed["pagination"]["total"], 1)
        self.assertEqual(listed["items"][0]["row_count"], 2)

    def test_manual_dataset_accepts_scalar_rows(self) -> None:
        from datasets.interfaces.http.dtos import DatasetRowsRequest

        created = services.save_dataset(
            {
                "key": "scalar_values",
                "name": "标量数据",
                "dataset_type": "manual",
            },
            self.user,
        )["item"]

        self.assertEqual(DatasetRowsRequest(rows=[1, 2, 3]).rows, [1, 2, 3])
        saved = services.save_manual_rows(int(created["id"]), {"rows": [1, 2, 3]}, self.user)

        self.assertEqual(saved["count"], 3)
        preview = services.preview_dataset(dataset_id=int(created["id"]), page=1, page_size=20, current_user=self.user)
        self.assertEqual(preview["pagination"]["total"], 3)
        self.assertEqual(preview["items"], [{"value": 1}, {"value": 2}, {"value": 3}])
        self.assertEqual(preview["fields"][0]["field_key"], "value")
        self.assertEqual(preview["fields"][0]["label"], "值")
        self.assertEqual(preview["fields"][0]["data_type"], "number")

    def test_dataset_is_platform_scoped(self) -> None:
        created = services.save_dataset({"key": "platform_only", "name": "平台数据集"}, self.user)["item"]

        self.assertEqual(created["tenant_id"], 1)
        self.assertEqual(created["visibility"], "platform")

        detail = services.dataset_detail(int(created["id"]), self.other_user)
        self.assertEqual(detail["item"]["id"], created["id"])

    def test_source_query_dataset_applies_current_tenant_scope(self) -> None:
        self.seed_orders()
        created = self.create_source_query_dataset()

        preview = services.preview_dataset(dataset_id=int(created["id"]), page=1, page_size=20, current_user=self.user)

        self.assertEqual(preview["pagination"]["total"], 2)
        self.assertEqual({row["name"] for row in preview["items"]}, {"自己的订单", "同租户订单"})
        self.assertEqual(
            [field["field_key"] for field in preview["fields"]],
            ["tenant_id", "owner_user_id", "owner_department_id", "name", "amount"],
        )
        self.assertEqual(preview["fields"][4]["data_type"], "number")
        self.assertEqual(preview["meta"]["runtime"], "source_query")

    def test_source_query_dataset_applies_data_permission_scope(self) -> None:
        self.seed_orders()
        created = self.create_source_query_dataset()
        configure_data_access_filter_provider(SelfOnlyProvider())

        preview = services.preview_dataset(dataset_id=int(created["id"]), page=1, page_size=20, current_user=self.user)

        self.assertEqual(preview["pagination"]["total"], 1)
        self.assertEqual(preview["items"][0]["name"], "自己的订单")

    def test_platform_source_query_preview_can_disable_data_access_scope(self) -> None:
        self.seed_orders()
        created = self.create_source_query_dataset()
        configure_data_access_filter_provider(SelfOnlyProvider())

        preview = services.preview_dataset(
            dataset_id=int(created["id"]),
            page=1,
            page_size=20,
            current_user=self.user,
            apply_data_access=False,
        )

        self.assertEqual(preview["pagination"]["total"], 3)
        self.assertEqual({row["name"] for row in preview["items"]}, {"自己的订单", "同租户订单", "其他租户订单"})
        self.assertEqual(preview["meta"]["data_scope"], "disabled")

    def test_source_query_dataset_applies_scope_without_projecting_owner_columns(self) -> None:
        self.seed_orders()
        created = services.save_dataset(
            {
                "key": "orders_public_columns",
                "name": "订单公开列查询",
                "dataset_type": "source_query",
                "query_config": {
                    "sql": "SELECT name, amount FROM business_orders",
                    "data_access": {"resource_key": "business.orders"},
                },
            },
            self.user,
        )["item"]
        configure_data_access_filter_provider(SelfOnlyProvider())

        preview = services.preview_dataset(dataset_id=int(created["id"]), page=1, page_size=20, current_user=self.user)

        self.assertEqual(preview["pagination"]["total"], 1)
        self.assertEqual(preview["items"][0]["name"], "自己的订单")
        self.assertEqual([field["field_key"] for field in preview["fields"]], ["name", "amount"])

    def test_source_query_preview_can_use_temporary_query_config_without_saving(self) -> None:
        self.seed_orders()
        created = self.create_source_query_dataset()

        preview = services.preview_dataset(
            dataset_id=int(created["id"]),
            page=1,
            page_size=20,
            query_config={
                "sql": "SELECT tenant_id, owner_user_id, owner_department_id, name, amount FROM business_orders WHERE amount > ?",
                "params": [150],
                "data_access": {"resource_key": "business.orders"},
            },
            current_user=self.user,
        )
        detail = services.dataset_detail(int(created["id"]), self.user)

        self.assertEqual(preview["pagination"]["total"], 1)
        self.assertEqual(preview["items"][0]["name"], "同租户订单")
        self.assertEqual(detail["item"]["query_config"]["sql"], "SELECT tenant_id, owner_user_id, owner_department_id, name, amount FROM business_orders")

    def test_source_query_schema_lists_source_tables_and_columns(self) -> None:
        self.seed_orders()
        created = self.create_source_query_dataset()

        schema = services.source_schema(int(created["id"]), self.user)
        orders = next(item for item in schema["tables"] if item["name"] == "business_orders")

        self.assertEqual(schema["backend"], "sqlite")
        self.assertIn("amount", {column["name"] for column in orders["columns"]})
        self.assertIn("tenant_id", {column["name"] for column in orders["columns"]})

    def test_publish_source_query_dataset_serializes_native_sample_values(self) -> None:
        services.configure_external_executor(NativeValueExecutor())
        created = services.save_dataset(
            {
                "key": "native_values_query",
                "name": "原生值查询数据集",
                "dataset_type": "source_query",
                "query_config": {"sql": "SELECT created_at, business_date, run_time, amount FROM native_values"},
            },
            self.user,
        )["item"]

        version = services.publish_dataset(int(created["id"]), self.user)["item"]

        self.assertEqual(version["sample_rows"][0]["created_at"], "2026-05-28T12:30:45")
        self.assertEqual(version["sample_rows"][0]["business_date"], "2026-05-28")
        self.assertEqual(version["sample_rows"][0]["run_time"], "09:15:30")
        self.assertEqual(version["sample_rows"][0]["amount"], "19.99")

    def test_mysql_schema_introspection_handles_uppercase_information_schema_keys(self) -> None:
        from datasets.infrastructure.schema_introspection import inspect_mysql_tables

        class FakeCursor:
            def __init__(self, rows: list[dict[str, object]]) -> None:
                self.rows = rows

            def fetchall(self) -> list[dict[str, object]]:
                return self.rows

        class FakeConnection:
            column_params: tuple[object, ...] | None = None

            def execute(self, sql: str, params: tuple[object, ...] = ()) -> FakeCursor:
                if "information_schema.tables" in sql:
                    return FakeCursor([{"TABLE_SCHEMA": "ops_admin", "TABLE_NAME": "users"}])
                if "information_schema.columns" in sql:
                    self.column_params = params
                    return FakeCursor(
                        [
                            {
                                "COLUMN_NAME": "id",
                                "DATA_TYPE": "bigint",
                                "IS_NULLABLE": "NO",
                                "PRIMARY_KEY": 1,
                            },
                            {
                                "COLUMN_NAME": "username",
                                "DATA_TYPE": "varchar",
                                "IS_NULLABLE": "YES",
                                "PRIMARY_KEY": 0,
                            },
                        ]
                    )
                raise AssertionError(sql)

        conn = FakeConnection()
        tables = inspect_mysql_tables(conn)

        self.assertEqual(tables[0]["schema"], "ops_admin")
        self.assertEqual(tables[0]["name"], "users")
        self.assertEqual(conn.column_params[:2], ("ops_admin", "users"))
        self.assertEqual([column["name"] for column in tables[0]["columns"]], ["id", "username"])
        self.assertTrue(tables[0]["columns"][0]["primary_key"])
        self.assertFalse(tables[0]["columns"][0]["nullable"])

    def test_source_query_dataset_rejects_non_select_sql(self) -> None:
        with self.assertRaises(Exception) as caught:
            services.save_dataset(
                {
                    "key": "bad_query",
                    "name": "危险查询",
                    "dataset_type": "source_query",
                    "query_config": {"sql": "DELETE FROM business_orders"},
                },
                self.user,
            )

        self.assertIn("SELECT", str(caught.exception))

    def test_requires_explicit_initialization(self) -> None:
        missing_db = Path(self.temp_dir.name) / "missing.db"
        sqlite3.connect(missing_db).close()
        with mock.patch.dict("os.environ", {"FG_AGENT_DB_PATH": str(missing_db)}, clear=False):
            with self.assertRaises(Exception) as caught:
                services.list_datasets(page=1, page_size=20, current_user=self.user)

        self.assertIn("init_datasets.py", str(caught.exception))

    def test_mysql_dataset_key_column_is_quoted(self) -> None:
        from datasets.infrastructure.persistence import repositories

        with mock.patch.object(repositories, "database_target", return_value="mysql://user:pass@localhost/app"):
            self.assertEqual(repositories.dataset_key_column(), "`key`")
            self.assertEqual(repositories.dataset_key_column("d"), "d.`key`")
            self.assertEqual(repositories.dataset_sort_columns()["key"], "d.`key`")

    def seed_orders(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE business_orders (
                    id INTEGER PRIMARY KEY,
                    tenant_id INTEGER NOT NULL,
                    owner_user_id INTEGER NOT NULL,
                    owner_department_id INTEGER,
                    name TEXT NOT NULL,
                    amount INTEGER NOT NULL
                )
                """
            )
            conn.executemany(
                "INSERT INTO business_orders (tenant_id, owner_user_id, owner_department_id, name, amount) VALUES (?, ?, ?, ?, ?)",
                [
                    (7, 10, 1, "自己的订单", 100),
                    (7, 11, 1, "同租户订单", 200),
                    (8, 11, 2, "其他租户订单", 300),
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def create_source_query_dataset(self) -> dict[str, object]:
        created = services.save_dataset(
            {
                "key": "orders_query",
                "name": "订单查询数据集",
                "dataset_type": "source_query",
                "query_config": {
                    "sql": "SELECT tenant_id, owner_user_id, owner_department_id, name, amount FROM business_orders",
                    "data_access": {"resource_key": "business.orders"},
                },
            },
            self.user,
        )["item"]
        return created


if __name__ == "__main__":
    unittest.main()
