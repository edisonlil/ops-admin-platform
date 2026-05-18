from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from audit_logging.application import services
from audit_logging.interfaces.http.dtos import AuditLoggingSettingsRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import ok


router = APIRouter(prefix="/audit-logs")


@router.get("/system")
def system_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/operations")
def operation_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/apis")
def api_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/sql")
def sql_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            keyword=keyword,
            outcome=outcome,
            severity=severity,
        )
    )


@router.get("/visitors")
def visitor_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
