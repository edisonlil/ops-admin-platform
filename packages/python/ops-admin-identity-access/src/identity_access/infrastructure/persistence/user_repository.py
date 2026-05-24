from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from identity_access.infrastructure.persistence.common import (
    DisabledUserException,
    DEFAULT_TENANT_KEY,
    PLATFORM_TENANT_KEY,
    _executemany,
    auth_database_target,
    connect,
    normalize_username,
    now_iso,
    require_auth_ready,
)
from identity_access.infrastructure.security import hash_password, verify_password


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def looks_like_email(value: str) -> bool:
    normalized = normalize_email(value)
    return bool(normalized and "@" in normalized)


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
        "full_name": str(row.get("full_name", "") or ""),
        "email": normalize_email(str(row.get("email", "") or "")),
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


def user_by_login_identifier(identifier: str, tenant_id: int | None = None) -> dict[str, Any] | None:
    if looks_like_email(identifier):
        email = normalize_email(identifier)
        if not email or tenant_id is None:
            return None
        with connect(auth_database_target(), readonly=False) as conn:
            require_auth_ready(conn)
            row = conn.execute(
                """
                SELECT *
                FROM users
                WHERE tenant_id = ? AND lower(email) = ? AND email <> ''
                LIMIT 1
                """,
                (tenant_id, email),
            ).fetchone()
        return dict(row) if row else None
    return user_by_username(identifier, tenant_id=tenant_id)


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


def platform_user_by_login_identifier(identifier: str) -> dict[str, Any] | None:
    if looks_like_email(identifier):
        email = normalize_email(identifier)
        with connect(auth_database_target(), readonly=False) as conn:
            require_auth_ready(conn)
            row = conn.execute(
                """
                SELECT u.*
                FROM users u
                JOIN tenants t ON t.id = u.tenant_id
                WHERE t.tenant_key = ?
                  AND lower(u.email) = ?
                  AND u.email <> ''
                  AND u.is_superuser = ?
                LIMIT 1
                """,
                (PLATFORM_TENANT_KEY, email, True),
            ).fetchone()
        return dict(row) if row else None
    return platform_user_by_username(identifier)


def authenticate_user(username: str, password: str, tenant_id: int | None = None) -> dict[str, Any] | None:
    row = user_by_login_identifier(username, tenant_id=tenant_id)
    if not row:
        return None
    if not bool(row.get("is_active", True)):
        raise DisabledUserException()
    if not verify_password(password, str(row.get("hashed_password", ""))):
        return None
    return public_user(row, auth_scope="tenant")


def authenticate_platform_admin(username: str, password: str) -> dict[str, Any] | None:
    row = platform_user_by_login_identifier(username)
    if not row:
        return None
    if not bool(row.get("is_active", True)):
        raise DisabledUserException()
    if not verify_password(password, str(row.get("hashed_password", ""))):
        return None
    return public_user(row, auth_scope="platform")


def list_users() -> list[dict[str, Any]]:
    return list_users_by_tenant_key()


def list_platform_users() -> list[dict[str, Any]]:
    return list_users_by_tenant_key(PLATFORM_TENANT_KEY)


def get_user(user_id: int) -> dict[str, Any] | None:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute(
            """
            SELECT id, tenant_id, username, full_name, email, is_active, is_superuser, create_time, update_time
            FROM users
            WHERE id = ? AND deleted = 0
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if not row:
            return None
        roles_by_user = roles_by_user_ids(conn, [user_id])
    return user_payload(dict(row), roles_by_user)


def list_users_by_tenant_key(tenant_key: str | None = None) -> list[dict[str, Any]]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        params: list[Any] = []
        tenant_filter = ""
        if tenant_key:
            tenant_filter = "JOIN tenants t ON t.id = u.tenant_id WHERE t.tenant_key = ?"
            params.append(tenant_key)
        rows = conn.execute(
            f"""
            SELECT u.id, u.tenant_id, u.username, u.full_name, u.email, u.is_active, u.is_superuser, u.create_time, u.update_time
            FROM users u
            {tenant_filter}
            ORDER BY u.tenant_id, u.username, u.id
            """,
            tuple(params),
        ).fetchall()
        role_params: list[Any] = []
        role_filter = ""
        if tenant_key:
            role_filter = "WHERE r.role_scope = ?"
            role_params.append("platform" if tenant_key == PLATFORM_TENANT_KEY else "tenant")
        role_rows = conn.execute(
            """
            SELECT ur.user_id, r.role_key, r.name, r.role_scope
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            {role_filter}
            ORDER BY r.role_key
            """.format(role_filter=role_filter),
            tuple(role_params),
        ).fetchall()
    roles_by_user = roles_by_role_rows(role_rows)
    return [user_payload(dict(row), roles_by_user) for row in rows]


def roles_by_user_ids(conn: Any, user_ids: list[int]) -> dict[int, list[dict[str, str]]]:
    normalized = [int(value) for value in sorted(set(user_ids)) if int(value)]
    if not normalized:
        return {}
    placeholders = ", ".join("?" for _ in normalized)
    role_rows = conn.execute(
        f"""
        SELECT ur.user_id, r.role_key, r.name, r.role_scope
        FROM user_roles ur
        JOIN roles r ON r.id = ur.role_id
        WHERE ur.user_id IN ({placeholders})
          AND ur.deleted = 0
          AND r.deleted = 0
        ORDER BY r.role_key
        """,
        tuple(normalized),
    ).fetchall()
    return roles_by_role_rows(role_rows)


def roles_by_role_rows(role_rows: list[Any]) -> dict[int, list[dict[str, str]]]:
    roles_by_user: dict[int, list[dict[str, str]]] = {}
    for row in role_rows:
        roles_by_user.setdefault(int(row["user_id"]), []).append(
            {"key": str(row["role_key"]), "name": str(row["name"]), "role_scope": str(row["role_scope"] or "platform")}
        )
    return roles_by_user


def user_payload(row: dict[str, Any], roles_by_user: dict[int, list[dict[str, str]]]) -> dict[str, Any]:
    user_id = int(row["id"])
    return {
        "id": user_id,
        "tenant_id": int(row.get("tenant_id", 1) or 1),
        "username": str(row["username"]),
        "full_name": str(row.get("full_name", "") or ""),
        "email": normalize_email(str(row.get("email", "") or "")),
        "is_active": bool(row["is_active"]),
        "is_superuser": bool(row["is_superuser"]),
        "roles": roles_by_user.get(user_id, []),
        "create_time": str(row.get("create_time", "") or ""),
        "update_time": str(row.get("update_time", "") or ""),
    }


def users_by_ids(user_ids: list[int]) -> list[dict[str, Any]]:
    normalized = [int(value) for value in sorted(set(user_ids)) if int(value)]
    if not normalized:
        return []
    placeholders = ", ".join("?" for _ in normalized)
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        rows = conn.execute(
            f"""
            SELECT id, tenant_id, username, full_name, email, is_active, is_superuser, create_time, update_time
            FROM users
            WHERE id IN ({placeholders}) AND deleted = 0
            ORDER BY id
            """,
            tuple(normalized),
        ).fetchall()
        roles_by_user = roles_by_user_ids(conn, normalized)
    order = {user_id: index for index, user_id in enumerate(normalized)}
    items = [user_payload(dict(row), roles_by_user) for row in rows]
    return sorted(items, key=lambda item: order.get(int(item["id"]), len(order)))


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


def ensure_email_available(conn: Any, *, tenant_id: int, email: str, exclude_user_id: int | None = None) -> None:
    normalized_email = normalize_email(email)
    if not normalized_email:
        return
    params: list[Any] = [tenant_id, normalized_email]
    exclude_clause = ""
    if exclude_user_id is not None:
        exclude_clause = " AND id <> ?"
        params.append(exclude_user_id)
    existing = conn.execute(
        f"""
        SELECT id FROM users
        WHERE tenant_id = ? AND lower(email) = ? AND email <> ''{exclude_clause}
        LIMIT 1
        """,
        tuple(params),
    ).fetchone()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already exists in tenant")


def create_user(
    *,
    username: str,
    password: str,
    full_name: str = "",
    email: str | None = None,
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    normalized_username = normalize_username(username)
    normalized_email = normalize_email(email or "")
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
        ensure_email_available(conn, tenant_id=tenant_id, email=normalized_email)
        cursor = conn.execute(
            """
            INSERT INTO users (tenant_id, username, full_name, email, hashed_password, is_active, is_superuser, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                normalized_username,
                full_name.strip(),
                normalized_email,
                hash_password(password),
                bool(is_active),
                bool(is_superuser),
                now,
                now,
            ),
        )
        user_id = int(getattr(cursor, "lastrowid", 0) or 0)
        if not user_id:
            row = conn.execute(
                "SELECT id FROM users WHERE tenant_id = ? AND username = ?",
                (tenant_id, normalized_username),
            ).fetchone()
            user_id = int(row["id"])
        sync_user_roles(conn, user_id, list(role_keys or []), role_scope=role_scope)

    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


def import_users_batch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows = normalize_import_rows(rows)
    if not normalized_rows:
        return []
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        platform_id = platform_tenant_id(conn)
        tenant_ids = sorted({int(row.get("tenant_id") or platform_id) for row in normalized_rows})
        tenant_rows = conn.execute(
            f"SELECT id, tenant_key FROM tenants WHERE id IN ({', '.join('?' for _ in tenant_ids)})",
            tuple(tenant_ids),
        ).fetchall()
        tenant_keys = {int(row["id"]): str(row["tenant_key"]) for row in tenant_rows}
        missing_tenants = [str(tenant_id) for tenant_id in tenant_ids if tenant_id not in tenant_keys]
        if missing_tenants:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"tenant not found: {', '.join(missing_tenants)}")

        validate_import_user_rows(conn, normalized_rows, platform_id=platform_id, tenant_keys=tenant_keys)
        role_ids_by_scope_key = resolve_import_role_ids(conn, normalized_rows, platform_id=platform_id, tenant_keys=tenant_keys)
        _executemany(
            conn,
            """
            INSERT INTO users (tenant_id, username, full_name, email, hashed_password, is_active, is_superuser, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    int(row.get("tenant_id") or platform_id),
                    row["username"],
                    row["full_name"],
                    row["email"],
                    hash_password(row["password"]),
                    bool(row["is_active"]),
                    bool(row["is_superuser"]),
                    now,
                    now,
                )
                for row in normalized_rows
            ],
        )
        user_rows = conn.execute(
            f"""
            SELECT id, tenant_id, username
            FROM users
            WHERE tenant_id IN ({', '.join('?' for _ in tenant_ids)})
              AND create_time = ?
            """,
            (*tenant_ids, now),
        ).fetchall()
        user_ids_by_key = {
            (int(row["tenant_id"]), str(row["username"])): int(row["id"])
            for row in user_rows
        }
        role_rows: list[tuple[int, int]] = []
        for row in normalized_rows:
            tenant_id = int(row.get("tenant_id") or platform_id)
            user_id = user_ids_by_key[(tenant_id, row["username"])]
            role_scope = "platform" if tenant_keys[tenant_id] == PLATFORM_TENANT_KEY else "tenant"
            seen_role_keys: set[str] = set()
            for role_key in list(row.get("role_keys") or []):
                normalized_role_key = str(role_key).strip()
                if not normalized_role_key or normalized_role_key in seen_role_keys:
                    continue
                seen_role_keys.add(normalized_role_key)
                role_id = role_ids_by_scope_key[(role_scope, normalized_role_key)]
                role_rows.append((user_id, role_id))
        _executemany(
            conn,
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES (?, ?)
            """,
            role_rows,
        )

    ordered_ids = [
        user_ids_by_key[(int(row.get("tenant_id") or platform_id), row["username"])]
        for row in normalized_rows
    ]
    return users_by_ids(ordered_ids)


def normalize_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        username = normalize_username(str(row.get("username", "") or ""))
        password = str(row.get("password", "") or "").strip()
        if not username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 行用户名不能为空")
        if not password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 行初始密码不能为空")
        normalized_rows.append(
            {
                "tenant_id": row.get("tenant_id"),
                "username": username,
                "full_name": str(row.get("full_name", "") or "").strip(),
                "email": normalize_email(str(row.get("email", "") or "")),
                "password": password,
                "role_keys": list(row.get("role_keys") or []),
                "is_active": bool(row.get("is_active", True)),
                "is_superuser": bool(row.get("is_superuser", False)),
            }
        )
    return normalized_rows


def validate_import_user_rows(
    conn: Any,
    rows: list[dict[str, Any]],
    *,
    platform_id: int,
    tenant_keys: dict[int, str],
) -> None:
    seen_usernames: set[tuple[int, str]] = set()
    seen_emails: set[tuple[int, str]] = set()
    for index, row in enumerate(rows, start=1):
        tenant_id = int(row.get("tenant_id") or platform_id)
        username_key = (tenant_id, str(row["username"]))
        if username_key in seen_usernames:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 行用户名在导入文件中重复")
        seen_usernames.add(username_key)
        email = str(row.get("email") or "")
        if email:
            email_key = (tenant_id, email)
            if email_key in seen_emails:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 行邮箱在导入文件中重复")
            seen_emails.add(email_key)
        if bool(row.get("is_superuser")) and tenant_keys[tenant_id] != PLATFORM_TENANT_KEY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 行超级用户必须属于平台租户")

    tenant_ids = sorted({tenant_id for tenant_id, _username in seen_usernames})
    placeholders = ", ".join("?" for _ in tenant_ids)
    existing_rows = conn.execute(
        f"""
        SELECT tenant_id, username, lower(email) AS email
        FROM users
        WHERE tenant_id IN ({placeholders}) AND deleted = 0
        """,
        tuple(tenant_ids),
    ).fetchall()
    existing_usernames = {(int(row["tenant_id"]), str(row["username"])) for row in existing_rows}
    existing_emails = {
        (int(row["tenant_id"]), str(row["email"]))
        for row in existing_rows
        if str(row["email"] or "")
    }
    for index, row in enumerate(rows, start=1):
        tenant_id = int(row.get("tenant_id") or platform_id)
        if (tenant_id, str(row["username"])) in existing_usernames:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"第 {index} 行用户名已存在")
        email = str(row.get("email") or "")
        if email and (tenant_id, email) in existing_emails:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"第 {index} 行邮箱已存在")


def resolve_import_role_ids(
    conn: Any,
    rows: list[dict[str, Any]],
    *,
    platform_id: int,
    tenant_keys: dict[int, str],
) -> dict[tuple[str, str], int]:
    requested: set[tuple[str, str]] = set()
    for row in rows:
        tenant_id = int(row.get("tenant_id") or platform_id)
        role_scope = "platform" if tenant_keys[tenant_id] == PLATFORM_TENANT_KEY else "tenant"
        for role_key in list(row.get("role_keys") or []):
            normalized_key = str(role_key).strip()
            if normalized_key:
                requested.add((role_scope, normalized_key))
    if not requested:
        return {}
    role_keys = sorted({role_key for _scope, role_key in requested})
    scopes = sorted({scope for scope, _role_key in requested})
    role_placeholders = ", ".join("?" for _ in role_keys)
    scope_placeholders = ", ".join("?" for _ in scopes)
    role_rows = conn.execute(
        f"""
        SELECT id, role_scope, role_key
        FROM roles
        WHERE role_key IN ({role_placeholders})
          AND role_scope IN ({scope_placeholders})
          AND deleted = 0
        """,
        (*role_keys, *scopes),
    ).fetchall()
    resolved = {
        (str(row["role_scope"] or "platform"), str(row["role_key"])): int(row["id"])
        for row in role_rows
    }
    missing = sorted(requested - set(resolved))
    if missing:
        scope, role_key = missing[0]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown role keys: {role_key} ({scope})")
    return resolved


def update_user(
    user_id: int,
    *,
    username: str,
    full_name: str = "",
    email: str = "",
    password: str = "",
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    normalized_username = normalize_username(username)
    normalized_email = normalize_email(email)
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
        ensure_email_available(conn, tenant_id=effective_tenant_id, email=normalized_email, exclude_user_id=user_id)
        ensure_last_superuser_survives(conn, user_id, is_active=bool(is_active), is_superuser=bool(is_superuser))

        fields = ["tenant_id = ?", "username = ?", "full_name = ?", "email = ?", "is_active = ?", "is_superuser = ?", "update_time = ?"]
        params: list[Any] = [effective_tenant_id, normalized_username, full_name.strip(), normalized_email, bool(is_active), bool(is_superuser), now]
        if password.strip():
            fields.insert(5, "hashed_password = ?")
            params.insert(5, hash_password(password))
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

    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


def update_own_profile(
    user_id: int,
    *,
    full_name: str,
    email: str | None = None,
    current_password: str = "",
    new_password: str = "",
) -> dict[str, Any]:
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

        fields = ["full_name = ?", "update_time = ?"]
        params: list[Any] = [full_name.strip(), now]
        if email is not None:
            normalized_email = normalize_email(email)
            ensure_email_available(
                conn,
                tenant_id=int(row["tenant_id"]),
                email=normalized_email,
                exclude_user_id=user_id,
            )
            fields.insert(1, "email = ?")
            params.insert(1, normalized_email)
        if new_password.strip():
            if not current_password.strip() or not verify_password(current_password, str(row["hashed_password"])):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="current password is incorrect")
            fields.insert(-1, "hashed_password = ?")
            params.insert(-1, hash_password(new_password))
        params.append(user_id)
        conn.execute(
            f"""
            UPDATE users
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            tuple(params),
        )
        updated = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return public_user(dict(updated))


def set_user_active(user_id: int, is_active: bool) -> dict[str, Any]:
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute("SELECT id, is_superuser FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        ensure_last_superuser_survives(conn, user_id, is_active=bool(is_active), is_superuser=bool(row["is_superuser"]))
        conn.execute(
            """
            UPDATE users
            SET is_active = ?, update_time = ?
            WHERE id = ?
            """,
            (bool(is_active), now, user_id),
        )

    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user
