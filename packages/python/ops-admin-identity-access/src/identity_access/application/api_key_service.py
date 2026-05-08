from __future__ import annotations

from typing import Any

from identity_access.infrastructure.persistence import repositories


def create_api_key(*, name: str, created_by: str, tenant_id: int | None = None) -> dict[str, Any]:
    return repositories.create_api_key(name=name, created_by=created_by, tenant_id=tenant_id)


def list_api_keys(tenant_id: int | None = None) -> list[dict[str, Any]]:
    return repositories.list_api_keys(tenant_id=tenant_id)


def get_api_key(key_id: int) -> dict[str, Any] | None:
    return repositories.get_api_key(key_id)


def revoke_api_key(key_id: int) -> dict[str, Any]:
    return repositories.revoke_api_key(key_id)


def validate_api_key(api_key: str) -> dict[str, Any] | None:
    return repositories.validate_api_key(api_key)
