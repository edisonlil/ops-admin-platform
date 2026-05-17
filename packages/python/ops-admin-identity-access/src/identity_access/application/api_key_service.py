from __future__ import annotations

from typing import Any

from identity_access.infrastructure.persistence import repositories
from system.application.data_access import (
    ResourceDescriptor,
    current_user_primary_department_id,
    resolve_data_access_filter,
)


API_KEY_RESOURCE = ResourceDescriptor(resource_key="identity.api-key")


def create_api_key(
    *,
    name: str,
    creator: str,
    tenant_id: int | None = None,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return repositories.create_api_key(
        name=name,
        creator=creator,
        tenant_id=tenant_id,
        owner_user_id=current_user_id_or_none(current_user or {}),
        owner_department_id=current_user_primary_department_id(current_user or {}),
    )


def list_api_keys(tenant_id: int | None = None, current_user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    data_scope = (
        resolve_data_access_filter(current_user=current_user, resource=API_KEY_RESOURCE, action="read")
        if current_user is not None
        else None
    )
    return repositories.list_api_keys(tenant_id=tenant_id, data_scope=data_scope)


def get_api_key(key_id: int) -> dict[str, Any] | None:
    return repositories.get_api_key(key_id)


def revoke_api_key(key_id: int) -> dict[str, Any]:
    return repositories.revoke_api_key(key_id)


def validate_api_key(api_key: str) -> dict[str, Any] | None:
    return repositories.validate_api_key(api_key)


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None
