from __future__ import annotations

from typing import Any


class IdentityAccessMenuMountPort:
    """Application-layer adapter for identity_access menu operations."""

    def upsert_page_menu(self, payload: dict[str, Any]) -> dict[str, Any]:
        from identity_access.application import services as identity_services

        menu_key = str(payload["menu_key"])
        existing = next(
            (item for item in identity_services.list_menus(menu_scope=str(payload.get("menu_scope") or "tenant")) if item.get("key") == menu_key or item.get("menu_key") == menu_key),
            None,
        )
        values = {
            "menu_key": menu_key,
            "label": str(payload["label"]),
            "menu_type": "page",
            "menu_scope": str(payload.get("menu_scope") or "tenant"),
            "path": str(payload.get("path") or ""),
            "route_name": str(payload.get("route_name") or menu_key),
            "component": str(payload.get("component") or "/page-designer/runtime/index"),
            "icon": str(payload.get("icon") or "DashboardOutlined"),
            "parent_key": str(payload.get("parent_key") or "page-designer"),
            "permission_code": str(payload.get("permission_code") or "page_designer:page:view"),
            "sort_order": int(payload.get("sort_order") or 0),
            "is_visible": bool(payload.get("is_visible", True)),
        }
        if existing:
            return identity_services.update_menu(int(existing["id"]), **values)
        return identity_services.create_menu(**values)

    def delete_page_menu(self, menu_key: str) -> dict[str, Any] | None:
        from identity_access.application import services as identity_services

        existing = next((item for item in identity_services.list_menus() if item.get("key") == menu_key or item.get("menu_key") == menu_key), None)
        if not existing:
            return None
        return identity_services.delete_menu(int(existing["id"]))
