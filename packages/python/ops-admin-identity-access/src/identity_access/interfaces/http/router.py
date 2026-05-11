from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login.exceptions import InvalidCredentialsException

from identity_access.interfaces.http.dtos import (
    ApiKeyCreateRequest,
    RbacMenuCreateRequest,
    RbacMenuUpdateRequest,
    RbacRoleCreateRequest,
    RbacRoleMenusUpdateRequest,
    RbacRoleUpdateRequest,
    RbacUserCreateRequest,
    RbacUserUpdateRequest,
    TenantCreateRequest,
    TenantSwitchRequest,
    TenantUpdateRequest,
    TenantUserCreateRequest,
    TenantUserUpdateRequest,
)
from identity_access.application import services, tenant_service
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import error_response, ok


router = APIRouter()


@router.post("/auth/token")
def login(response: Response, form: OAuth2PasswordRequestForm = Depends()) -> dict[str, Any]:
    payload = services.authenticate(form.username, form.password, response, tenant_key="default")
    if not payload:
        raise InvalidCredentialsException
    return ok(payload)


@router.get("/auth/me")
def me(current_user: dict[str, Any] = Depends(auth.require_user)) -> dict[str, Any]:
    return ok(current_user)


@router.post("/auth/tenant/switch")
def switch_tenant(
    payload: TenantSwitchRequest,
    response: Response,
    current_user: dict[str, Any] = Depends(auth.require_user),
) -> dict[str, Any]:
    return ok(
        services.switch_tenant(
            str(current_user["username"]),
            payload.tenant_id,
            response=response,
            auth_scope=str(current_user.get("auth_scope") or "tenant"),
        )
    )


@router.post("/auth/logout")
def logout(response: Response) -> dict[str, Any]:
    return ok({"ok": services.logout(response)})


@router.post("/login")
def naive_admin_login(response: Response, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    params = payload.get("params", payload) if isinstance(payload, dict) else {}
    username = str(params.get("username", "")).strip()
    password = str(params.get("password", ""))
    tenant_key = str(params.get("tenant_key") or params.get("tenant") or "default").strip() or "default"
    result = services.login_for_admin(username, password, response, tenant_key=tenant_key)
    if not result:
        return error_response(status_code=401, code="INVALID_CREDENTIALS", message="用户名或密码错误")
    return ok(result)


@router.post("/login/logout")
def naive_admin_logout(response: Response) -> dict[str, Any]:
    return ok(services.logout(response))


@router.get("/admin_info")
def naive_admin_info(current_user: dict[str, Any] = Depends(auth.require_user)) -> dict[str, Any]:
    return ok(services.scaffold_user(current_user))


@router.get("/api-keys")
def api_keys(_: dict[str, Any] = Depends(auth.require_permission("api_keys:access"))) -> dict[str, Any]:
    return ok({"items": services.list_api_keys()})


@router.post("/api-keys")
def create_api_key(
    payload: ApiKeyCreateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("api_keys:create")),
) -> dict[str, Any]:
    return ok(services.create_api_key(name=payload.name, creator=str(current_user["username"])))


@router.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: int, _: dict[str, Any] = Depends(auth.require_permission("api_keys:revoke"))) -> dict[str, Any]:
    return ok(services.revoke_api_key(key_id))


@router.get("/tenants")
def tenants(
    q: str | None = None,
    _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:access")),
) -> dict[str, Any]:
    return ok({"items": services.list_tenants(q=q)})


@router.post("/tenants")
def create_tenant(
    payload: TenantCreateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:create")),
) -> dict[str, Any]:
    return ok({"item": services.create_tenant(payload.model_dump())})


@router.put("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: int,
    payload: TenantUpdateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:update")),
) -> dict[str, Any]:
    return ok({"item": services.update_tenant(tenant_id, payload.model_dump())})


@router.post("/tenants/{tenant_id}/activate")
def activate_tenant(tenant_id: int, _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:activate"))) -> dict[str, Any]:
    return ok({"item": services.activate_tenant(tenant_id)})


@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(tenant_id: int, _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:suspend"))) -> dict[str, Any]:
    return ok({"item": services.suspend_tenant(tenant_id)})


@router.get("/tenants/{tenant_id}/users")
def tenant_users(tenant_id: int, _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:access"))) -> dict[str, Any]:
    return ok({"items": services.list_tenant_users(tenant_id)})


@router.post("/tenants/{tenant_id}/users")
def create_tenant_user(
    tenant_id: int,
    payload: TenantUserCreateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:users:create")),
) -> dict[str, Any]:
    return ok({"item": services.create_tenant_user(tenant_id, payload.model_dump())})


@router.put("/tenants/{tenant_id}/users/{user_id}")
def update_tenant_user(
    tenant_id: int,
    user_id: int,
    payload: TenantUserUpdateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:users:update")),
) -> dict[str, Any]:
    return ok({"item": services.update_tenant_user(tenant_id, user_id, payload.model_dump())})


@router.post("/tenants/{tenant_id}/users/{user_id}/enable")
def enable_tenant_user(
    tenant_id: int,
    user_id: int,
    _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:users:enable")),
) -> dict[str, Any]:
    return ok({"item": services.set_tenant_user_active(tenant_id, user_id, True)})


@router.post("/tenants/{tenant_id}/users/{user_id}/disable")
def disable_tenant_user(
    tenant_id: int,
    user_id: int,
    _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:users:disable")),
) -> dict[str, Any]:
    return ok({"item": services.set_tenant_user_active(tenant_id, user_id, False)})


@router.get("/tenants/{tenant_id}/api-keys")
def tenant_api_keys(tenant_id: int, _: dict[str, Any] = Depends(auth.require_platform_permission("tenant:access"))) -> dict[str, Any]:
    return ok({"items": services.list_api_keys(tenant_id=tenant_id)})


@router.post("/tenants/{tenant_id}/api-keys")
def create_tenant_api_key(
    tenant_id: int,
    payload: ApiKeyCreateRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("tenant:api_keys:create")),
) -> dict[str, Any]:
    return ok(services.create_api_key(name=payload.name, creator=str(current_user["username"]), tenant_id=tenant_id))


@router.delete("/tenants/{tenant_id}/api-keys/{key_id}")
def revoke_tenant_api_key(
    tenant_id: int,
    key_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("tenant:api_keys:revoke")),
) -> dict[str, Any]:
    existing = services.get_api_key(key_id)
    if existing:
        tenant_service.ensure_tenant_access(current_user, int(existing.get("tenant_id", 0) or 0))
    item = services.revoke_api_key(key_id)
    return ok(item)


@router.get("/tenant/users")
def current_tenant_users(current_user: dict[str, Any] = Depends(auth.require_permission("tenant:user:manage"))) -> dict[str, Any]:
    tenant_id = int((current_user.get("current_tenant") or {}).get("id", 0) or 0)
    return ok({"items": services.list_tenant_users(tenant_id)})


@router.post("/tenant/users")
def create_current_tenant_user(
    payload: TenantUserCreateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("tenant:users:create")),
) -> dict[str, Any]:
    tenant_id = int((current_user.get("current_tenant") or {}).get("id", 0) or 0)
    return ok({"item": services.create_tenant_user(tenant_id, payload.model_dump())})


@router.put("/tenant/users/{user_id}")
def update_current_tenant_user(
    user_id: int,
    payload: TenantUserUpdateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("tenant:users:update")),
) -> dict[str, Any]:
    tenant_id = int((current_user.get("current_tenant") or {}).get("id", 0) or 0)
    return ok({"item": services.update_tenant_user(tenant_id, user_id, payload.model_dump())})


@router.post("/tenant/users/{user_id}/enable")
def enable_current_tenant_user(
    user_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("tenant:users:enable")),
) -> dict[str, Any]:
    tenant_id = int((current_user.get("current_tenant") or {}).get("id", 0) or 0)
    return ok({"item": services.set_tenant_user_active(tenant_id, user_id, True)})


@router.post("/tenant/users/{user_id}/disable")
def disable_current_tenant_user(
    user_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("tenant:users:disable")),
) -> dict[str, Any]:
    tenant_id = int((current_user.get("current_tenant") or {}).get("id", 0) or 0)
    return ok({"item": services.set_tenant_user_active(tenant_id, user_id, False)})


@router.get("/tenant/roles")
def current_tenant_roles(_: dict[str, Any] = Depends(auth.require_permission("tenant:user:manage"))) -> dict[str, Any]:
    return ok({"items": [role for role in services.list_roles() if role.get("role_scope") == "tenant"]})


@router.get("/tenant/api-keys")
def current_tenant_api_keys(current_user: dict[str, Any] = Depends(auth.require_permission("tenant:api_key:manage"))) -> dict[str, Any]:
    tenant_id = int((current_user.get("current_tenant") or {}).get("id", 0) or 0)
    return ok({"items": services.list_api_keys(tenant_id=tenant_id)})


@router.post("/tenant/api-keys")
def create_current_tenant_api_key(
    payload: ApiKeyCreateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("tenant:api_keys:create")),
) -> dict[str, Any]:
    tenant_id = int((current_user.get("current_tenant") or {}).get("id", 0) or 0)
    return ok(services.create_api_key(name=payload.name, creator=str(current_user["username"]), tenant_id=tenant_id))


@router.delete("/tenant/api-keys/{key_id}")
def revoke_current_tenant_api_key(
    key_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("tenant:api_keys:revoke")),
) -> dict[str, Any]:
    existing = services.get_api_key(key_id)
    if existing:
        tenant_service.ensure_tenant_access(current_user, int(existing.get("tenant_id", 0) or 0))
    item = services.revoke_api_key(key_id)
    return ok(item)


@router.get("/rbac/users")
def rbac_users(_: dict[str, Any] = Depends(auth.require_platform_permission("system:user:access"))) -> dict[str, Any]:
    return ok({"items": services.list_users()})


@router.post("/rbac/users")
def create_rbac_user(
    payload: RbacUserCreateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:users:create")),
) -> dict[str, Any]:
    return ok({"item": services.create_user(
        tenant_id=payload.tenant_id,
        username=payload.username,
        password=payload.password,
        role_keys=payload.role_keys,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )})


@router.put("/rbac/users/{user_id}")
def update_rbac_user(
    user_id: int,
    payload: RbacUserUpdateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:users:update")),
) -> dict[str, Any]:
    return ok({"item": services.update_user(
        user_id,
        tenant_id=payload.tenant_id,
        username=payload.username,
        password=payload.password,
        role_keys=payload.role_keys,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )})


@router.post("/rbac/users/{user_id}/enable")
def enable_rbac_user(
    user_id: int,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:users:enable")),
) -> dict[str, Any]:
    return ok({"item": services.set_user_active(user_id, True)})


@router.post("/rbac/users/{user_id}/disable")
def disable_rbac_user(
    user_id: int,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:users:disable")),
) -> dict[str, Any]:
    return ok({"item": services.set_user_active(user_id, False)})


@router.get("/rbac/roles")
def rbac_roles(_: dict[str, Any] = Depends(auth.require_platform_permission("system:role:access"))) -> dict[str, Any]:
    return ok({"items": services.list_roles()})


@router.post("/rbac/roles")
def create_rbac_role(
    payload: RbacRoleCreateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:roles:create")),
) -> dict[str, Any]:
    return ok({"item": services.create_role(
        role_key=payload.key,
        name=payload.name,
        description=payload.description,
        menu_keys=payload.menu_keys,
    )})


@router.put("/rbac/roles/{role_id}/menus")
def update_rbac_role_menus(
    role_id: int,
    payload: RbacRoleMenusUpdateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:roles:assign_menus")),
) -> dict[str, Any]:
    return ok({"item": services.update_role_menus(role_id, payload.menu_keys)})


@router.put("/rbac/roles/{role_id}")
def update_rbac_role(
    role_id: int,
    payload: RbacRoleUpdateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:roles:update")),
) -> dict[str, Any]:
    return ok({"item": services.update_role(
        role_id,
        role_key=payload.key,
        name=payload.name,
        description=payload.description,
        menu_keys=payload.menu_keys,
    )})


@router.delete("/rbac/roles/{role_id}")
def delete_rbac_role(
    role_id: int,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:roles:delete")),
) -> dict[str, Any]:
    return ok({"item": services.delete_role(role_id)})


@router.get("/rbac/permissions")
def rbac_permissions(_: dict[str, Any] = Depends(auth.require_platform_permission("system:role:access"))) -> dict[str, Any]:
    return ok({"items": services.list_permissions()})


@router.get("/rbac/menus")
def rbac_menus(_: dict[str, Any] = Depends(auth.require_platform_permission("system:menu:access"))) -> dict[str, Any]:
    return ok({"items": services.list_menus()})


@router.post("/rbac/menus")
def create_rbac_menu(
    payload: RbacMenuCreateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:menus:create")),
) -> dict[str, Any]:
    return ok({"item": services.create_menu(
        menu_key=payload.key,
        label=payload.label,
        menu_type=payload.menu_type,
        path=payload.path,
        route_name=payload.route_name,
        component=payload.component,
        icon=payload.icon,
        parent_key=payload.parent_key,
        permission_code=payload.permission_code,
        sort_order=payload.sort_order,
        is_visible=payload.is_visible,
    )})


@router.put("/rbac/menus/{menu_id}")
def update_rbac_menu(
    menu_id: int,
    payload: RbacMenuUpdateRequest,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:menus:update")),
) -> dict[str, Any]:
    return ok({"item": services.update_menu(
        menu_id,
        menu_key=payload.key,
        label=payload.label,
        menu_type=payload.menu_type,
        path=payload.path,
        route_name=payload.route_name,
        component=payload.component,
        icon=payload.icon,
        parent_key=payload.parent_key,
        permission_code=payload.permission_code,
        sort_order=payload.sort_order,
        is_visible=payload.is_visible,
    )})


@router.delete("/rbac/menus/{menu_id}")
def delete_rbac_menu(
    menu_id: int,
    _: dict[str, Any] = Depends(auth.require_platform_permission("system:menus:delete")),
) -> dict[str, Any]:
    return ok({"item": services.delete_menu(menu_id)})
