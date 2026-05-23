from __future__ import annotations

from typing import Any

from identity_access.application import auth_service, tenant_service
from fastapi import HTTPException, status

from identity_access.application.ports import IdentityAccessRepository
from system.application.data_access import (
    ResourceDescriptor,
    current_user_primary_department_id,
    resolve_data_access_filter,
)


API_KEY_RESOURCE = ResourceDescriptor(resource_key="identity.api-key")
repository: IdentityAccessRepository | None = None


def configure_repository(identity_repository: IdentityAccessRepository) -> None:
    global repository
    repository = identity_repository


def repo() -> IdentityAccessRepository:
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identity_access repository is not configured",
        )
    return repository


def create_api_key(
    *,
    name: str,
    creator: str,
    tenant_id: int | None = None,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return repo().create_api_key(
        name=name,
        creator=creator,
        tenant_id=tenant_id,
        owner_user_id=current_user_id_or_none(current_user or {}),
        owner_department_id=current_user_primary_department_id(current_user or {}),
    )


def list_api_keys(
    tenant_id: int | None = None,
    current_user: dict[str, Any] | None = None,
    *,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> list[dict[str, Any]]:
    data_scope = (
        resolve_data_access_filter(current_user=current_user, resource=API_KEY_RESOURCE, action="read")
        if current_user is not None
        else None
    )
    return repo().list_api_keys(tenant_id=tenant_id, data_scope=data_scope, sort_by=sort_by, sort_dir=sort_dir)


def get_api_key(key_id: int) -> dict[str, Any] | None:
    return repo().get_api_key(key_id)


def update_api_key(key_id: int, *, name: str, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    user = current_user or {}
    return repo().update_api_key(
        key_id,
        name=name,
        editor=str(user.get("username", "") or ""),
        editor_id=current_user_id_or_none(user),
    )


def revoke_api_key(key_id: int) -> dict[str, Any]:
    return repo().revoke_api_key(key_id)


def validate_api_key(api_key: str) -> dict[str, Any] | None:
    return repo().validate_api_key(api_key)


def validate_user_bound_api_key(api_key: str) -> dict[str, Any] | None:
    principal = validate_api_key(api_key)
    if not principal:
        return None

    item = principal.get("api_key") or {}
    owner_user_id = int(item.get("owner_user_id") or item.get("creator_id") or 0)
    tenant_id = int(principal.get("tenant_id", 0) or 0)
    if not owner_user_id or not tenant_id:
        return None

    owner = auth_service.get_user(owner_user_id)
    if not owner or not bool(owner.get("is_active", True)):
        return None

    current_user = tenant_service.load_user_for_tenant(
        str(owner.get("username", "") or ""),
        tenant_id,
        auth_scope="tenant",
    )
    if not current_user or not bool(current_user.get("is_active", True)):
        return None

    tenant_payload = tenant_service.tenant_access_payload(current_user, tenant_id)
    current = tenant_payload.get("current_tenant")
    if not current:
        return None

    current_user.update(tenant_payload)
    current_user["tenant_id"] = int(current["id"])
    current_user["departments"] = tenant_service.user_departments_for_current_tenant(current_user)

    return {
        **principal,
        **tenant_payload,
        "auth_type": "api_key",
        "user": current_user,
        "tenant_id": int(current["id"]),
        "roles": current_user.get("roles", []),
        "permissions": current_user.get("permissions", []),
        "menus": current_user.get("menus", []),
        "departments": current_user.get("departments", []),
        "username": current_user.get("username"),
        "full_name": current_user.get("full_name", ""),
        "is_platform_admin": False,
        "is_tenant_admin": bool(current_user.get("is_tenant_admin", False)),
    }


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None
