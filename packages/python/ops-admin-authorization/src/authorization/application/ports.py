from __future__ import annotations

from typing import Any, Protocol

from authorization.domain.models import ResourceDescriptorRecord, RoleDataScope


class AuthorizationRepository(Protocol):
    def list_resource_descriptors(self) -> list[ResourceDescriptorRecord]: ...

    def upsert_resource_descriptor(self, payload: dict[str, Any], *, actor: str, actor_id: int | None) -> ResourceDescriptorRecord: ...

    def get_resource_descriptor(self, resource_key: str) -> ResourceDescriptorRecord | None: ...

    def list_role_data_scopes(self, *, role_key: str | None = None) -> list[RoleDataScope]: ...

    def save_role_data_scope(
        self,
        *,
        role_key: str,
        resource_key: str,
        action: str,
        scope: str,
        department_ids: list[int],
        actor: str,
        actor_id: int | None,
    ) -> RoleDataScope: ...

    def delete_role_data_scope(self, scope_id: int) -> RoleDataScope | None: ...
