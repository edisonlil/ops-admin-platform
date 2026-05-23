from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from appearance.application.ports import AppearanceRepository
from appearance.domain.theme import AppearancePayload
from system.application.sorting import sort_dict_items


repository: AppearanceRepository | None = None
THEME_SORT_COLUMNS = {
    "id": "id",
    "tenant_id": "tenant_id",
    "name": "name",
    "status": "status",
    "effective_source": "effective_source",
    "create_time": "create_time",
    "update_time": "update_time",
}


def configure_repository(appearance_repository: AppearanceRepository) -> None:
    global repository
    repository = appearance_repository


def repo() -> AppearanceRepository:
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="appearance repository is not configured",
        )
    return repository


def list_themes(
    *,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status_filter: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    try:
        themes = repo().list_themes()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    items = filter_themes([theme.to_dict() for theme in themes], keyword=keyword, status_filter=status_filter)
    items = sort_dict_items(items, sort_by, sort_dir, allowed=THEME_SORT_COLUMNS)
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, int(page_size or 20))
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    return {"items": items[start:start + safe_page_size], "pagination": {"page": safe_page, "page_size": safe_page_size, "total": total}}


def filter_themes(items: list[dict[str, Any]], *, keyword: str | None, status_filter: str | None) -> list[dict[str, Any]]:
    text = str(keyword or "").strip().lower()
    normalized_status = str(status_filter or "").strip()
    if normalized_status == "all":
        normalized_status = ""
    return [
        item
        for item in items
        if (not normalized_status or str(item.get("status") or "draft") == normalized_status)
        and (
            not text
            or text in str(item.get("name") or "").lower()
            or text in str(item.get("preset_id") or item.get("presetId") or "default").lower()
        )
    ]


def get_theme(theme_id: int) -> dict[str, Any]:
    try:
        theme = repo().get_theme(theme_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="theme not found")
    return {"item": theme.to_dict()}


def get_platform_branding() -> dict[str, Any]:
    try:
        branding = repo().get_platform_branding()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"branding": branding.to_dict()}


def platform_default_theme() -> dict[str, Any]:
    return effective_theme_for_tenant(0)


def update_platform_branding(*, payload: dict[str, Any], actor: str) -> dict[str, Any]:
    platform_name = str(payload.get("platform_name") or payload.get("platformName") or "").strip()
    logo_url = str(payload.get("logo_url") if "logo_url" in payload else payload.get("logoUrl", "")).strip()
    platform_name_font_size = int(
        payload.get("platform_name_font_size") or payload.get("platformNameFontSize") or 20
    )
    try:
        branding = repo().save_platform_branding(
            platform_name=platform_name,
            logo_url=logo_url,
            platform_name_font_size=platform_name_font_size,
            actor=actor,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"branding": branding.to_dict()}


def create_theme(*, payload: dict[str, Any], actor: str) -> dict[str, Any]:
    name = str(payload.get("name") or "未命名主题").strip() or "未命名主题"
    appearance_payload = AppearancePayload.from_mapping(payload)
    try:
        theme = repo().create_theme(name=name, payload=appearance_payload, actor=actor)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"item": theme.to_dict()}


def update_theme(*, theme_id: int, payload: dict[str, Any], actor: str) -> dict[str, Any]:
    name = str(payload.get("name") or "未命名主题").strip() or "未命名主题"
    appearance_payload = AppearancePayload.from_mapping(payload)
    try:
        theme = repo().update_theme(theme_id=theme_id, name=name, payload=appearance_payload, actor=actor)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="theme not found")
    return {"item": theme.to_dict()}


def publish_theme(*, theme_id: int, actor: str) -> dict[str, Any]:
    try:
        theme = repo().publish_theme(theme_id=theme_id, actor=actor)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="theme not found")
    return {"item": theme.to_dict()}


def disable_theme(*, theme_id: int, actor: str) -> dict[str, Any]:
    try:
        theme = repo().disable_theme(theme_id=theme_id, actor=actor)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="theme not found")
    return {"item": theme.to_dict()}


def set_platform_default_theme(*, theme_id: int, actor: str) -> dict[str, Any]:
    try:
        theme = repo().assign_platform_default_theme(theme_id=theme_id, actor=actor)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="published theme not found")
    item = theme.to_dict()
    item["is_platform_default"] = True
    return {"item": item}


def tenant_theme_assignment(tenant_id: int) -> dict[str, Any]:
    try:
        theme = repo().get_tenant_assigned_theme(tenant_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"theme": theme.to_dict() if theme else None}


def assign_tenant_theme(*, tenant_id: int, theme_id: int | None, actor: str) -> dict[str, Any]:
    try:
        theme = repo().assign_theme_to_tenant(tenant_id=tenant_id, theme_id=theme_id, actor=actor)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if theme_id is not None and not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="published theme not found")
    return {"theme": theme.to_dict() if theme else None}


def effective_theme_for_tenant(tenant_id: int) -> dict[str, Any]:
    try:
        theme = repo().get_effective_tenant_theme(tenant_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not theme:
        return {"source": "builtin", "theme": None}
    theme_data = theme.to_dict()
    return {
        "source": str(theme_data.pop("effective_source", "") or ("tenant" if theme.tenant_id != 0 else "platform")),
        "theme": theme_data,
    }


def publish_tenant_theme(*, tenant_id: int, payload: dict[str, Any], actor: str) -> dict[str, Any]:
    if tenant_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant is required")
    appearance_payload = AppearancePayload.from_mapping(payload)
    name = str(payload.get("name") or "当前租户主题").strip() or "当前租户主题"
    try:
        theme = repo().save_published_tenant_theme(
            tenant_id=tenant_id,
            name=name,
            payload=appearance_payload,
            actor=actor,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {
        "source": "tenant",
        "theme": theme.to_dict(),
    }
