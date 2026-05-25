from __future__ import annotations

from typing import Any

from page_designer.application.ports import MenuMountPort, PageDesignerRepository
from page_designer.domain.exceptions import PageDesignerDomainError, PageDesignerNotFoundError, PageDesignerStorageNotReadyError
from page_designer.domain.models import (
    DEFAULT_SCHEMA_VERSION,
    PAGE_TYPE_DASHBOARD,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    PageDefinition,
    PageVersion,
    default_dashboard_layout,
)


repository: PageDesignerRepository | None = None
menu_port: MenuMountPort | None = None


def configure_repository(page_repository: PageDesignerRepository) -> None:
    global repository
    repository = page_repository


def configure_menu_port(port: MenuMountPort) -> None:
    global menu_port
    menu_port = port


def repo() -> PageDesignerRepository:
    if repository is None:
        raise PageDesignerStorageNotReadyError("page designer repository is not configured")
    return repository


def menu_mount_port() -> MenuMountPort:
    if menu_port is None:
        raise PageDesignerStorageNotReadyError("page designer menu port is not configured")
    return menu_port


def list_pages(
    *,
    page: int,
    page_size: int,
    keyword: str,
    page_type: str | None,
    status: str | None,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    try:
        items, total = repo().list_pages(
            tenant_id=current_tenant_id(current_user),
            page=page,
            page_size=page_size,
            keyword=keyword,
            page_type=page_type or None,
            status=status or None,
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    return {"items": [item.to_dict() for item in items], "pagination": {"page": page, "page_size": page_size, "total": total}}


def create_page(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_page_payload(payload)
    try:
        item = repo().create_page(
            tenant_id=current_tenant_id(current_user),
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    return {"item": decorate_page_detail(item, None)}


def get_page(page_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    page = ensure_page(page_id=page_id, current_user=current_user)
    version = current_or_latest_version(page)
    return {"item": decorate_page_detail(page, version)}


def update_page(page_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    ensure_page(page_id=page_id, current_user=current_user)
    normalized = normalize_page_payload(payload, partial=True)
    try:
        page = repo().update_page(
            tenant_id=current_tenant_id(current_user),
            page_id=page_id,
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    if not page:
        raise PageDesignerNotFoundError("页面不存在")
    return {"item": decorate_page_detail(page, current_or_latest_version(page))}


def delete_page(page_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    page = ensure_page(page_id=page_id, current_user=current_user)
    if page.menu_mounted and page.menu_key:
        menu_mount_port().delete_page_menu(page.menu_key)
    try:
        deleted = repo().delete_page(
            tenant_id=current_tenant_id(current_user),
            page_id=page_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    if not deleted:
        raise PageDesignerNotFoundError("页面不存在")
    return {"id": page_id, "deleted": True}


def save_draft(page_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    page = ensure_page(page_id=page_id, current_user=current_user)
    normalized = normalize_version_payload(payload)
    try:
        version = repo().save_draft_version(
            tenant_id=current_tenant_id(current_user),
            page_id=page_id,
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    if not version:
        raise PageDesignerNotFoundError("页面不存在")
    return {"item": decorate_page_detail(page, version)}


def preview_page(page_id: int, payload: dict[str, Any] | None, current_user: dict[str, Any]) -> dict[str, Any]:
    page = ensure_page(page_id=page_id, current_user=current_user)
    if payload:
        version_payload = normalize_version_payload(payload)
        version = PageVersion(
            id=0,
            tenant_id=current_tenant_id(current_user),
            page_id=page.id,
            version_no=0,
            schema_version=str(version_payload.get("schema_version") or DEFAULT_SCHEMA_VERSION),
            layout=version_payload["layout"],
            components=version_payload["components"],
            data_bindings=version_payload["data_bindings"],
            interactions=version_payload["interactions"],
            status=STATUS_DRAFT,
        )
        version.validate(page.page_type)
    else:
        version = current_or_latest_version(page)
    if not version:
        raise PageDesignerNotFoundError("页面版本不存在")
    return runtime_payload(page, version, preview=True)


def publish_page(page_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    page = ensure_page(page_id=page_id, current_user=current_user)
    version = repo().latest_version(tenant_id=current_tenant_id(current_user), page_id=page.id, status=STATUS_DRAFT)
    if not version:
        version = repo().latest_version(tenant_id=current_tenant_id(current_user), page_id=page.id)
    if not version:
        raise PageDesignerNotFoundError("页面版本不存在")
    version.validate(page.page_type)
    try:
        published = repo().publish_page(
            tenant_id=current_tenant_id(current_user),
            page_id=page.id,
            version_id=version.id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    if not published:
        raise PageDesignerNotFoundError("页面不存在")
    return {"item": decorate_page_detail(published, repo().get_version(tenant_id=current_tenant_id(current_user), version_id=version.id))}


def unpublish_page(page_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    ensure_page(page_id=page_id, current_user=current_user)
    try:
        page = repo().unpublish_page(
            tenant_id=current_tenant_id(current_user),
            page_id=page_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    if not page:
        raise PageDesignerNotFoundError("页面不存在")
    return {"item": decorate_page_detail(page, current_or_latest_version(page))}


def mount_menu(page_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    page = ensure_page(page_id=page_id, current_user=current_user)
    if page.status != STATUS_PUBLISHED:
        raise PageDesignerDomainError("只有已发布页面可以挂载到菜单")
    normalized = normalize_mount_payload(page, payload)
    menu_item = menu_mount_port().upsert_page_menu(normalized)
    try:
        mount = repo().save_menu_mount(
            tenant_id=current_tenant_id(current_user),
            page_id=page.id,
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    return {"item": {"mount": mount, "menu": menu_item}}


def unmount_menu(page_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    page = ensure_page(page_id=page_id, current_user=current_user)
    if page.menu_key:
        menu_mount_port().delete_page_menu(page.menu_key)
    try:
        mount = repo().delete_menu_mount(
            tenant_id=current_tenant_id(current_user),
            page_id=page.id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    return {"item": {"unmounted": True, "mount": mount}}


def runtime_page(page_key: str, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        page = repo().get_page_by_key(tenant_id=tenant_id, page_key=page_key)
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    if not page or page.status != STATUS_PUBLISHED or not page.current_version_id:
        raise PageDesignerNotFoundError("页面不存在或未发布")
    version = repo().get_version(tenant_id=tenant_id, version_id=page.current_version_id)
    if not version or version.status != STATUS_PUBLISHED:
        raise PageDesignerNotFoundError("页面版本不存在或未发布")
    return runtime_payload(page, version, preview=False)


def ensure_page(*, page_id: int, current_user: dict[str, Any]) -> PageDefinition:
    try:
        page = repo().get_page(tenant_id=current_tenant_id(current_user), page_id=page_id)
    except RuntimeError as exc:
        raise PageDesignerStorageNotReadyError(str(exc)) from exc
    if not page:
        raise PageDesignerNotFoundError("页面不存在")
    return page


def current_or_latest_version(page: PageDefinition) -> PageVersion | None:
    tenant_id = page.tenant_id
    if page.current_version_id:
        version = repo().get_version(tenant_id=tenant_id, version_id=page.current_version_id)
        if version:
            return version
    return repo().latest_version(tenant_id=tenant_id, page_id=page.id)


def decorate_page_detail(page: PageDefinition, version: PageVersion | None) -> dict[str, Any]:
    payload = page.to_dict()
    payload["version"] = version.to_dict() if version else None
    return payload


def runtime_payload(page: PageDefinition, version: PageVersion, *, preview: bool) -> dict[str, Any]:
    return {
        "item": {
            "page": page.to_dict(),
            "version": version.to_dict(),
            "runtime": {
                "preview": preview,
                "page_key": page.page_key,
                "page_type": page.page_type,
                "schema_version": version.schema_version,
                "layout": version.layout,
                "components": version.components,
                "data_bindings": version.data_bindings,
                "interactions": version.interactions,
            },
        }
    }


def normalize_page_payload(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    data = {
        "page_key": str(payload.get("page_key") or "").strip(),
        "name": str(payload.get("name") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "page_type": str(payload.get("page_type") or PAGE_TYPE_DASHBOARD).strip(),
        "thumbnail_file_id": int(payload.get("thumbnail_file_id") or 0) or None,
        "settings": payload.get("settings") if isinstance(payload.get("settings"), dict) else {},
    }
    if partial:
        return {key: value for key, value in data.items() if value not in ("", None, {}) or key in payload}
    return data


def normalize_version_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": str(payload.get("schema_version") or DEFAULT_SCHEMA_VERSION),
        "layout": payload.get("layout") if isinstance(payload.get("layout"), dict) else default_dashboard_layout(),
        "components": payload.get("components") if isinstance(payload.get("components"), list) else [],
        "data_bindings": payload.get("data_bindings") if isinstance(payload.get("data_bindings"), dict) else {},
        "interactions": payload.get("interactions") if isinstance(payload.get("interactions"), dict) else {},
    }


def normalize_mount_payload(page: PageDefinition, payload: dict[str, Any]) -> dict[str, Any]:
    menu_key = str(payload.get("menu_key") or f"page-designer-runtime-{page.page_key}").strip()
    path = str(payload.get("path") or f"/page-designer/runtime/{page.page_key}").strip()
    route_name = str(payload.get("route_name") or menu_key).strip()
    label = str(payload.get("label") or page.name).strip()
    parent_key = str(payload.get("parent_key") or "page-designer").strip()
    return {
        "menu_key": menu_key,
        "label": label,
        "menu_scope": "tenant",
        "path": path,
        "route_name": route_name,
        "component": "/page-designer/runtime/index",
        "icon": str(payload.get("icon") or "DashboardOutlined"),
        "parent_key": parent_key,
        "permission_code": str(payload.get("permission_code") or "page_designer:page:view"),
        "sort_order": int(payload.get("sort_order") or 869),
        "is_visible": True,
    }


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current_tenant = current_user.get("current_tenant") or {}
    tenant_id = current_tenant.get("id") or current_user.get("tenant_id") or 1
    return int(tenant_id)


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None
