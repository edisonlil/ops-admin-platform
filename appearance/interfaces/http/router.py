from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

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


@router.put("/platform-branding", dependencies=[Depends(auth.require_platform_admin)])
def update_platform_branding(
    payload: PlatformBrandingRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(
        services.update_platform_branding(
            payload=payload.model_dump(by_alias=False),
            actor=str(current_user.get("username", "")),
        )
    )


@router.get("/themes", dependencies=[Depends(auth.require_platform_admin)])
def themes() -> dict[str, Any]:
    return ok(services.list_themes())


@router.post("/themes", dependencies=[Depends(auth.require_platform_admin)])
def create_theme(
    payload: TenantAppearanceThemeRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.create_theme(payload=payload.model_dump(by_alias=False), actor=str(current_user.get("username", ""))))


@router.get("/themes/{theme_id}", dependencies=[Depends(auth.require_platform_admin)])
def theme(theme_id: int) -> dict[str, Any]:
    return ok(services.get_theme(theme_id))


@router.put("/themes/{theme_id}", dependencies=[Depends(auth.require_platform_admin)])
def update_theme(
    theme_id: int,
    payload: TenantAppearanceThemeRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(
        services.update_theme(
            theme_id=theme_id,
            payload=payload.model_dump(by_alias=False),
            actor=str(current_user.get("username", "")),
        )
    )


@router.post("/themes/{theme_id}/publish", dependencies=[Depends(auth.require_platform_admin)])
def publish_theme(theme_id: int, current_user: dict[str, Any] = Depends(auth.require_platform_admin)) -> dict[str, Any]:
    return ok(services.publish_theme(theme_id=theme_id, actor=str(current_user.get("username", ""))))


@router.post("/themes/{theme_id}/disable", dependencies=[Depends(auth.require_platform_admin)])
def disable_theme(theme_id: int, current_user: dict[str, Any] = Depends(auth.require_platform_admin)) -> dict[str, Any]:
    return ok(services.disable_theme(theme_id=theme_id, actor=str(current_user.get("username", ""))))


@router.post("/themes/{theme_id}/platform-default", dependencies=[Depends(auth.require_platform_admin)])
def set_platform_default_theme(
    theme_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.set_platform_default_theme(theme_id=theme_id, actor=str(current_user.get("username", ""))))


@router.get("/tenants/{tenant_id}/theme", dependencies=[Depends(auth.require_tenant_admin_for_path())])
def tenant_theme(tenant_id: int) -> dict[str, Any]:
    return ok(services.tenant_theme_assignment(tenant_id))


@router.put("/tenants/{tenant_id}/theme", dependencies=[Depends(auth.require_tenant_admin_for_path())])
def assign_tenant_theme(
    tenant_id: int,
    payload: TenantThemeAssignmentRequest,
    current_user: dict[str, Any] = Depends(auth.require_tenant_admin_for_path()),
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
