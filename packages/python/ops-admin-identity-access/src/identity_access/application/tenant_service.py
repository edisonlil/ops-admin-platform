from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Response, status

from identity_access.application.access_context_cache import clear_access_context_cache
from identity_access.application import auth_service, rbac_service
from identity_access.infrastructure.persistence import tenant_repository
from identity_access.infrastructure.persistence.common import _executemany, auth_database_target, connect, now_iso, require_auth_ready
from identity_access.infrastructure.persistence.tenant_repository import ensure_membership
from system.domain.tenancy import DEFAULT_TENANT_KEY


PLATFORM_TENANT_KEY = "platform"
TENANT_ADMIN_ROLE_KEY = "tenant-admin"


def _after_access_context_change(payload: dict[str, Any]) -> dict[str, Any]:
    clear_access_context_cache()
    return payload


def list_tenants(q: str | None = None, *, sort_by: str | None = None, sort_dir: str | None = None) -> list[dict[str, Any]]:
    return tenant_repository.list_tenants(q=q, sort_by=sort_by, sort_dir=sort_dir)


def get_tenant_by_key(tenant_key: str) -> dict[str, Any] | None:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_tenant_by_key(conn, tenant_key or DEFAULT_TENANT_KEY)
    if tenant and str(tenant.get("tenant_key", "")) == PLATFORM_TENANT_KEY:
        return None
    return tenant


def get_business_tenant_by_id(tenant_id: int) -> dict[str, Any] | None:
    with connect(auth_database_target(), readonly=True) as conn:
        require_auth_ready(conn)
        return tenant_repository.get_business_tenant_by_id(conn, tenant_id)


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


def user_departments_for_current_tenant(current_user: dict[str, Any]) -> list[dict[str, Any]]:
    tenant_id = int((current_user.get("current_tenant") or {}).get("id") or current_user.get("tenant_id") or 0)
    user_id = int(current_user.get("id", 0) or 0)
    if not tenant_id or not user_id:
        return []
    try:
        from organization.application import services as organization_services
    except Exception:
        return []
    try:
        return organization_services.user_departments(tenant_id=tenant_id, user_id=user_id)
    except Exception:
        return []


def tenant_users_departments_if_available(tenant_id: int, user_ids: list[int]) -> dict[int, list[dict[str, Any]]] | None:
    if not user_ids:
        return {}
    try:
        from organization.application import services as organization_services
    except Exception:
        return None
    try:
        return organization_services.users_departments(tenant_id=tenant_id, user_ids=user_ids)
    except Exception:
        return None


def tenant_users_reporting_managers_if_available(tenant_id: int, user_ids: list[int]) -> dict[int, dict[str, Any] | None] | None:
    if not user_ids:
        return {}
    try:
        from organization.application import services as organization_services
    except Exception:
        return None
    try:
        return organization_services.users_reporting_managers(tenant_id=tenant_id, user_ids=user_ids)
    except Exception:
        return None


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
                "full_name": str(payload.get("admin_full_name") or ""),
                "password": admin_password,
                "role_keys": [TENANT_ADMIN_ROLE_KEY],
                "is_active": True,
                "is_superuser": False,
            },
        )
        tenant["user_count"] = 1
    return _after_access_context_change(tenant)


def update_tenant(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return _after_access_context_change(tenant_repository.update_tenant(
        tenant_id,
        name=str(payload.get("name", "")),
        remark=str(payload.get("remark", "")),
        status_value=str(payload.get("status", "active")),
    ))


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
            "full_name": str(row.get("full_name", "") or ""),
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
    with connect(auth_database_target(), readonly=True) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_business_tenant_by_id(conn, tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.is_active, u.is_superuser, u.create_time, u.update_time, tm.is_tenant_admin
            FROM tenant_memberships tm
            JOIN users u ON u.id = tm.user_id
            WHERE tm.tenant_id = ? AND tm.deleted = 0 AND u.deleted = 0
            ORDER BY u.id
            """,
            (tenant_id,),
        ).fetchall()
        user_ids = [int(row["id"]) for row in rows]
        roles_by_user = tenant_user_roles(conn, user_ids)
    departments_by_user = tenant_users_departments_if_available(tenant_id, user_ids)
    managers_by_user = tenant_users_reporting_managers_if_available(tenant_id, user_ids)
    result = []
    for row in rows:
        user_id = int(row["id"])
        item = {
            "id": user_id,
            "tenant_id": int(tenant_id),
            "username": str(row["username"]),
            "full_name": str(row["full_name"] or ""),
            "email": str(row["email"] or ""),
            "is_active": bool(row["is_active"]),
            "is_superuser": bool(row["is_superuser"]),
            "roles": roles_by_user.get(user_id, []),
            "create_time": str(row["create_time"] or ""),
            "update_time": str(row["update_time"] or ""),
        }
        item["is_tenant_admin"] = bool(row["is_tenant_admin"])
        if departments_by_user is not None:
            apply_tenant_user_departments(item, departments_by_user.get(user_id, []))
        if managers_by_user is not None:
            apply_tenant_user_reporting_manager(item, managers_by_user.get(user_id))
        result.append(item)
    return result


def get_tenant_user(tenant_id: int, user_id: int) -> dict[str, Any] | None:
    with connect(auth_database_target(), readonly=True) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_business_tenant_by_id(conn, tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        row = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.is_active, u.is_superuser, u.create_time, u.update_time, tm.is_tenant_admin
            FROM tenant_memberships tm
            JOIN users u ON u.id = tm.user_id
            WHERE tm.tenant_id = ? AND tm.user_id = ? AND tm.deleted = 0 AND u.deleted = 0
            LIMIT 1
            """,
            (tenant_id, user_id),
        ).fetchone()
        if not row:
            return None
        roles_by_user = tenant_user_roles(conn, [user_id])
    item = {
        "id": int(row["id"]),
        "tenant_id": int(tenant_id),
        "username": str(row["username"]),
        "full_name": str(row["full_name"] or ""),
        "email": str(row["email"] or ""),
        "is_active": bool(row["is_active"]),
        "is_superuser": bool(row["is_superuser"]),
        "roles": roles_by_user.get(user_id, []),
        "create_time": str(row["create_time"] or ""),
        "update_time": str(row["update_time"] or ""),
        "is_tenant_admin": bool(row["is_tenant_admin"]),
    }
    return enrich_tenant_user_with_departments(item, tenant_id)


def tenant_user_roles(conn: Any, user_ids: list[int]) -> dict[int, list[dict[str, str]]]:
    if not user_ids:
        return {}
    placeholders = ", ".join("?" for _ in user_ids)
    rows = conn.execute(
        f"""
        SELECT ur.user_id, r.role_key, r.name, r.role_scope
        FROM user_roles ur
        JOIN roles r ON r.id = ur.role_id
        WHERE ur.user_id IN ({placeholders})
          AND r.role_scope = ?
          AND ur.deleted = 0
          AND r.deleted = 0
        ORDER BY ur.user_id ASC, r.role_key ASC
        """,
        (*user_ids, "tenant"),
    ).fetchall()
    roles_by_user: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        roles_by_user.setdefault(int(row["user_id"]), []).append(
            {"key": str(row["role_key"]), "name": str(row["name"]), "role_scope": str(row["role_scope"] or "tenant")}
        )
    return roles_by_user


def apply_tenant_user_departments(item: dict[str, Any], departments: list[dict[str, Any]]) -> dict[str, Any]:
    item["departments"] = departments
    item["department_ids"] = [int(department["department_id"]) for department in departments]
    primary = next((department for department in departments if bool(department.get("is_primary"))), departments[0] if departments else None)
    item["primary_department_id"] = int(primary["department_id"]) if primary else None
    return item


def apply_tenant_user_reporting_manager(item: dict[str, Any], relationship: dict[str, Any] | None) -> dict[str, Any]:
    item["manager_user_id"] = int((relationship or {}).get("manager_user_id") or 0) or None
    return item


def create_tenant_user(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    role_keys = list(payload.get("role_keys") or [])
    user = rbac_service.create_user(
        username=str(payload.get("username", "")),
        full_name=str(payload.get("full_name", "") or ""),
        email=str(payload.get("email", "") or ""),
        password=str(payload.get("password", "")),
        tenant_id=tenant_id,
        role_keys=role_keys,
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
            is_tenant_admin=TENANT_ADMIN_ROLE_KEY in role_keys,
        )
    if payload.get("department_ids") is not None or payload.get("primary_department_id") is not None:
        sync_tenant_user_departments_if_available(
            tenant_id=tenant_id,
            user_id=int(user["id"]),
            department_ids=[int(value) for value in payload.get("department_ids") or []],
            primary_department_id=payload.get("primary_department_id"),
        )
    if "manager_user_id" in payload:
        sync_tenant_user_reporting_manager_if_available(
            tenant_id=tenant_id,
            user_id=int(user["id"]),
            manager_user_id=payload.get("manager_user_id"),
        )
    return _after_access_context_change(get_tenant_user(tenant_id, int(user["id"])) or user)


def ensure_memberships_batch(tenant_id: int, rows: list[dict[str, Any]]) -> None:
    normalized_rows = [
        (tenant_id, int(row.get("user_id") or 0), bool(row.get("is_tenant_admin", False)), now_iso())
        for row in rows
        if int(row.get("user_id") or 0)
    ]
    if not normalized_rows:
        return
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        tenant = tenant_repository.get_business_tenant_by_id(conn, tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        _executemany(
            conn,
            """
            UPDATE tenant_memberships
            SET is_tenant_admin = ?
            WHERE tenant_id = ? AND user_id = ?
            """,
            [(is_tenant_admin, row_tenant_id, user_id) for row_tenant_id, user_id, is_tenant_admin, _timestamp in normalized_rows],
        )
        _executemany(
            conn,
            """
            INSERT INTO tenant_memberships (tenant_id, user_id, is_tenant_admin, create_time)
            SELECT ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM tenant_memberships WHERE tenant_id = ? AND user_id = ?
            )
            """,
            [
                (row_tenant_id, user_id, is_tenant_admin, timestamp, row_tenant_id, user_id)
                for row_tenant_id, user_id, is_tenant_admin, timestamp in normalized_rows
            ],
        )


def update_tenant_user(tenant_id: int, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    role_keys = list(payload.get("role_keys") or [])
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
        full_name=str(payload.get("full_name", "") or ""),
        email=str(payload.get("email", "") or ""),
        password=str(payload.get("password", "")),
        tenant_id=tenant_id,
        role_keys=role_keys,
        is_active=bool(payload.get("is_active", True)),
        is_superuser=False,
    )
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        ensure_membership(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            is_tenant_admin=TENANT_ADMIN_ROLE_KEY in role_keys,
        )
    if payload.get("department_ids") is not None or payload.get("primary_department_id") is not None:
        sync_tenant_user_departments_if_available(
            tenant_id=tenant_id,
            user_id=user_id,
            department_ids=[int(value) for value in payload.get("department_ids") or []],
            primary_department_id=payload.get("primary_department_id"),
        )
    if "manager_user_id" in payload:
        sync_tenant_user_reporting_manager_if_available(
            tenant_id=tenant_id,
            user_id=user_id,
            manager_user_id=payload.get("manager_user_id"),
        )
    return _after_access_context_change(get_tenant_user(tenant_id, user_id) or user)


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
    return _after_access_context_change(get_tenant_user(tenant_id, user_id) or user)


def sync_tenant_user_departments_if_available(
    *,
    tenant_id: int,
    user_id: int,
    department_ids: list[int],
    primary_department_id: Any,
) -> None:
    try:
        from organization.application import services as organization_services
    except Exception:
        return
    organization_services.set_user_departments(
        tenant_id=tenant_id,
        user_id=user_id,
        department_ids=department_ids,
        primary_department_id=int(primary_department_id or 0) or None,
        current_user={"username": "system", "id": None},
    )


def sync_tenant_user_reporting_manager_if_available(
    *,
    tenant_id: int,
    user_id: int,
    manager_user_id: Any,
) -> None:
    try:
        from organization.application import services as organization_services
    except Exception:
        return
    organization_services.set_user_reporting_manager(
        tenant_id=tenant_id,
        user_id=user_id,
        manager_user_id=int(manager_user_id or 0) or None,
        current_user={"username": "system", "id": None},
    )


def enrich_tenant_user_with_departments(item: dict[str, Any], tenant_id: int) -> dict[str, Any]:
    try:
        from organization.application import services as organization_services
    except Exception:
        return item
    user_id = int(item.get("id", 0) or 0)
    if not user_id:
        return item
    try:
        departments = organization_services.user_departments(tenant_id=tenant_id, user_id=user_id)
    except Exception:
        return item
    apply_tenant_user_departments(item, departments)
    try:
        relationship = organization_services.user_reporting_manager(tenant_id=tenant_id, user_id=user_id)
    except Exception:
        relationship = None
    return apply_tenant_user_reporting_manager(item, relationship)
