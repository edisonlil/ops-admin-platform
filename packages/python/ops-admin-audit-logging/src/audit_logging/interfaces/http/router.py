from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from audit_logging.application import services
from audit_logging.application.dispatcher import record_visitor_log
from audit_logging.interfaces.http.dtos import AuditLoggingSettingsRequest, VisitorTrackRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import current_request_id, error_response, ok


router = APIRouter(prefix="/audit-logs")


@router.get("/system")
def system_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:system-log:view")),
) -> dict[str, Any]:
    return list_logs_response(
        category="system",
        page=page,
        page_size=page_size,
        current_user=current_user,
        tenant_id=tenant_id,
        keyword=keyword,
        outcome=outcome,
        severity=severity,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def list_logs_response(**kwargs: Any) -> dict[str, Any]:
    try:
        return ok(services.list_logs(**kwargs))
    except ValueError as exc:
        return error_response(status_code=400, code="INVALID_SORT", message=str(exc))


@router.get("/operations")
def operation_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:operation-log:view")),
) -> dict[str, Any]:
    return list_logs_response(
        category="operation",
        page=page,
        page_size=page_size,
        current_user=current_user,
        tenant_id=tenant_id,
        keyword=keyword,
        outcome=outcome,
        severity=severity,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/apis")
def api_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:api-log:view")),
) -> dict[str, Any]:
    return list_logs_response(
        category="api",
        page=page,
        page_size=page_size,
        current_user=current_user,
        tenant_id=tenant_id,
        keyword=keyword,
        outcome=outcome,
        severity=severity,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/sql")
def sql_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:sql-log:view")),
) -> dict[str, Any]:
    return list_logs_response(
        category="sql",
        page=page,
        page_size=page_size,
        current_user=current_user,
        tenant_id=tenant_id,
        keyword=keyword,
        outcome=outcome,
        severity=severity,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/visitors")
def visitor_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: int | None = Query(default=None, ge=1),
    keyword: str = "",
    outcome: str = "",
    severity: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("audit:visitor-log:view")),
) -> dict[str, Any]:
    return list_logs_response(
        category="visitor",
        page=page,
        page_size=page_size,
        current_user=current_user,
        tenant_id=tenant_id,
        keyword=keyword,
        outcome=outcome,
        severity=severity,
        sort_by=sort_by,
        sort_dir=sort_dir,
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
            "request_id": current_request_id(),
            "event_action": f"VISIT {path}",
            "event_outcome": "success",
            "severity": "info",
            "source_module": "web",
            "actor_user_id": visitor_actor_user_id(current_user),
            "actor_name": visitor_actor_name(current_user),
            "actor_type": visitor_actor_type(current_user),
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


def visitor_actor_user_id(current_user: dict[str, Any] | None) -> int | None:
    if not current_user:
        return None
    user_id = current_user.get("id")
    return int(user_id) if user_id is not None else None


def visitor_actor_name(current_user: dict[str, Any] | None) -> str:
    if not current_user:
        return ""
    return str(current_user.get("username") or current_user.get("name") or "")


def visitor_actor_type(current_user: dict[str, Any] | None) -> str:
    if not current_user:
        return "anonymous"
    return "user"


def digest_or_empty(value: str) -> str:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
