from __future__ import annotations

from typing import Any, Protocol

from authorization.domain.models import DataAccessPolicy, ResourceDescriptorRecord


class AuthorizationRepository(Protocol):
    def list_resource_descriptors(self) -> list[ResourceDescriptorRecord]: ...

    def upsert_resource_descriptor(self, payload: dict[str, Any], *, actor: str, actor_id: int | None) -> ResourceDescriptorRecord: ...

    def get_resource_descriptor(self, resource_key: str) -> ResourceDescriptorRecord | None: ...

    def list_data_access_policies(
        self,
        *,
        tenant_id: int,
        subject_type: str | None = None,
        subject_id: int | None = None,
        resource_key: str | None = None,
    ) -> list[DataAccessPolicy]: ...

    def save_data_access_policy(
        self,
        *,
        tenant_id: int,
        subject_type: str,
        subject_id: int,
        resource_key: str,
        action: str,
        scope: str,
        department_ids: list[int],
        priority: int,
        actor: str,
        actor_id: int | None,
    ) -> DataAccessPolicy: ...

    def delete_data_access_policy(self, *, tenant_id: int, policy_id: int) -> DataAccessPolicy | None: ...
