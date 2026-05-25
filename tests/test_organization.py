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
                "OPS_ADMIN_APPLICATION_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-application.json"),
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

    def test_set_user_departments_is_idempotent_and_preserves_history(self) -> None:
        from organization.infrastructure.persistence import repositories

        first = repositories.save_department(
            tenant_id=1,
            payload={"code": "dept-a", "name": "Dept A", "status": "active"},
            actor="tester",
            actor_id=1,
        )
        second = repositories.save_department(
            tenant_id=1,
            payload={"code": "dept-b", "name": "Dept B", "status": "active"},
            actor="tester",
            actor_id=1,
        )

        initial = repositories.set_user_departments(
            tenant_id=1,
            user_id=9,
            department_ids=[first.id],
            primary_department_id=first.id,
            actor="tester",
            actor_id=1,
        )
        repeated = repositories.set_user_departments(
            tenant_id=1,
            user_id=9,
            department_ids=[first.id],
            primary_department_id=first.id,
            actor="tester",
            actor_id=1,
        )

        self.assertEqual([item["department_id"] for item in initial], [first.id])
        self.assertEqual([item["department_id"] for item in repeated], [first.id])

        switched = repositories.set_user_departments(
            tenant_id=1,
            user_id=9,
            department_ids=[second.id],
            primary_department_id=second.id,
            actor="tester",
            actor_id=1,
        )
        restored = repositories.set_user_departments(
            tenant_id=1,
            user_id=9,
            department_ids=[first.id],
            primary_department_id=first.id,
            actor="tester",
            actor_id=1,
        )

        self.assertEqual([item["department_id"] for item in switched], [second.id])
        self.assertEqual([item["department_id"] for item in restored], [first.id])
        batch = repositories.users_departments(tenant_id=1, user_ids=[9, 10])
        self.assertEqual([item["department_id"] for item in batch[9]], [first.id])
        self.assertEqual(batch[10], [])
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT department_id, deleted, active_marker
                FROM user_department_memberships
                WHERE tenant_id = 1 AND user_id = 9
                ORDER BY id
                """
            ).fetchall()
        finally:
            conn.close()
        self.assertEqual([row[0] for row in rows], [first.id, second.id, first.id])
        self.assertEqual([row[1] for row in rows], [1, 1, 0])
        self.assertEqual([row[2] for row in rows], [None, None, 1])

    def test_reporting_relationships_resolve_subordinates_and_reject_cycles(self) -> None:
        from organization.domain.exceptions import OrganizationDomainError
        from organization.infrastructure.persistence import repositories

        repositories.set_user_reporting_manager(
            tenant_id=1,
            user_id=20,
            manager_user_id=10,
            actor="tester",
            actor_id=1,
        )
        repositories.set_user_reporting_manager(
            tenant_id=1,
            user_id=30,
            manager_user_id=20,
            actor="tester",
            actor_id=1,
        )

        self.assertEqual(repositories.subordinate_user_ids(tenant_id=1, manager_user_id=10), [10, 20, 30])
        self.assertEqual(repositories.user_reporting_manager(tenant_id=1, user_id=20)["manager_user_id"], 10)

        with self.assertRaisesRegex(OrganizationDomainError, "cycle"):
            repositories.set_user_reporting_manager(
                tenant_id=1,
                user_id=10,
                manager_user_id=30,
                actor="tester",
                actor_id=1,
            )

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
