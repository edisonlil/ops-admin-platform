from __future__ import annotations

import unittest

from system.application.data_access import (
    DataAccessDeniedError,
    DataAccessPredicate,
    ResourceDescriptor,
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
        resource = ResourceDescriptor(resource_key="demo.order")
        current_user = {"id": 7, "current_tenant": {"id": 3}}

        predicate = data_access_for(current_user, resource).write()

        self.assertEqual(predicate.tenant_id, 3)
        self.assertEqual(predicate.scope, SCOPE_SELF)
        self.assertEqual(predicate.user_id, 7)

    def test_apply_data_access_appends_scope_without_duplicate_tenant(self) -> None:
        resource = ResourceDescriptor(resource_key="demo.order")
        where = ["o.tenant_id = ?", "o.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF, user_id=7)

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="o")

        self.assertEqual(where, ["o.tenant_id = ?", "o.deleted = 0", "o.owner_user_id = ?"])
        self.assertEqual(params, [3, 7])

    def test_apply_self_and_subordinates_uses_owner_user_set(self) -> None:
        resource = ResourceDescriptor(resource_key="demo.order")
        where = ["o.tenant_id = ?", "o.deleted = 0"]
        params: list[object] = [3]
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF_AND_SUBORDINATES, user_id=7, user_ids=(7, 8, 9))

        apply_data_access(where, params, data_scope=predicate, resource=resource, alias="o")

        self.assertEqual(where, ["o.tenant_id = ?", "o.deleted = 0", "o.owner_user_id IN (?, ?, ?)"])
        self.assertEqual(params, [3, 7, 8, 9])

    def test_self_and_subordinates_record_check_uses_owner_user_set(self) -> None:
        resource = ResourceDescriptor(resource_key="demo.order")
        predicate = DataAccessPredicate(tenant_id=3, scope=SCOPE_SELF_AND_SUBORDINATES, user_id=7, user_ids=(7, 8))

        self.assertTrue(predicate.allows_record({"tenant_id": 3, "owner_user_id": 8}, resource))
        self.assertFalse(predicate.allows_record({"tenant_id": 3, "owner_user_id": 9}, resource))

    def test_ensure_data_access_record_raises_denied_error_by_default(self) -> None:
        configure_data_access_filter_provider(SelfOnlyProvider())
        resource = ResourceDescriptor(resource_key="demo.order")
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
