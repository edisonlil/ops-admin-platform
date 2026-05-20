from __future__ import annotations

from typing import Any

from identity_access.application.access_context_cache import clear_access_context_cache
from identity_access.infrastructure.persistence import repositories


def _after_access_context_change(payload: dict[str, Any]) -> dict[str, Any]:
    clear_access_context_cache()
    return payload


def list_users() -> list[dict[str, Any]]:
    return repositories.list_users()


def list_platform_users() -> list[dict[str, Any]]:
    return repositories.list_platform_users()


def create_user(
    *,
    username: str,
    password: str,
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    return _after_access_context_change(repositories.create_user(
        username=username,
        password=password,
        tenant_id=tenant_id,
        role_keys=role_keys,
        is_active=is_active,
        is_superuser=is_superuser,
    ))


def update_user(
    user_id: int,
    *,
    username: str,
    password: str = "",
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    return _after_access_context_change(repositories.update_user(
        user_id,
        username=username,
        password=password,
        tenant_id=tenant_id,
        role_keys=role_keys,
        is_active=is_active,
        is_superuser=is_superuser,
    ))


def set_user_active(user_id: int, is_active: bool) -> dict[str, Any]:
    return _after_access_context_change(repositories.set_user_active(user_id, is_active))


def list_roles() -> list[dict[str, Any]]:
    return repositories.list_roles()


def create_role(
    *,
    role_key: str,
    name: str,
    description: str = "",
    role_scope: str = "platform",
    menu_keys: list[str] | None = None,
) -> dict[str, Any]:
    return _after_access_context_change(repositories.create_role(
        role_key=role_key,
        name=name,
        description=description,
        role_scope=role_scope,
        menu_keys=menu_keys,
    ))


def update_role(
    role_id: int,
    *,
    role_key: str,
    name: str,
    description: str = "",
    menu_keys: list[str] | None = None,
) -> dict[str, Any]:
    return _after_access_context_change(repositories.update_role(
        role_id,
        role_key=role_key,
        name=name,
        description=description,
        menu_keys=menu_keys,
    ))


def update_role_menus(role_id: int, menu_keys: list[str]) -> dict[str, Any]:
    return _after_access_context_change(repositories.update_role_menus(role_id, menu_keys))


def delete_role(role_id: int) -> dict[str, Any]:
    return _after_access_context_change(repositories.delete_role(role_id))


def list_permissions() -> list[dict[str, str]]:
    return repositories.list_permissions()


def list_menus(menu_scope: str | None = None) -> list[dict[str, Any]]:
    return repositories.list_menus(menu_scope=menu_scope)


def create_menu(
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    menu_scope: str = "platform",
    path: str = "",
    route_name: str = "",
    component: str = "",
    icon: str = "",
    parent_key: str = "",
    permission_code: str = "",
    sort_order: int = 0,
    is_visible: bool = True,
) -> dict[str, Any]:
    return _after_access_context_change(repositories.create_menu(
        menu_key=menu_key,
        label=label,
        menu_scope=menu_scope,
        menu_type=menu_type,
        path=path,
        route_name=route_name,
        component=component,
        icon=icon,
        parent_key=parent_key,
        permission_code=permission_code,
        sort_order=sort_order,
        is_visible=is_visible,
    ))


def update_menu(
    menu_id: int,
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    menu_scope: str = "platform",
    path: str = "",
    route_name: str = "",
    component: str = "",
    icon: str = "",
    parent_key: str = "",
    permission_code: str = "",
    sort_order: int = 0,
    is_visible: bool = True,
) -> dict[str, Any]:
    return _after_access_context_change(repositories.update_menu(
        menu_id,
        menu_key=menu_key,
        label=label,
        menu_scope=menu_scope,
        menu_type=menu_type,
        path=path,
        route_name=route_name,
        component=component,
        icon=icon,
        parent_key=parent_key,
        permission_code=permission_code,
        sort_order=sort_order,
        is_visible=is_visible,
    ))


def delete_menu(menu_id: int) -> dict[str, Any]:
    return _after_access_context_change(repositories.delete_menu(menu_id))
