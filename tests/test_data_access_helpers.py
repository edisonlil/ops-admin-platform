from __future__ import annotations

import unittest

from system.application.data_access import (
    DataAccessDeniedError,
    DataAccessPredicate,
    ResourceDescriptor,
    SCOPE_DEPARTMENT,
    SCOPE_SELF,
    SCOPE_SELF_AND_SUBORDINATES,
    TenantOnlyDataAccessFilterProvider,
    apply_data_access,
    configure_data_access_filter_provider,
    data_access_for,
    data_owner_fields,
    ensure_data_access_record,
)


class SelfOnlyProvider:
    def resolve_filter(self, *, current_user: dict[str, object], resource: ResourceDescriptor, action: str) -> DataAccessPredicate:
        tenant = current_user.get("current_tenant") or {}
        return DataAccessPredicate(
            tenant_id=int(tenant.get("id") or current_user.get("tenant_id") or 0),
            scope=SCOPE_SELF,
            user_id=int(current_user.get("id") or 0),
        )


class DataAccessHelperTests(unittest.TestCase):
    def tearDown(self) -> None:
        configure_data_access_filter_provider(TenantOnlyDataAccessFilterProvider())

    def test_context_resolves_action_predicate(self) -> None:
        configure_data_access_filter_provider(SelfOnlyProvider())
        resource = ResourceDescriptor(resource_key="demo.document")
        current_user = {"id": 7, "current_tenant": {"id": 3}}

        predicate = data_access_for(current_user, resource).write()

        self.assertEqual(predicate.tenant_id, 3)
        self.assertEqual(predicate.scope, SCOPE_SELF)
        self.assertEqual(predicate.user_id, 7)

    def test_apply_data_access_appends_scope_without_duplicate_tenant(self) -> None:
        resource = ResourceDescriptor(resource_key="demo.document")
        where = ["o.tenant_id = ?", "o.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF, user_id=7)

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="o")

        self.assertEqual(where, ["o.tenant_id = ?", "o.deleted = 0", "o.owner_user_id = ?"])
        self.assertEqual(params, [3, 7])

    def test_apply_ai_application_self_scope_uses_creator_column(self) -> None:
        resource = ResourceDescriptor(resource_key="ai.application", owner_user_column="creator_id")
        where = ["tenant_id = ?", "deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF, user_id=7)

        apply_data_access(where, params, data_scope=predicate, resource=resource)

        self.assertEqual(where, ["tenant_id = ?", "deleted = 0", "creator_id = ?"])
        self.assertEqual(params, [3, 7])

    def test_apply_self_and_subordinates_uses_owner_user_set(self) -> None:
        resource = ResourceDescriptor(resource_key="demo.document")
        where = ["o.tenant_id = ?", "o.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF_AND_SUBORDINATES, user_id=7, user_ids=(7, 8, 9))

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="o")

        self.assertEqual(where, ["o.tenant_id = ?", "o.deleted = 0", "o.owner_user_id IN (?, ?, ?)"])
        self.assertEqual(params, [3, 7, 8, 9])

    def test_relation_table_self_uses_exists_predicate(self) -> None:
        resource = ResourceDescriptor(
            resource_key="demo.document",
            access_mode="relation_table",
            relation_table="demo_document_members",
            relation_resource_id_column="document_id",
            relation_user_column="subject_user_id",
            relation_tenant_column="tenant_id",
            relation_deleted_column="deleted",
        )
        where = ["d.tenant_id = ?", "d.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF, user_id=7)

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="d")

        self.assertEqual(len(where), 3)
        self.assertIn("EXISTS (SELECT 1 FROM demo_document_members data_access_rel", where[2])
        self.assertIn("data_access_rel.document_id = d.id", where[2])
        self.assertIn("data_access_rel.subject_user_id = ?", where[2])
        self.assertEqual(params, [3, 3, 7])

    def test_relation_table_self_and_subordinates_uses_user_set(self) -> None:
        resource = ResourceDescriptor(
            resource_key="demo.document",
            access_mode="relation_table",
            relation_table="demo_document_members",
            relation_resource_id_column="document_id",
            relation_user_column="subject_user_id",
        )
        where = ["d.tenant_id = ?", "d.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF_AND_SUBORDINATES, user_id=7, user_ids=(7, 8))

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="d")

        self.assertIn("data_access_rel.subject_user_id IN (?, ?)", where[-1])
        self.assertEqual(params, [3, 3, 7, 8])

    def test_relation_table_department_uses_department_set(self) -> None:
        resource = ResourceDescriptor(
            resource_key="demo.document",
            access_mode="relation_table",
            relation_table="demo_document_members",
            relation_resource_id_column="document_id",
            relation_department_column="subject_department_id",
        )
        where = ["d.tenant_id = ?", "d.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_DEPARTMENT, department_ids=(11, 12))

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="d")

        self.assertIn("data_access_rel.subject_department_id IN (?, ?)", where[-1])
        self.assertEqual(params, [3, 3, 11, 12])

    def test_relation_table_missing_configuration_fails_closed(self) -> None:
        resource = ResourceDescriptor(resource_key="demo.document", access_mode="relation_table")
        where = ["d.tenant_id = ?", "d.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF, user_id=7)

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="d")

        self.assertEqual(where, ["d.tenant_id = ?", "d.deleted = 0", "1 = 0"])
        self.assertEqual(params, [3])

    def test_relation_table_invalid_identifier_fails_closed(self) -> None:
        resource = ResourceDescriptor(
            resource_key="demo.document",
            access_mode="relation_table",
            relation_table="demo_document_members; DROP TABLE users",
            relation_resource_id_column="document_id",
            relation_user_column="subject_user_id",
        )
        where = ["d.tenant_id = ?", "d.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF, user_id=7)

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="d")

        self.assertEqual(where[-1], "1 = 0")
        self.assertEqual(params, [3])

    def test_self_and_subordinates_record_check_uses_owner_user_set(self) -> None:
        resource = ResourceDescriptor(resource_key="demo.document")
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF_AND_SUBORDINATES, user_id=7, user_ids=(7, 8))

        self.assertTrue(predicate.allows_record({"tenant_id": 3, "owner_user_id": 8}, resource))
        self.assertFalse(predicate.allows_record({"tenant_id": 3, "owner_user_id": 9}, resource))

    def test_ensure_data_access_record_raises_denied_error_by_default(self) -> None:
        configure_data_access_filter_provider(SelfOnlyProvider())
        resource = ResourceDescriptor(resource_key="demo.document")
        current_user = {"id": 7, "current_tenant": {"id": 3}}

        with self.assertRaises(DataAccessDeniedError):
            ensure_data_access_record(
                {"tenant_id": 3, "owner_user_id": 8},
                current_user=current_user,
                resource=resource,
                action="read",
            )

    def test_data_owner_fields_uses_primary_department(self) -> None:
        current_user = {
            "id": 7,
            "departments": [
                {"department_id": 11, "is_primary": False},
                {"department_id": 12, "is_primary": True},
            ],
        }

        self.assertEqual(data_owner_fields(current_user), {"owner_user_id": 7, "owner_department_id": 12})


if __name__ == "__main__":
    unittest.main()
