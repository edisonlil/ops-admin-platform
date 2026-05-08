from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from identity_access.infrastructure.persistence.common import (
    DisabledUserException,
    DEFAULT_TENANT_KEY,
    PLATFORM_TENANT_KEY,
    auth_database_target,
    connect,
    normalize_username,
    now_iso,
    require_auth_ready,
)
from identity_access.infrastructure.security import hash_password, verify_password


def platform_tenant_id(conn: Any) -> int:
    row = conn.execute("SELECT id FROM tenants WHERE tenant_key = ?", (PLATFORM_TENANT_KEY,)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="platform tenant missing")
    return int(row["id"])


def public_user(
    row: dict[str, Any],
    *,
    tenant_id: int | None = None,
    auth_scope: str | None = None,
    is_tenant_admin: bool = False,
) -> dict[str, Any]:
    effective_tenant_id = int(tenant_id or row.get("tenant_id", 1) or 1)
    user = {
        "id": int(row.get("id", 0) or 0),
        "tenant_id": effective_tenant_id,
        "username": str(row.get("username", "")),
        "is_active": bool(row.get("is_active", True)),
        "is_superuser": bool(row.get("is_superuser", False)),
    }
    from identity_access.infrastructure.persistence.rbac_repository import user_access_payload

    user.update(
        user_access_payload(
            int(row.get("id", 0) or 0),
            bool(row.get("is_superuser", False)),
            tenant_id=effective_tenant_id,
            auth_scope=auth_scope,
            is_tenant_admin=is_tenant_admin,
        )
    )
    return user


def user_by_username(username: str, tenant_id: int | None = None) -> dict[str, Any] | None:
    username = normalize_username(username)
    if not username:
        return None
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        if tenant_id:
            row = conn.execute(
                "SELECT * FROM users WHERE tenant_id = ? AND username = ?",
                (tenant_id, username),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT u.*
                FROM users u
                JOIN tenants t ON t.id = u.tenant_id
                WHERE u.username = ?
                ORDER BY CASE WHEN t.tenant_key = ? THEN 0 ELSE 1 END, u.tenant_id, u.id
                LIMIT 1
                """,
                (username, DEFAULT_TENANT_KEY),
            ).fetchone()
    return dict(row) if row else None


def platform_user_by_username(username: str) -> dict[str, Any] | None:
    username = normalize_username(username)
    if not username:
        return None
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute(
            """
            SELECT u.*
            FROM users u
            JOIN tenants t ON t.id = u.tenant_id
            WHERE t.tenant_key = ?
              AND u.username = ?
              AND u.is_superuser = ?
            LIMIT 1
            """,
            (PLATFORM_TENANT_KEY, username, True),
        ).fetchone()
    return dict(row) if row else None


def authenticate_user(username: str, password: str, tenant_id: int | None = None) -> dict[str, Any] | None:
    row = user_by_username(username, tenant_id=tenant_id)
    if not row:
        return None
    if not bool(row.get("is_active", True)):
        raise DisabledUserException()
    if not verify_password(password, str(row.get("hashed_password", ""))):
        return None
    return public_user(row, auth_scope="tenant")


def authenticate_platform_admin(username: str, password: str) -> dict[str, Any] | None:
    row = platform_user_by_username(username)
    if not row:
        return None
    if not bool(row.get("is_active", True)):
        raise DisabledUserException()
    if not verify_password(password, str(row.get("hashed_password", ""))):
        return None
    return public_user(row, auth_scope="platform")


def list_users() -> list[dict[str, Any]]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        rows = conn.execute(
            """
            SELECT id, tenant_id, username, is_active, is_superuser, created_at, updated_at
            FROM users
            ORDER BY tenant_id, username, id
            """
        ).fetchall()
        role_rows = conn.execute(
            """
            SELECT ur.user_id, r.role_key, r.name
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            ORDER BY r.role_key
            """
        ).fetchall()
    roles_by_user: dict[int, list[dict[str, str]]] = {}
    for row in role_rows:
        roles_by_user.setdefault(int(row["user_id"]), []).append(
            {"key": str(row["role_key"]), "name": str(row["name"])}
        )
    return [
        {
              "id": int(dict(row)["id"]),
              "tenant_id": int(dict(row).get("tenant_id", 1) or 1),
              "username": str(dict(row)["username"]),
            "is_active": bool(dict(row)["is_active"]),
            "is_superuser": bool(dict(row)["is_superuser"]),
            "roles": roles_by_user.get(int(dict(row)["id"]), []),
            "created_at": str(dict(row).get("created_at", "") or ""),
            "updated_at": str(dict(row).get("updated_at", "") or ""),
        }
        for row in rows
    ]


def resolve_role_ids(conn: Any, role_keys: list[str], *, role_scope: str | None = None) -> list[int]:
    normalized_keys = []
    seen: set[str] = set()
    for key in role_keys:
        item = str(key).strip()
        if item and item not in seen:
            normalized_keys.append(item)
            seen.add(item)
    if not normalized_keys:
        return []
    placeholders = ", ".join("?" for _ in normalized_keys)
    scope_clause = " AND role_scope = ?" if role_scope else ""
    params: list[Any] = [*normalized_keys]
    if role_scope:
        params.append(role_scope)
    rows = conn.execute(
        f"SELECT id, role_key FROM roles WHERE role_key IN ({placeholders}){scope_clause}",
        tuple(params),
    ).fetchall()
    ids_by_key = {str(row["role_key"]): int(row["id"]) for row in rows}
    missing = [key for key in normalized_keys if key not in ids_by_key]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown role keys: {', '.join(missing)}")
    return [ids_by_key[key] for key in normalized_keys]


def sync_user_roles(conn: Any, user_id: int, role_keys: list[str], *, role_scope: str | None = None) -> None:
    role_ids = resolve_role_ids(conn, role_keys, role_scope=role_scope)
    conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
    for role_id in role_ids:
        conn.execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES (?, ?)
            """,
            (user_id, role_id),
        )


def ensure_last_superuser_survives(conn: Any, user_id: int, *, is_active: bool, is_superuser: bool) -> None:
    current = conn.execute("SELECT is_active, is_superuser FROM users WHERE id = ?", (user_id,)).fetchone()
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if bool(current["is_active"]) and bool(current["is_superuser"]) and not (is_active and is_superuser):
        remaining = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM users
            WHERE id <> ? AND is_active = ? AND is_superuser = ?
            """,
            (user_id, True, True),
        ).fetchone()
        if int(remaining["count"]) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="at least one active superuser is required",
            )


def create_user(
    *,
    username: str,
    password: str,
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    normalized_username = normalize_username(username)
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        if tenant_id is None:
            tenant_id = platform_tenant_id(conn)
        tenant = conn.execute("SELECT tenant_key FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        tenant_key = str(tenant["tenant_key"])
        if bool(is_superuser) and tenant_key != PLATFORM_TENANT_KEY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="superuser must belong to platform tenant")
        role_scope = "platform" if tenant_key == PLATFORM_TENANT_KEY else "tenant"
        existing = conn.execute(
            "SELECT id FROM users WHERE tenant_id = ? AND username = ?",
            (tenant_id, normalized_username),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists in tenant")
        cursor = conn.execute(
            """
            INSERT INTO users (tenant_id, username, hashed_password, is_active, is_superuser, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, normalized_username, hash_password(password), bool(is_active), bool(is_superuser), now, now),
        )
        user_id = int(getattr(cursor, "lastrowid", 0) or 0)
        if not user_id:
            row = conn.execute(
                "SELECT id FROM users WHERE tenant_id = ? AND username = ?",
                (tenant_id, normalized_username),
            ).fetchone()
            user_id = int(row["id"])
        sync_user_roles(conn, user_id, list(role_keys or []), role_scope=role_scope)

    user = next((item for item in list_users() if int(item["id"]) == user_id), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


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
    normalized_username = normalize_username(username)
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute("SELECT id, tenant_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        effective_tenant_id = int(tenant_id or row["tenant_id"] or platform_tenant_id(conn))
        tenant = conn.execute("SELECT tenant_key FROM tenants WHERE id = ?", (effective_tenant_id,)).fetchone()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        tenant_key = str(tenant["tenant_key"])
        if bool(is_superuser) and tenant_key != PLATFORM_TENANT_KEY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="superuser must belong to platform tenant")
        role_scope = "platform" if tenant_key == PLATFORM_TENANT_KEY else "tenant"
        existing = conn.execute(
            "SELECT id FROM users WHERE tenant_id = ? AND username = ? AND id <> ?",
            (effective_tenant_id, normalized_username, user_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists in tenant")
        ensure_last_superuser_survives(conn, user_id, is_active=bool(is_active), is_superuser=bool(is_superuser))

        fields = ["tenant_id = ?", "username = ?", "is_active = ?", "is_superuser = ?", "updated_at = ?"]
        params: list[Any] = [effective_tenant_id, normalized_username, bool(is_active), bool(is_superuser), now]
        if password.strip():
            fields.insert(3, "hashed_password = ?")
            params.insert(3, hash_password(password))
        params.append(user_id)
        conn.execute(
            f"""
            UPDATE users
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            tuple(params),
        )
        sync_user_roles(conn, user_id, list(role_keys or []), role_scope=role_scope)

    user = next((item for item in list_users() if int(item["id"]) == user_id), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user
