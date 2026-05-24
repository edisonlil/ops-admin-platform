from __future__ import annotations

from typing import Any

from system.domain.events import DomainEvent


SOURCE = "identity_access"


def user_event_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": item.get("id"),
        "tenant_id": item.get("tenant_id"),
        "username": item.get("username"),
        "full_name": item.get("full_name", ""),
        "email": item.get("email", ""),
        "is_active": bool(item.get("is_active", True)),
        "is_superuser": bool(item.get("is_superuser", False)),
        "roles": item.get("roles", []),
        "department_ids": item.get("department_ids", []),
        "primary_department_id": item.get("primary_department_id"),
    }


def user_created(item: dict[str, Any], *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="identity.user_created",
        source=SOURCE,
        payload=user_event_payload(item),
        correlation_id=correlation_id,
    )


def user_updated(
    item: dict[str, Any],
    *,
    changed_fields: list[str] | None = None,
    correlation_id: str | None = None,
) -> DomainEvent:
    payload = user_event_payload(item)
    payload["changed_fields"] = list(changed_fields or [])
    return DomainEvent(
        event_type="identity.user_updated",
        source=SOURCE,
        payload=payload,
        correlation_id=correlation_id,
    )


def user_email_changed(
    item: dict[str, Any],
    *,
    old_email: str,
    new_email: str,
    correlation_id: str | None = None,
) -> DomainEvent:
    payload = user_event_payload(item)
    payload["old_email"] = old_email
    payload["new_email"] = new_email
    return DomainEvent(
        event_type="identity.user_email_changed",
        source=SOURCE,
        payload=payload,
        correlation_id=correlation_id,
    )


def user_logged_in(username: str, *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="identity.user_logged_in",
        source=SOURCE,
        payload={"username": username},
        correlation_id=correlation_id,
    )


def users_imported(items: list[dict[str, Any]], *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="identity.users_imported",
        source=SOURCE,
        payload={
            "count": len(items),
            "users": [user_event_payload(item) for item in items],
        },
        correlation_id=correlation_id,
    )


def api_key_created(item: dict[str, Any], *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="identity.api_key_created",
        source=SOURCE,
        payload={"api_key_id": item.get("id"), "name": item.get("name"), "creator": item.get("creator")},
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
