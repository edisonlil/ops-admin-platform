from __future__ import annotations

from typing import Any

from system.domain.events import DomainEvent


SOURCE = "identity_access"


def user_logged_in(username: str, *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="identity.user_logged_in",
        source=SOURCE,
        payload={"username": username},
        correlation_id=correlation_id,
    )


def api_key_created(item: dict[str, Any], *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="identity.api_key_created",
        source=SOURCE,
        payload={"api_key_id": item.get("id"), "name": item.get("name"), "created_by": item.get("created_by")},
        correlation_id=correlation_id,
    )


def role_permissions_changed(role_id: int, *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="identity.role_permissions_changed",
        source=SOURCE,
        payload={"role_id": role_id},
        correlation_id=correlation_id,
    )


def role_deleted(role_id: int, *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="identity.role_deleted",
        source=SOURCE,
        payload={"role_id": role_id},
        correlation_id=correlation_id,
    )
