from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class OrganizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ops-admin-organization-test.db"
        self.env_patch = mock.patch.dict(
            os.environ,
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
                "FG_AGENT_DB_PATH": str(self.db_path),
            },
            clear=False,
        )
        self.env_patch.start()

        from organization.infrastructure.persistence.bootstrap import ensure_organization_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_organization_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_department_rename_keeps_existing_parent(self) -> None:
        from organization.domain.exceptions import OrganizationDomainError
        from organization.infrastructure.persistence import repositories

        parent = repositories.save_department(
            tenant_id=1,
            payload={"code": "001", "name": "技术支持部门", "status": "active"},
            actor="tester",
            actor_id=1,
        )
        child = repositories.save_department(
            tenant_id=1,
            payload={"parent_id": parent.id, "code": "0011", "name": "一线技术支持", "status": "active"},
            actor="tester",
            actor_id=1,
        )

        renamed = repositories.save_department(
            tenant_id=1,
            payload={"id": child.id, "parent_id": parent.id, "code": "0011", "name": "一线技术支持部门", "status": "active"},
            actor="tester",
            actor_id=1,
        )

        self.assertEqual(renamed.name, "一线技术支持部门")
        self.assertEqual(renamed.parent_id, parent.id)
        with self.assertRaisesRegex(OrganizationDomainError, "下级部门"):
            repositories.save_department(
                tenant_id=1,
                payload={"id": parent.id, "parent_id": child.id, "code": "001", "name": "技术支持部门", "status": "active"},
                actor="tester",
                actor_id=1,
            )
