from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from audit_logging.application import services
from audit_logging.application.dispatcher import record_visitor_log
from audit_logging.interfaces.http.dtos import AuditLoggingSettingsRequest, VisitorTrackRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import ok


router = APIRouter(prefix="/audit-logs")


@router.get("/system")
def system_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:system-log:view")),
) -> dict[str, Any]:
    return ok(
        services.list_logs(
            category="system",
            page=page,
            page_size=page_size,
            current_user=current_user,
            tenant_id=tenant_id,
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/operations")
def operation_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:operation-log:view")),
) -> dict[str, Any]:
    return ok(
        services.list_logs(
            category="operation",
            page=page,
            page_size=page_size,
            current_user=current_user,
            tenant_id=tenant_id,
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/apis")
def api_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:api-log:view")),
) -> dict[str, Any]:
    return ok(
        services.list_logs(
            category="api",
            page=page,
            page_size=page_size,
            current_user=current_user,
            tenant_id=tenant_id,
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/sql")
def sql_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:sql-log:view")),
) -> dict[str, Any]:
    return ok(
        services.list_logs(
            category="sql",
            page=page,
            page_size=page_size,
            current_user=current_user,
            tenant_id=tenant_id,
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/visitors")
def visitor_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:visitor-log:view")),
) -> dict[str, Any]:
    return ok(
        services.list_logs(
            category="visitor",
            page=page,
            page_size=page_size,
            current_user=current_user,
            tenant_id=tenant_id,
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/settings")
def settings(
    _: dict[str, Any] = Depends(auth.require_platform_permission("audit:settings:view")),
) -> dict[str, Any]:
    return ok(services.list_settings())


@router.get("/settings/effective")
def effective_settings(
    tenant_id: int = 0,
    _: dict[str, Any] = Depends(auth.require_platform_permission("audit:settings:view")),
) -> dict[str, Any]:
    return ok(services.get_effective_settings(tenant_id))


@router.put("/settings/{tenant_id}")
def update_settings(
    tenant_id: int,
    payload: AuditLoggingSettingsRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("audit:settings:manage")),
) -> dict[str, Any]:
    return ok(services.save_settings(tenant_id, payload.model_dump(), current_user))


@router.get("/stats")
def worker_stats(
    _: dict[str, Any] = Depends(auth.require_platform_permission("audit:settings:view")),
) -> dict[str, Any]:
    return ok(services.stats())


@router.post("/visitors/track")
def track_visitor(payload: VisitorTrackRequest, request: Request) -> dict[str, Any]:
    current_user = auth.optional_user_from_request(request)
    tenant_id = visitor_tenant_id(current_user)
    client_ip = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    path = payload.path or "/"
    record_visitor_log(
        {
            "tenant_id": tenant_id,
            "event_action": f"VISIT {path}",
            "event_outcome": "success",
            "severity": "info",
            "source_module": "web",
            "client_ip": client_ip,
            "user_agent": user_agent,
            "visitor_id": digest_or_empty(payload.visitor_id) or digest_or_empty(f"{client_ip}:{user_agent}"),
            "session_id_hash": digest_or_empty(payload.session_id),
            "ip_hash": digest_or_empty(client_ip),
            "device_type": payload.device_type,
            "browser": payload.browser,
            "os": payload.os,
            "referer": payload.referrer,
            "entry_path": path,
            "summary": f"访客访问 {payload.title or path}",
            "detail": {"title": payload.title},
        }
    )
    return ok({"accepted": True})


def visitor_tenant_id(current_user: dict[str, Any] | None) -> int:
    if not current_user:
        return 0
    current = current_user.get("current_tenant") or {}
    return int(current.get("id") or current_user.get("tenant_id") or 0)


def digest_or_empty(value: str) -> str:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
