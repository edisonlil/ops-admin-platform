from __future__ import annotations

import unittest

from system.application.data_access import DataAccessPredicate, ResourceDescriptor, SCOPE_SELF
from system.application.sql_data_access import SQLDataAccessInjectionError, SQLDataAccessInjectionRequest
from system.application.sql_data_access import inject_data_access_into_select


class SQLDataAccessInjectionTests(unittest.TestCase):
    def test_injects_owner_scope_without_projecting_owner_columns(self) -> None:
        sql, params = inject_data_access_into_select(
            SQLDataAccessInjectionRequest(
                sql="SELECT name, amount FROM demo_documents WHERE status = ? ORDER BY id DESC",
                params=("active",),
                resource=ResourceDescriptor(resource_key="demo.document"),
                predicate=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
            )
        )

        self.assertIn("demo_documents.tenant_id = ?", sql)
        self.assertIn("demo_documents.owner_user_id = ?", sql)
        self.assertIn("ORDER BY id DESC", sql)
        self.assertEqual(params, ("active", 7, 10))

    def test_real_table_filter_ignores_forged_projected_tenant_column(self) -> None:
        sql, params = inject_data_access_into_select(
            SQLDataAccessInjectionRequest(
                sql="SELECT 7 AS tenant_id, name FROM demo_documents",
                params=(),
                resource=ResourceDescriptor(resource_key="demo.document"),
                predicate=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
            )
        )

        self.assertIn("demo_documents.tenant_id = ?", sql)
        self.assertIn("demo_documents.owner_user_id = ?", sql)
        self.assertEqual(params, (7, 10))

    def test_join_requires_source_alias(self) -> None:
        request = SQLDataAccessInjectionRequest(
            sql="SELECT d.name, m.id FROM demo_documents d JOIN demo_document_members m ON m.document_id = d.id",
            params=(),
            resource=ResourceDescriptor(resource_key="demo.document"),
            predicate=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
        )

        with self.assertRaises(SQLDataAccessInjectionError):
            inject_data_access_into_select(request)

    def test_join_can_target_configured_source_alias(self) -> None:
        sql, params = inject_data_access_into_select(
            SQLDataAccessInjectionRequest(
                sql="SELECT d.name, m.id FROM demo_documents d JOIN demo_document_members m ON m.document_id = d.id",
                params=(),
                resource=ResourceDescriptor(resource_key="demo.document"),
                predicate=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
                source_alias="d",
            )
        )

        self.assertIn("d.tenant_id = ?", sql)
        self.assertIn("d.owner_user_id = ?", sql)
        self.assertEqual(params, (7, 10))

    def test_relation_table_injects_exists_against_target_alias(self) -> None:
        sql, params = inject_data_access_into_select(
            SQLDataAccessInjectionRequest(
                sql="SELECT d.name FROM demo_documents d WHERE d.status = ?",
                params=("active",),
                resource=ResourceDescriptor(
                    resource_key="demo.document",
                    access_mode="relation_table",
                    relation_table="demo_document_members",
                    relation_resource_id_column="document_id",
                    relation_user_column="subject_user_id",
                ),
                predicate=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
                source_alias="d",
            )
        )

        self.assertIn("EXISTS", sql)
        self.assertIn("data_access_rel.document_id = d.id", sql)
        self.assertIn("data_access_rel.subject_user_id = ?", sql)
        self.assertEqual(params, ("active", 7, 7, 10))

    def test_inserts_scope_params_before_limit_placeholders(self) -> None:
        sql, params = inject_data_access_into_select(
            SQLDataAccessInjectionRequest(
                sql="SELECT d.name FROM demo_documents d WHERE d.status = ? ORDER BY d.id LIMIT ? OFFSET ?",
                params=("active", 20, 40),
                resource=ResourceDescriptor(resource_key="demo.document"),
                predicate=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
                source_alias="d",
            )
        )

        self.assertIn("LIMIT ? OFFSET ?", sql)
        self.assertEqual(params, ("active", 7, 10, 20, 40))


if __name__ == "__main__":
    unittest.main()
