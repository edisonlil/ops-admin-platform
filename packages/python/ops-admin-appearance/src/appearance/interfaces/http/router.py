from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from appearance.application import services
from appearance.interfaces.http.dtos import PlatformBrandingRequest, TenantAppearanceThemeRequest, TenantThemeAssignmentRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import ok


router = APIRouter(prefix="/appearance")


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current = current_user.get("current_tenant") or {}
    return int(current.get("id", 0) or 0)


@router.get("/effective-theme")
def effective_theme(current_user: dict[str, Any] = Depends(auth.require_user)) -> dict[str, Any]:
    return ok(services.effective_theme_for_tenant(current_tenant_id(current_user)))


@router.get("/platform-branding")
def platform_branding() -> dict[str, Any]:
    return ok(services.get_platform_branding())


@router.get("/platform-theme")
def platform_theme() -> dict[str, Any]:
    return ok(services.platform_default_theme())


@router.put("/platform-branding", dependencies=[Depends(auth.require_platform_permission("platform:branding:update"))])
def update_platform_branding(
    payload: PlatformBrandingRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("platform:branding:update")),
) -> dict[str, Any]:
    return ok(
        services.update_platform_branding(
            payload=payload.model_dump(by_alias=False),
            actor=str(current_user.get("username", "")),
        )
    )


@router.get("/themes", dependencies=[Depends(auth.require_platform_permission("appearance:access"))])
def themes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
) -> dict[str, Any]:
    return ok(services.list_themes(page=page, page_size=page_size, keyword=keyword, status_filter=status, sort_by=sort_by, sort_dir=sort_dir))


@router.post("/themes", dependencies=[Depends(auth.require_platform_permission("appearance:themes:create"))])
def create_theme(
    payload: TenantAppearanceThemeRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("appearance:themes:create")),
) -> dict[str, Any]:
    return ok(services.create_theme(payload=payload.model_dump(by_alias=False), actor=str(current_user.get("username", ""))))


@router.get("/themes/{theme_id}", dependencies=[Depends(auth.require_platform_permission("appearance:access"))])
def theme(theme_id: int) -> dict[str, Any]:
    return ok(services.get_theme(theme_id))


@router.put("/themes/{theme_id}", dependencies=[Depends(auth.require_platform_permission("appearance:themes:update"))])
def update_theme(
    theme_id: int,
    payload: TenantAppearanceThemeRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("appearance:themes:update")),
) -> dict[str, Any]:
    return ok(
        services.update_theme(
            theme_id=theme_id,
            payload=payload.model_dump(by_alias=False),
            actor=str(current_user.get("username", "")),
        )
    )


@router.post("/themes/{theme_id}/publish", dependencies=[Depends(auth.require_platform_permission("appearance:themes:publish"))])
def publish_theme(theme_id: int, current_user: dict[str, Any] = Depends(auth.require_platform_permission("appearance:themes:publish"))) -> dict[str, Any]:
    return ok(services.publish_theme(theme_id=theme_id, actor=str(current_user.get("username", ""))))


@router.post("/themes/{theme_id}/disable", dependencies=[Depends(auth.require_platform_permission("appearance:themes:disable"))])
def disable_theme(theme_id: int, current_user: dict[str, Any] = Depends(auth.require_platform_permission("appearance:themes:disable"))) -> dict[str, Any]:
    return ok(services.disable_theme(theme_id=theme_id, actor=str(current_user.get("username", ""))))


@router.post("/themes/{theme_id}/platform-default", dependencies=[Depends(auth.require_platform_permission("appearance:themes:set_default"))])
def set_platform_default_theme(
    theme_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("appearance:themes:set_default")),
) -> dict[str, Any]:
    return ok(services.set_platform_default_theme(theme_id=theme_id, actor=str(current_user.get("username", ""))))


@router.get("/tenants/{tenant_id}/theme", dependencies=[Depends(auth.require_platform_permission("tenant:access"))])
def tenant_theme(tenant_id: int) -> dict[str, Any]:
    return ok(services.tenant_theme_assignment(tenant_id))


@router.put("/tenants/{tenant_id}/theme", dependencies=[Depends(auth.require_platform_permission("tenant:theme:assign"))])
def assign_tenant_theme(
    tenant_id: int,
    payload: TenantThemeAssignmentRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("tenant:theme:assign")),
) -> dict[str, Any]:
    return ok(
        services.assign_tenant_theme(
            tenant_id=tenant_id,
            theme_id=payload.theme_id,
            actor=str(current_user.get("username", "")),
        )
    )


@router.put("/tenant-theme")
def publish_current_tenant_theme(
    payload: TenantAppearanceThemeRequest,
    current_user: dict[str, Any] = Depends(auth.require_current_tenant_admin),
) -> dict[str, Any]:
    return ok(
        services.publish_tenant_theme(
            tenant_id=current_tenant_id(current_user),
            payload=payload.model_dump(by_alias=False),
            actor=str(current_user.get("username", "")),
        )
    )
