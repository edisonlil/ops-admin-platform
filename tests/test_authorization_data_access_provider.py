from __future__ import annotations

import unittest
from unittest import mock

from authorization.application import services
from authorization.domain.models import DATA_SCOPE_SELF, DataAccessPolicy
from system.application.data_access import ResourceDescriptor, SCOPE_SELF, SCOPE_TENANT


class FakeAuthorizationRepository:
    def __init__(self, policies: list[DataAccessPolicy]) -> None:
        self.policies = policies

    def list_data_access_policies(
        self,
        *,
        tenant_id: int,
        subject_type: str | None = None,
        subject_id: int | None = None,
        resource_key: str | None = None,
    ) -> list[DataAccessPolicy]:
        return [
            item
            for item in self.policies
            if item.tenant_id == tenant_id
            and (subject_type is None or item.subject_type == subject_type)
            and (subject_id is None or item.subject_id == subject_id)
            and (resource_key is None or item.resource_key == resource_key)
        ]


class BuiltinDataAccessFilterProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_repository = services.repository

    def tearDown(self) -> None:
        services.repository = self.previous_repository

    def test_non_admin_without_policy_falls_back_to_tenant_scope(self) -> None:
        services.configure_repository(FakeAuthorizationRepository([]))
        provider = services.BuiltinDataAccessFilterProvider()

        with mock.patch.object(services.organization_services, "user_departments", return_value=[]):
            predicate = provider.resolve_filter(
                current_user={"id": 7, "current_tenant": {"id": 3}, "is_tenant_admin": False},
                resource=ResourceDescriptor(resource_key="basic-data.dictionary"),
                action="read",
            )

        self.assertEqual(predicate.tenant_id, 3)
        self.assertEqual(predicate.scope, SCOPE_TENANT)
        self.assertEqual(predicate.user_id, 7)

    def test_matching_policy_still_applies_resource_scope(self) -> None:
        services.configure_repository(
            FakeAuthorizationRepository(
                [
                    DataAccessPolicy(
                        id=1,
                        tenant_id=3,
                        subject_type="user",
                        subject_id=7,
                        resource_key="basic-data.dictionary",
                        action="read",
                        scope=DATA_SCOPE_SELF,
                        department_ids=(),
                        priority=100,
                        create_time="",
                        update_time="",
                    )
                ]
            )
        )
        provider = services.BuiltinDataAccessFilterProvider()

        with mock.patch.object(services.organization_services, "user_departments", return_value=[]):
            predicate = provider.resolve_filter(
                current_user={"id": 7, "current_tenant": {"id": 3}, "is_tenant_admin": False},
                resource=ResourceDescriptor(resource_key="basic-data.dictionary"),
                action="read",
            )

        self.assertEqual(predicate.scope, SCOPE_SELF)

    def test_all_users_policy_applies_to_any_user_subject(self) -> None:
        services.configure_repository(
            FakeAuthorizationRepository(
                [
                    DataAccessPolicy(
                        id=1,
                        tenant_id=3,
                        subject_type="user",
                        subject_id=0,
                        resource_key="basic-data.dictionary",
                        action="read",
                        scope=DATA_SCOPE_SELF,
                        department_ids=(),
                        priority=100,
                        create_time="",
                        update_time="",
                    )
                ]
            )
        )
        provider = services.BuiltinDataAccessFilterProvider()

        with mock.patch.object(services.organization_services, "user_departments", return_value=[]):
            predicate = provider.resolve_filter(
                current_user={"id": 42, "current_tenant": {"id": 3}, "is_tenant_admin": False},
                resource=ResourceDescriptor(resource_key="basic-data.dictionary"),
                action="read",
            )

        self.assertEqual(predicate.scope, SCOPE_SELF)
        self.assertEqual(predicate.user_id, 42)

    def test_manage_policy_applies_to_read_requests(self) -> None:
        services.configure_repository(
            FakeAuthorizationRepository(
                [
                    DataAccessPolicy(
                        id=1,
                        tenant_id=3,
                        subject_type="user",
                        subject_id=7,
                        resource_key="basic-data.dictionary",
                        action="manage",
                        scope=DATA_SCOPE_SELF,
                        department_ids=(),
                        priority=100,
                        create_time="",
                        update_time="",
                    )
                ]
            )
        )
        provider = services.BuiltinDataAccessFilterProvider()

        with mock.patch.object(services.organization_services, "user_departments", return_value=[]):
            predicate = provider.resolve_filter(
                current_user={"id": 7, "current_tenant": {"id": 3}, "is_tenant_admin": False},
                resource=ResourceDescriptor(resource_key="basic-data.dictionary"),
                action="read",
            )

        self.assertEqual(predicate.scope, SCOPE_SELF)

    def test_configured_policy_for_uncovered_action_denies_access(self) -> None:
        services.configure_repository(
            FakeAuthorizationRepository(
                [
                    DataAccessPolicy(
                        id=1,
                        tenant_id=3,
                        subject_type="user",
                        subject_id=7,
                        resource_key="basic-data.dictionary",
                        action="read",
                        scope=DATA_SCOPE_SELF,
                        department_ids=(),
                        priority=100,
                        create_time="",
                        update_time="",
                    )
                ]
            )
        )
        provider = services.BuiltinDataAccessFilterProvider()

        with mock.patch.object(services.organization_services, "user_departments", return_value=[]):
            predicate = provider.resolve_filter(
                current_user={"id": 7, "current_tenant": {"id": 3}, "is_tenant_admin": False},
                resource=ResourceDescriptor(resource_key="basic-data.dictionary"),
                action="manage",
            )

        self.assertEqual(predicate.scope, "deny")


if __name__ == "__main__":
    unittest.main()
