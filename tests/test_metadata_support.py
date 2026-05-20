from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from metadata_support.application import services
from metadata_support.entrypoints import init_tasks


class MetadataSupportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "metadata.db"
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
        self.current_user = {
            "id": 10,
            "username": "owner",
            "current_tenant": {"id": 7, "tenant_key": "tenant-a", "name": "Tenant A"},
            "tenant_id": 7,
        }
        self.initialize_db()
        init_tasks()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize_db(self) -> None:
        from metadata_support.infrastructure.persistence.bootstrap import ensure_metadata_support_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_metadata_support_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def test_bind_and_search_resource_metadata_and_tags(self) -> None:
        services.bind_resource_metadata(
            tenant_id=7,
            resource_type_code="file_management.file_object",
            resource_id=12,
            metadata={"project_code": "P001", "amount": 120000, "archived": False},
            tag_codes=["合同", "归档"],
            actor="owner",
            actor_id=10,
        )

        resource = services.get_resource_metadata(
            resource_type_code="file_management.file_object",
            resource_id=12,
            current_user=self.current_user,
        )
        self.assertEqual(resource["item"]["metadata"]["project_code"], "P001")
        self.assertEqual({item["code"] for item in resource["tags"]}, {"合同", "归档"})

        by_tag = services.search_resource_ids(
            tenant_id=7,
            resource_type_code="file_management.file_object",
            tag_codes=["合同"],
        )
        self.assertEqual(by_tag["resource_ids"], ["12"])

        by_metadata = services.search_resource_ids(
            tenant_id=7,
            resource_type_code="file_management.file_object",
            metadata_filters=[{"field_key": "amount", "op": "gte", "value": 100000, "value_type": "number"}],
        )
        self.assertEqual(by_metadata["resource_ids"], ["12"])


if __name__ == "__main__":
    unittest.main()
