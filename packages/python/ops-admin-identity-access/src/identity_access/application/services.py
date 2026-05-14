from __future__ import annotations

from typing import Any

from fastapi import Response

from identity_access.application import api_key_service, auth_service, rbac_service, tenant_service
from identity_access.domain import events
from system.application.event_bus import publish_event
from system.interfaces.http import current_request_id


def authenticate(
    username: str,
    password: str,
    response: Response | None = None,
    *,
    tenant_key: str = "default",
) -> dict[str, Any] | None:
    normalized_tenant_key = (tenant_key or "default").strip()
    if normalized_tenant_key == tenant_service.PLATFORM_TENANT_KEY:
        user = auth_service.authenticate_platform_admin(username, password)
        if not user:
            return None
        user["auth_scope"] = "platform"
        tenant_payload = tenant_service.tenant_access_payload(user)
        token = auth_service.create_access_token(
            user["username"],
            auth_scope="platform",
            user_id=int(user.get("id", 0) or 0),
        )
        if response is not None:
            auth_service.set_login_cookie(response, token)
        publish_event(events.user_logged_in(str(user["username"]), correlation_id=current_request_id()))
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user["username"],
            "expires_in": auth_service.ACCESS_TOKEN_EXPIRE_SECONDS,
            "roles": user.get("roles", []),
            "permissions": user.get("permissions", []),
            "menus": user.get("menus", []),
            **tenant_payload,
        }
    tenant = tenant_service.get_tenant_by_key(tenant_key)
    if not tenant:
        return None
    user = auth_service.authenticate_user(username, password, tenant_id=int(tenant["id"]))
    if not user:
        return None
    membership = tenant_service.membership_for_user_in_tenant(int(user.get("id", 0) or 0), int(tenant["id"]))
    if membership:
        user = auth_service.public_user(
            user,
            tenant_id=int(tenant["id"]),
            auth_scope="tenant",
            is_tenant_admin=bool(membership.get("is_tenant_admin", False)),
        )
        user["auth_scope"] = "tenant"
    tenant_payload = tenant_service.tenant_access_payload(user)
    token = auth_service.create_access_token(
        user["username"],
        tenant_id=int(tenant_payload["current_tenant"]["id"]),
        auth_scope="tenant",
        user_id=int(user.get("id", 0) or 0),
    )
    if response is not None:
        auth_service.set_login_cookie(response, token)
    publish_event(events.user_logged_in(str(user["username"]), correlation_id=current_request_id()))
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "expires_in": auth_service.ACCESS_TOKEN_EXPIRE_SECONDS,
        "roles": user.get("roles", []),
        "permissions": user.get("permissions", []),
        "menus": user.get("menus", []),
        **tenant_payload,
    }


def login_for_admin(username: str, password: str, response: Response, *, tenant_key: str = "default") -> dict[str, Any] | None:
    normalized_tenant_key = (tenant_key or "default").strip()
    if normalized_tenant_key == tenant_service.PLATFORM_TENANT_KEY:
        user = auth_service.authenticate_platform_admin(username, password)
        if not user:
            return None
        user["auth_scope"] = "platform"
        tenant_payload = tenant_service.tenant_access_payload(user)
        token = auth_service.create_access_token(
            user["username"],
            auth_scope="platform",
            user_id=int(user.get("id", 0) or 0),
        )
        auth_service.set_login_cookie(response, token)
        publish_event(events.user_logged_in(str(user["username"]), correlation_id=current_request_id()))
        return {
            "token": token,
            "username": user["username"],
            "avatar": "",
            "permissions": scaffold_permissions(list(user.get("permissions", []))),
            "roles": user.get("roles", []),
            "menus": user.get("menus", []),
            **tenant_payload,
        }
    tenant = tenant_service.get_tenant_by_key(tenant_key)
    if not tenant:
        return None
    user = auth_service.authenticate_user(username, password, tenant_id=int(tenant["id"]))
    if not user:
        return None
    membership = tenant_service.membership_for_user_in_tenant(int(user.get("id", 0) or 0), int(tenant["id"]))
    if membership:
        user = auth_service.public_user(
            user,
            tenant_id=int(tenant["id"]),
            auth_scope="tenant",
            is_tenant_admin=bool(membership.get("is_tenant_admin", False)),
        )
        user["auth_scope"] = "tenant"
    tenant_payload = tenant_service.tenant_access_payload(user)
    token = auth_service.create_access_token(
        user["username"],
        tenant_id=int(tenant_payload["current_tenant"]["id"]),
        auth_scope="tenant",
        user_id=int(user.get("id", 0) or 0),
    )
    auth_service.set_login_cookie(response, token)
    publish_event(events.user_logged_in(str(user["username"]), correlation_id=current_request_id()))
    return {
        "token": token,
        "username": user["username"],
        "avatar": "",
        "permissions": scaffold_permissions(list(user.get("permissions", []))),
        "roles": user.get("roles", []),
        "menus": user.get("menus", []),
        **tenant_payload,
    }


def logout(response: Response) -> bool:
    auth_service.clear_login_cookie(response)
    return True


def scaffold_permissions(permission_codes: list[str]) -> list[dict[str, str]]:
    catalog = {item["code"]: item for item in rbac_service.list_permissions()}
    return [
        {
            "label": catalog.get(code, {}).get("name", code),
            "value": code,
        }
        for code in permission_codes
    ]


def scaffold_user(current_user: dict[str, Any]) -> dict[str, Any]:
    roles = current_user.get("roles", [])
    payload = {
        "username": str(current_user.get("username", "")),
        "email": "",
        "avatar": "",
        "roles": [
            {
                "label": str(role.get("name", role.get("key", ""))),
                "value": str(role.get("key", "")),
            }
            for role in roles
        ],
        "permissions": scaffold_permissions(list(current_user.get("permissions", []))),
        "menus": current_user.get("menus", []),
    }
    current_tenant_id = None if bool(current_user.get("is_platform_admin", False)) else current_user.get("tenant_id")
    payload.update(tenant_service.tenant_access_payload(current_user, current_tenant_id))
    return payload


def switch_tenant(
    username: str,
    tenant_id: int,
    response: Response | None = None,
    *,
    auth_scope: str = "tenant",
) -> dict[str, Any]:
    return tenant_service.switch_tenant(username, tenant_id, response=response, auth_scope=auth_scope)


def list_tenants(q: str | None = None) -> list[dict[str, Any]]:
    return tenant_service.list_tenants(q=q)


def create_tenant(payload: dict[str, Any]) -> dict[str, Any]:
    return tenant_service.create_tenant(payload)


def update_tenant(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return tenant_service.update_tenant(tenant_id, payload)


def activate_tenant(tenant_id: int) -> dict[str, Any]:
    return tenant_service.activate_tenant(tenant_id)


def suspend_tenant(tenant_id: int) -> dict[str, Any]:
    return tenant_service.suspend_tenant(tenant_id)


def list_tenant_users(tenant_id: int) -> list[dict[str, Any]]:
    return tenant_service.list_tenant_users(tenant_id)


def create_tenant_user(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return tenant_service.create_tenant_user(tenant_id, payload)


def update_tenant_user(tenant_id: int, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return tenant_service.update_tenant_user(tenant_id, user_id, payload)


def set_tenant_user_active(tenant_id: int, user_id: int, is_active: bool) -> dict[str, Any]:
    return tenant_service.set_tenant_user_active(tenant_id, user_id, is_active)


def list_users() -> list[dict[str, Any]]:
    return [enrich_user_with_departments(item) for item in rbac_service.list_users()]


def create_user(
    *,
    username: str,
    password: str,
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    department_ids: list[int] | None = None,
    primary_department_id: int | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    user = rbac_service.create_user(
        username=username,
        password=password,
        tenant_id=tenant_id,
        role_keys=role_keys,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    sync_user_departments_if_available(user, department_ids or [], primary_department_id)
    return enrich_user_with_departments(user)


def update_user(
    user_id: int,
    *,
    username: str,
    password: str = "",
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    department_ids: list[int] | None = None,
    primary_department_id: int | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    user = rbac_service.update_user(
        user_id,
        username=username,
        password=password,
        tenant_id=tenant_id,
        role_keys=role_keys,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    sync_user_departments_if_available(user, department_ids or [], primary_department_id)
    return enrich_user_with_departments(user)


def set_user_active(user_id: int, is_active: bool) -> dict[str, Any]:
    return rbac_service.set_user_active(user_id, is_active)


def list_roles() -> list[dict[str, Any]]:
    return [enrich_role_with_data_scopes(item) for item in rbac_service.list_roles()]


def create_role(
    *,
    role_key: str,
    name: str,
    description: str = "",
    role_scope: str = "platform",
    menu_keys: list[str] | None = None,
    data_scopes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    role = rbac_service.create_role(
        role_key=role_key,
        name=name,
        description=description,
        role_scope=role_scope,
        menu_keys=menu_keys,
    )
    sync_role_data_scopes_if_available(role, data_scopes or [])
    publish_event(events.role_permissions_changed(int(role["id"]), correlation_id=current_request_id()))
    return enrich_role_with_data_scopes(role)


def update_role(
    role_id: int,
    *,
    role_key: str,
    name: str,
    description: str = "",
    menu_keys: list[str] | None = None,
    data_scopes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    role = rbac_service.update_role(
        role_id,
        role_key=role_key,
        name=name,
        description=description,
        menu_keys=menu_keys,
    )
    sync_role_data_scopes_if_available(role, data_scopes or [])
    publish_event(events.role_permissions_changed(role_id, correlation_id=current_request_id()))
    return enrich_role_with_data_scopes(role)


def update_role_menus(role_id: int, menu_keys: list[str]) -> dict[str, Any]:
    role = rbac_service.update_role_menus(role_id, menu_keys)
    publish_event(events.role_permissions_changed(role_id, correlation_id=current_request_id()))
    return role


def delete_role(role_id: int) -> dict[str, Any]:
    role = rbac_service.delete_role(role_id)
    publish_event(events.role_deleted(role_id, correlation_id=current_request_id()))
    return role


def list_permissions() -> list[dict[str, str]]:
    return rbac_service.list_permissions()


def list_menus() -> list[dict[str, Any]]:
    return rbac_service.list_menus()


def sync_user_departments_if_available(user: dict[str, Any], department_ids: list[int], primary_department_id: int | None) -> None:
    if not department_ids and not primary_department_id:
        return
    try:
        from organization.application import services as organization_services
    except Exception:
        return
    tenant_id = int(user.get("tenant_id", 0) or 0)
    user_id = int(user.get("id", 0) or 0)
    if not tenant_id or not user_id:
        return
    organization_services.set_user_departments(
        tenant_id=tenant_id,
        user_id=user_id,
        department_ids=department_ids,
        primary_department_id=primary_department_id,
        current_user={"username": "system", "id": None},
    )


def enrich_user_with_departments(user: dict[str, Any]) -> dict[str, Any]:
    try:
        from organization.application import services as organization_services
    except Exception:
        return user
    tenant_id = int(user.get("tenant_id", 0) or 0)
    user_id = int(user.get("id", 0) or 0)
    if not tenant_id or not user_id:
        return user
    try:
        departments = organization_services.user_departments(tenant_id=tenant_id, user_id=user_id)
    except Exception:
        return user
    item = dict(user)
    item["departments"] = departments
    primary = next((department for department in departments if bool(department.get("is_primary"))), departments[0] if departments else None)
    item["department_ids"] = [int(department["department_id"]) for department in departments]
    item["primary_department_id"] = int(primary["department_id"]) if primary else None
    return item


def sync_role_data_scopes_if_available(role: dict[str, Any], data_scopes: list[dict[str, Any]]) -> None:
    if not data_scopes:
        return
    try:
        from authorization.application import services as authorization_services
    except Exception:
        return
    role_key = str(role.get("key") or role.get("role_key") or "")
    if not role_key:
        return
    for scope in data_scopes:
        payload = dict(scope)
        payload["role_key"] = role_key
        authorization_services.save_role_data_scope(payload, {"username": "system", "id": None})


def enrich_role_with_data_scopes(role: dict[str, Any]) -> dict[str, Any]:
    try:
        from authorization.application import services as authorization_services
    except Exception:
        return role
    role_key = str(role.get("key") or role.get("role_key") or "")
    if not role_key:
        return role
    try:
        payload = authorization_services.list_role_data_scopes(role_key=role_key)
    except Exception:
        return role
    item = dict(role)
    item["data_scopes"] = payload.get("items", [])
    return item


def create_menu(
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    path: str = "",
    route_name: str = "",
    component: str = "",
    icon: str = "",
    parent_key: str = "",
    permission_code: str = "",
    sort_order: int = 0,
    is_visible: bool = True,
) -> dict[str, Any]:
    return rbac_service.create_menu(
        menu_key=menu_key,
        label=label,
        menu_type=menu_type,
        path=path,
        route_name=route_name,
        component=component,
        icon=icon,
        parent_key=parent_key,
        permission_code=permission_code,
        sort_order=sort_order,
        is_visible=is_visible,
    )


def update_menu(
    menu_id: int,
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    path: str = "",
    route_name: str = "",
    component: str = "",
    icon: str = "",
    parent_key: str = "",
    permission_code: str = "",
    sort_order: int = 0,
    is_visible: bool = True,
) -> dict[str, Any]:
    return rbac_service.update_menu(
        menu_id,
        menu_key=menu_key,
        label=label,
        menu_type=menu_type,
        path=path,
        route_name=route_name,
        component=component,
        icon=icon,
        parent_key=parent_key,
        permission_code=permission_code,
        sort_order=sort_order,
        is_visible=is_visible,
    )


def delete_menu(menu_id: int) -> dict[str, Any]:
    return rbac_service.delete_menu(menu_id)


def create_api_key(*, name: str, creator: str, tenant_id: int | None = None) -> dict[str, Any]:
    payload = api_key_service.create_api_key(name=name, creator=creator, tenant_id=tenant_id)
    publish_event(events.api_key_created(payload["item"], correlation_id=current_request_id()))
    return payload


def list_api_keys(tenant_id: int | None = None) -> list[dict[str, Any]]:
    return api_key_service.list_api_keys(tenant_id=tenant_id)


def get_api_key(key_id: int) -> dict[str, Any] | None:
    return api_key_service.get_api_key(key_id)


def revoke_api_key(key_id: int) -> dict[str, Any]:
    return api_key_service.revoke_api_key(key_id)
