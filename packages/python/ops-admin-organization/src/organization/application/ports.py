from __future__ import annotations

from typing import Any, Protocol

from organization.domain.models import Department


class OrganizationRepository(Protocol):
    def list_departments(self, *, tenant_id: int, include_disabled: bool = False) -> list[Department]: ...

    def get_department(self, *, tenant_id: int, department_id: int) -> Department | None: ...

    def save_department(
        self,
        *,
        tenant_id: int,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> Department: ...

    def delete_department(self, *, tenant_id: int, department_id: int, actor: str, actor_id: int | None) -> Department | None: ...

    def set_user_departments(
        self,
        *,
        tenant_id: int,
        user_id: int,
        department_ids: list[int],
        primary_department_id: int | None,
        actor: str,
        actor_id: int | None,
    ) -> list[dict[str, Any]]: ...

    def set_users_departments_batch(
        self,
        rows: list[dict[str, Any]],
        *,
        actor: str,
        actor_id: int | None,
    ) -> None: ...

    def user_departments(self, *, tenant_id: int, user_id: int) -> list[dict[str, Any]]: ...

    def users_departments(self, *, tenant_id: int, user_ids: list[int]) -> dict[int, list[dict[str, Any]]]: ...
