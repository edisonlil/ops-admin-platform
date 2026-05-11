from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Response, status

from identity_access.application import auth_service, rbac_service
from identity_access.infrastructure.persistence import tenant_repository
from identity_access.infrastructure.persistence.common import auth_database_target, connect, require_auth_ready
from identity_access.infrastructure.persistence.tenant_repository import ensure_membership
from system.domain.tenancy import DEFAULT_TENANT_KEY


PLATFORM_TENANT_KEY = "platform"


def list_tenants(q: str | None = None) -> list[dict[str, Any]]:
    return tenant_repository.list_tenants(q=q)


def get_tenant_by_key(tenant_key: str) -> dict[str, Any] | None:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_tenant_by_key(conn, tenant_key or DEFAULT_TENANT_KEY)
    if tenant and str(tenant.get("tenant_key", "")) == PLATFORM_TENANT_KEY:
        return None
    return tenant


def membership_for_user_in_tenant(user_id: int, tenant_id: int | None) -> dict[str, Any] | None:
    if not user_id or not tenant_id:
        return None
    return next(
        (item for item in tenant_repository.memberships_for_user(user_id) if int(item["id"]) == int(tenant_id)),
        None,
    )


def load_user_for_tenant(username: str, tenant_id: int | None, *, auth_scope: str = "tenant") -> dict[str, Any] | None:
    if auth_scope == "platform":
        row = auth_service.platform_user_by_username(username)
        if not row:
            return None
    else:
        row = auth_service.user_by_username(username, tenant_id=tenant_id)
    if not row:
        return None
    effective_tenant_id = tenant_id or int(row.get("tenant_id", 1) or 1)
    membership = membership_for_user_in_tenant(int(row.get("id", 0) or 0), tenant_id)
    if auth_scope == "tenant" and membership is None:
        membership = membership_for_user_in_tenant(int(row.get("id", 0) or 0), effective_tenant_id)
    public = auth_service.public_user(
        row,
        tenant_id=effective_tenant_id,
        auth_scope=auth_scope,
        is_tenant_admin=bool((membership or {}).get("is_tenant_admin", False)),
    )
    public["id"] = int(row.get("id", 0) or 0)
    public["tenant_id"] = (
        effective_tenant_id
        if auth_scope == "tenant"
        else int(row.get("tenant_id", 1) or 1)
    )
    public["is_superuser"] = bool(row.get("is_superuser", False))
    public["auth_scope"] = auth_scope
    public["is_tenant_admin"] = bool((membership or {}).get("is_tenant_admin", False))
    return public


def create_tenant(payload: dict[str, Any]) -> dict[str, Any]:
    tenant = tenant_repository.create_tenant(
        tenant_key=str(payload.get("tenant_key") or payload.get("key") or ""),
        name=str(payload.get("name", "")),
        remark=str(payload.get("remark", "")),
        status_value=str(payload.get("status", "active")),
    )
    admin_username = str(payload.get("admin_username", "") or "").strip()
    admin_password = str(payload.get("admin_password", "") or "")
    if admin_username and admin_password:
        create_tenant_user(
            int(tenant["id"]),
            {
                "username": admin_username,
                "password": admin_password,
                "role_keys": ["tenant-admin"],
                "is_active": True,
                "is_superuser": False,
                "is_tenant_admin": True,
            },
        )
        tenant["user_count"] = 1
    return tenant


def update_tenant(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return tenant_repository.update_tenant(
        tenant_id,
        name=str(payload.get("name", "")),
        remark=str(payload.get("remark", "")),
        status_value=str(payload.get("status", "active")),
    )


def activate_tenant(tenant_id: int) -> dict[str, Any]:
    return tenant_repository.set_tenant_status(tenant_id, "active")


def suspend_tenant(tenant_id: int) -> dict[str, Any]:
    return tenant_repository.set_tenant_status(tenant_id, "suspended")


def current_tenant_for_user(user: dict[str, Any], tenant_id: int | None = None) -> dict[str, Any] | None:
    user_id = int(user.get("id", 0) or 0)
    memberships = tenant_repository.memberships_for_user(user_id)
    if bool(user.get("is_superuser", False)) and str(user.get("auth_scope", "tenant")) == "platform":
        tenants = tenant_repository.list_tenants()
        if tenant_id:
            tenant = next((item for item in tenants if int(item["id"]) == tenant_id), None)
            if not tenant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
            return tenant
        return None

    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user has no tenant membership")
    if tenant_id:
        tenant = next((item for item in memberships if int(item["id"]) == tenant_id), None)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant access denied")
        if tenant["status"] != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant is suspended")
        return tenant
    tenant = memberships[0]
    if tenant["status"] != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant is suspended")
    return tenant


def tenant_access_payload(user: dict[str, Any], current_tenant_id: int | None = None) -> dict[str, Any]:
    auth_scope = str(user.get("auth_scope", "tenant") or "tenant")
    current = current_tenant_for_user(user, current_tenant_id)
    memberships = tenant_repository.memberships_for_user(int(user.get("id", 0) or 0))
    if bool(user.get("is_superuser", False)) and auth_scope == "platform":
        memberships = tenant_repository.list_tenants()
    is_tenant_admin = False
    if current:
        membership = next((item for item in memberships if int(item["id"]) == int(current["id"])), None)
        is_tenant_admin = bool((membership or {}).get("is_tenant_admin", False))
    return {
        "current_tenant": current,
        "tenant_memberships": memberships,
        "auth_scope": auth_scope,
        "is_platform_admin": bool(user.get("is_superuser", False)) and auth_scope == "platform",
        "is_tenant_admin": is_tenant_admin,
    }


def switch_tenant(username: str, tenant_id: int, response: Response | None = None, *, auth_scope: str = "tenant") -> dict[str, Any]:
    if auth_scope == "platform":
        row = auth_service.platform_user_by_username(username)
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid user")
    else:
        row = auth_service.user_by_username(username, tenant_id=tenant_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid user")
    membership = membership_for_user_in_tenant(int(row.get("id", 0) or 0), tenant_id)
    public = auth_service.public_user(
        row,
        tenant_id=tenant_id,
        auth_scope=auth_scope,
        is_tenant_admin=bool((membership or {}).get("is_tenant_admin", False)),
    )
    public["auth_scope"] = auth_scope
    tenant = current_tenant_for_user({**row, **public}, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
    token = auth_service.create_access_token(
        str(row["username"]),
        tenant_id=int(tenant["id"]),
        auth_scope=auth_scope,
        user_id=int(row.get("id", 0) or 0),
    )
    if response is not None:
        auth_service.set_login_cookie(response, token)
    result = tenant_access_payload({**row, **public}, int(tenant["id"]))
    refreshed_public = auth_service.public_user(
        row,
        tenant_id=int(tenant["id"]),
        auth_scope=auth_scope,
        is_tenant_admin=bool(result.get("is_tenant_admin", False)),
    )
    result.update(
        {
            "token": token,
            "access_token": token,
            "token_type": "bearer",
            "username": str(row["username"]),
            "roles": refreshed_public.get("roles", []),
            "permissions": refreshed_public.get("permissions", []),
            "menus": refreshed_public.get("menus", []),
        }
    )
    return result


def ensure_tenant_access(current_user: dict[str, Any], tenant_id: int) -> None:
    if bool(current_user.get("is_platform_admin", False)):
        return
    current = current_user.get("current_tenant") or {}
    if int(current.get("id", 0) or 0) != int(tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant access denied")


def ensure_tenant_admin_access(current_user: dict[str, Any], tenant_id: int) -> None:
    if bool(current_user.get("is_platform_admin", False)):
        return
    ensure_tenant_access(current_user, tenant_id)
    if not bool(current_user.get("is_tenant_admin", False)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant admin required")


def list_tenant_users(tenant_id: int) -> list[dict[str, Any]]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_business_tenant_by_id(conn, tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.is_active, u.is_superuser, u.create_time, u.update_time, tm.is_tenant_admin
            FROM tenant_memberships tm
            JOIN users u ON u.id = tm.user_id
            WHERE tm.tenant_id = ?
            ORDER BY u.id
            """,
            (tenant_id,),
        ).fetchall()
    users = rbac_service.list_users()
    by_id = {int(item["id"]): item for item in users}
    result = []
    for row in rows:
        item = dict(by_id.get(int(row["id"]), {}))
        item["is_tenant_admin"] = bool(row["is_tenant_admin"])
        result.append(item)
    return result


def create_tenant_user(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    user = rbac_service.create_user(
        username=str(payload.get("username", "")),
        password=str(payload.get("password", "")),
        tenant_id=tenant_id,
        role_keys=list(payload.get("role_keys") or []),
        is_active=bool(payload.get("is_active", True)),
        is_superuser=False,
    )
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_business_tenant_by_id(conn, tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        ensure_membership(
            conn,
            tenant_id=tenant_id,
            user_id=int(user["id"]),
            is_tenant_admin=bool(payload.get("is_tenant_admin", False)),
        )
    return next((item for item in list_tenant_users(tenant_id) if int(item["id"]) == int(user["id"])), user)


def update_tenant_user(tenant_id: int, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_business_tenant_by_id(conn, tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        membership = conn.execute(
            "SELECT 1 FROM tenant_memberships WHERE tenant_id = ? AND user_id = ?",
            (tenant_id, user_id),
        ).fetchone()
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant user not found")

    user = rbac_service.update_user(
        user_id,
        username=str(payload.get("username", "")),
        password=str(payload.get("password", "")),
        tenant_id=tenant_id,
        role_keys=list(payload.get("role_keys") or []),
        is_active=bool(payload.get("is_active", True)),
        is_superuser=False,
    )
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        ensure_membership(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            is_tenant_admin=bool(payload.get("is_tenant_admin", False)),
        )
    return next((item for item in list_tenant_users(tenant_id) if int(item["id"]) == user_id), user)


def set_tenant_user_active(tenant_id: int, user_id: int, is_active: bool) -> dict[str, Any]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_business_tenant_by_id(conn, tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        membership = conn.execute(
            "SELECT 1 FROM tenant_memberships WHERE tenant_id = ? AND user_id = ?",
            (tenant_id, user_id),
        ).fetchone()
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant user not found")

    user = rbac_service.set_user_active(user_id, is_active)
    return next((item for item in list_tenant_users(tenant_id) if int(item["id"]) == user_id), user)
