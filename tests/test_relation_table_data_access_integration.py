from __future__ import annotations

import sqlite3
import unittest
from typing import Any

from system.application.data_access import DataAccessPredicate, ResourceDescriptor, SCOPE_DEPARTMENT, SCOPE_SELF
from system.application.sql_data_access import SQLDataAccessInjectionRequest, inject_data_access_into_select


RELATION_RESOURCE = ResourceDescriptor(
    resource_key="demo.document",
    access_mode="relation_table",
    relation_table="demo_document_members",
    relation_resource_id_column="document_id",
    relation_user_column="subject_user_id",
    relation_department_column="subject_department_id",
    relation_tenant_column="tenant_id",
    relation_deleted_column="deleted",
)


class RelationTableDataAccessIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE demo_documents (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                owner_user_id INTEGER,
                owner_department_id INTEGER,
                deleted INTEGER NOT NULL DEFAULT 0,
                title TEXT NOT NULL
            );

            CREATE TABLE demo_document_members (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                subject_user_id INTEGER,
                subject_department_id INTEGER,
                deleted INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        self.conn.executemany(
            """
            INSERT INTO demo_documents (id, tenant_id, owner_user_id, owner_department_id, deleted, title)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 7, 99, 99, 0, "user-visible"),
                (2, 7, 99, 99, 0, "not-visible"),
                (3, 7, 99, 99, 0, "department-visible"),
                (4, 8, 10, 33, 0, "other-tenant"),
                (5, 7, 10, 33, 1, "deleted-document"),
            ],
        )
        self.conn.executemany(
            """
            INSERT INTO demo_document_members (
                id, tenant_id, document_id, subject_user_id, subject_department_id, deleted
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 7, 1, 10, None, 0),
                (2, 7, 2, 11, None, 0),
                (3, 7, 3, None, 33, 0),
                (4, 8, 4, 10, 33, 0),
                (5, 7, 5, 10, None, 0),
                (6, 7, 2, 10, None, 1),
            ],
        )
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()

    def test_relation_table_self_list_count_and_detail_match(self) -> None:
        predicate = DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10)

        items_sql, items_params = guarded_sql(
            "SELECT d.id, d.title FROM demo_documents d WHERE d.deleted = 0 ORDER BY d.id",
            (),
            predicate,
        )
        items = [dict(row) for row in self.conn.execute(items_sql, items_params).fetchall()]
        total = self.conn.execute(f"SELECT COUNT(*) AS total FROM ({items_sql}) AS guarded", items_params).fetchone()["total"]

        self.assertEqual(total, 1)
        self.assertEqual(items, [{"id": 1, "title": "user-visible"}])
        self.assertIsNotNone(self.fetch_detail(1, predicate))
        self.assertIsNone(self.fetch_detail(2, predicate))
        self.assertIsNone(self.fetch_detail(4, predicate))

    def test_relation_table_department_list_count_and_detail_match(self) -> None:
        predicate = DataAccessPredicate(tenant_id=7, scope=SCOPE_DEPARTMENT, department_ids=(33,))

        items_sql, items_params = guarded_sql(
            "SELECT d.id, d.title FROM demo_documents d WHERE d.deleted = 0 ORDER BY d.id",
            (),
            predicate,
        )
        items = [dict(row) for row in self.conn.execute(items_sql, items_params).fetchall()]
        total = self.conn.execute(f"SELECT COUNT(*) AS total FROM ({items_sql}) AS guarded", items_params).fetchone()["total"]

        self.assertEqual(total, 1)
        self.assertEqual(items, [{"id": 3, "title": "department-visible"}])
        self.assertIsNone(self.fetch_detail(1, predicate))
        self.assertIsNotNone(self.fetch_detail(3, predicate))

    def fetch_detail(self, document_id: int, predicate: DataAccessPredicate) -> dict[str, Any] | None:
        sql, params = guarded_sql(
            "SELECT d.id, d.title FROM demo_documents d WHERE d.id = ? AND d.deleted = 0",
            (document_id,),
            predicate,
        )
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def guarded_sql(sql: str, params: tuple[Any, ...], predicate: DataAccessPredicate) -> tuple[str, tuple[Any, ...]]:
    return inject_data_access_into_select(
        SQLDataAccessInjectionRequest(
            sql=sql,
            params=params,
            resource=RELATION_RESOURCE,
            predicate=predicate,
            source_alias="d",
        )
    )


if __name__ == "__main__":
    unittest.main()
