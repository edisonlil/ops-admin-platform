from __future__ import annotations

from typing import Any

from organization.application.ports import OrganizationRepository
from organization.domain.exceptions import OrganizationDomainError
from organization.domain.exceptions import OrganizationNotFoundError, OrganizationStorageNotReadyError
from organization.domain.models import Department
from system.application.sorting import sort_dict_items


repository: OrganizationRepository | None = None
DEPARTMENT_SORT_COLUMNS = {
    "id": "id",
    "tenant_id": "tenant_id",
    "parent_id": "parent_id",
    "code": "code",
    "name": "name",
    "manager_user_id": "manager_user_id",
    "base_location": "base_location",
    "region": "region",
    "status": "status",
    "sort_order": "sort_order",
    "create_time": "create_time",
    "update_time": "update_time",
}


def configure_repository(organization_repository: OrganizationRepository) -> None:
    global repository
    repository = organization_repository


def repo() -> OrganizationRepository:
    if repository is None:
        raise OrganizationStorageNotReadyError("organization repository is not configured")
    return repository


def list_departments(
    *,
    tenant_id: int,
    include_disabled: bool = False,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    items = repo().list_departments(tenant_id=tenant_id, include_disabled=include_disabled)
    return {"items": sort_dict_items([department_to_dict(item) for item in items], sort_by, sort_dir, allowed=DEPARTMENT_SORT_COLUMNS)}


def save_department(payload: dict[str, Any], current_user: dict[str, Any], department_id: int | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    body = dict(payload)
    if department_id is not None:
        body["id"] = department_id
    item = repo().save_department(
        tenant_id=tenant_id,
        payload=body,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    return {"item": department_to_dict(item)}


def delete_department(*, department_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = repo().delete_department(
        tenant_id=current_tenant_id(current_user),
        department_id=department_id,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    if item is None:
        raise OrganizationNotFoundError("department not found")
    return {"id": department_id, "deleted": True}


def set_user_departments(
    *,
    tenant_id: int,
    user_id: int,
    department_ids: list[int],
    primary_department_id: int | None,
    current_user: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    actor = current_actor(current_user or {})
    actor_id = current_user_id_or_none(current_user or {})
    return repo().set_user_departments(
        tenant_id=tenant_id,
        user_id=user_id,
        department_ids=department_ids,
        primary_department_id=primary_department_id,
        actor=actor,
        actor_id=actor_id,
    )


def user_departments(*, tenant_id: int, user_id: int) -> list[dict[str, Any]]:
    return repo().user_departments(tenant_id=tenant_id, user_id=user_id)


def department_descendant_ids(*, tenant_id: int, department_id: int, include_self: bool = True) -> list[int]:
    departments = repo().list_departments(tenant_id=tenant_id, include_disabled=False)
    children_by_parent: dict[int | None, list[Department]] = {}
    for department in departments:
        children_by_parent.setdefault(department.parent_id, []).append(department)
    collected: list[int] = []
    pending = [department_id]
    while pending:
        current = pending.pop(0)
        if current in collected:
            continue
        if current != department_id or include_self:
            collected.append(current)
        pending.extend(item.id for item in children_by_parent.get(current, []))
    return collected


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current = current_user.get("current_tenant") or {}
    tenant_id = current.get("id") or current_user.get("tenant_id") or 0
    tenant_id = int(tenant_id or 0)
    if not tenant_id:
        raise OrganizationDomainError("tenant context required")
    return tenant_id


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None


def department_to_dict(item: Department) -> dict[str, Any]:
    return {
        "id": item.id,
        "tenant_id": item.tenant_id,
        "parent_id": item.parent_id,
        "code": item.code,
        "name": item.name,
        "manager_user_id": item.manager_user_id,
        "base_location": item.base_location,
        "region": item.region,
        "status": item.status,
        "sort_order": item.sort_order,
        "create_time": item.create_time,
        "update_time": item.update_time,
    }
