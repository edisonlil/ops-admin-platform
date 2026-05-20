from __future__ import annotations

from typing import Any

from audit_logging.application import dispatcher
from audit_logging.infrastructure.persistence import repositories
from system.application.data_access import ResourceDescriptor, data_access_for
from system.application.sorting import InvalidSortError


RESOURCE_BY_CATEGORY = {
    "system": ResourceDescriptor(resource_key="audit.system-log"),
    "operation": ResourceDescriptor(resource_key="audit.operation-log"),
    "api": ResourceDescriptor(resource_key="audit.api-log"),
    "sql": ResourceDescriptor(resource_key="audit.sql-log"),
    "visitor": ResourceDescriptor(resource_key="audit.visitor-log"),
}


def list_logs(
    *,
    category: str,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    tenant_id: int | None = None,
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    effective_tenant_id = requested_tenant_id(current_user, tenant_id=tenant_id)
    resource = RESOURCE_BY_CATEGORY[category]
    data_scope = data_access_for(current_user, resource).read()
    try:
        items, total = repositories.list_logs(
            category=category,
            tenant_id=effective_tenant_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            outcome=outcome,
            severity=severity,
            data_scope=data_scope,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except InvalidSortError as exc:
        raise ValueError(str(exc)) from exc
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total}}


def list_settings() -> dict[str, Any]:
    return {"items": [item.to_dict() for item in repositories.list_settings()]}


def get_effective_settings(tenant_id: int = 0) -> dict[str, Any]:
    return {"item": repositories.get_effective_settings(tenant_id).to_dict()}


def save_settings(tenant_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    item = repositories.save_settings(
        tenant_id=tenant_id,
        payload=payload,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    dispatcher.cache_settings(item)
    dispatcher.enqueue_log(
        "operation",
        {
            "tenant_id": 0,
            "event_action": "audit.settings.update",
            "event_outcome": "success",
            "severity": "warning",
            "source_module": "audit_logging",
            "actor_user_id": current_user_id_or_none(current_user),
            "actor_name": current_actor(current_user),
            "summary": f"更新租户 {tenant_id} 的日志配置",
            "resource_type": "audit_logging_settings",
            "resource_id": str(item.id),
            "risk_level": "high",
            "detail": {"tenant_id": tenant_id},
        },
        priority="high",
    )
    return {"item": item.to_dict()}


def stats() -> dict[str, Any]:
    return {"item": dispatcher.dispatcher_stats()}


def requested_tenant_id(current_user: dict[str, Any], *, tenant_id: int | None = None) -> int | None:
    if bool(current_user.get("is_platform_admin")):
        return int(tenant_id) if tenant_id else None
    current = current_user.get("current_tenant") or {}
    current_tenant_id = current.get("id") or current_user.get("tenant_id") or 0
    return int(current_tenant_id)


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None
