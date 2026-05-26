from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python" / "ops-admin-datasets" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "python" / "ops-admin-system" / "src"))

from datasets.application import services


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

        services.configure_repository(repositories)
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

        services.save_fields(
            int(created["id"]),
            {
                "fields": [
                    {"field_key": "date", "label": "日期", "data_type": "date", "sort_order": 1},
                    {"field_key": "amount", "label": "销售额", "data_type": "number", "sort_order": 2},
                ]
            },
            self.user,
        )
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
        self.assertEqual(preview["fields"][0]["label"], "日期")
        self.assertEqual(preview["meta"]["runtime"], "manual")

        listed = services.list_datasets(page=1, page_size=20, current_user=self.user)
        self.assertEqual(listed["pagination"]["total"], 1)
        self.assertEqual(listed["items"][0]["field_count"], 2)
        self.assertEqual(listed["items"][0]["row_count"], 2)

    def test_dataset_is_platform_scoped(self) -> None:
        created = services.save_dataset({"key": "platform_only", "name": "平台数据集"}, self.user)["item"]

        self.assertEqual(created["tenant_id"], 1)
        self.assertEqual(created["visibility"], "platform")

        detail = services.dataset_detail(int(created["id"]), self.other_user)
        self.assertEqual(detail["item"]["id"], created["id"])

    def test_requires_explicit_initialization(self) -> None:
        missing_db = Path(self.temp_dir.name) / "missing.db"
        sqlite3.connect(missing_db).close()
        with mock.patch.dict("os.environ", {"FG_AGENT_DB_PATH": str(missing_db)}, clear=False):
            with self.assertRaises(Exception) as caught:
                services.list_datasets(page=1, page_size=20, current_user=self.user)

        self.assertIn("init_datasets.py", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
