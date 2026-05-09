from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from identity_access.infrastructure.persistence.common import (
    DEFAULT_TENANT_KEY,
    PLATFORM_TENANT_KEY,
    auth_database_target,
    connect,
    ensure_tenant_menu_defaults,
    now_iso,
    require_auth_ready,
)


def row_to_tenant(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "key": str(row.get("tenant_key", "")),
        "tenant_key": str(row.get("tenant_key", "")),
        "name": str(row.get("name", "")),
        "status": str(row.get("status", "active") or "active"),
        "remark": str(row.get("remark", "") or ""),
        "create_time": str(row.get("create_time", "") or ""),
        "update_time": str(row.get("update_time", "") or ""),
    }


def default_tenant(conn: Any) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM tenants WHERE tenant_key = ?", (DEFAULT_TENANT_KEY,)).fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="default tenant missing")
    return row_to_tenant(dict(row))


def get_tenant_by_id(conn: Any, tenant_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    return row_to_tenant(dict(row)) if row else None


def get_business_tenant_by_id(conn: Any, tenant_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM tenants WHERE id = ? AND tenant_key <> ?",
        (tenant_id, PLATFORM_TENANT_KEY),
    ).fetchone()
    return row_to_tenant(dict(row)) if row else None


def get_tenant_by_key(conn: Any, tenant_key: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM tenants WHERE tenant_key = ?", (tenant_key.strip(),)).fetchone()
    return row_to_tenant(dict(row)) if row else None


def list_tenants(*, q: str | None = None) -> list[dict[str, Any]]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        params: list[Any] = [PLATFORM_TENANT_KEY]
        where = "WHERE t.tenant_key <> ?"
        if q and q.strip():
            where += " AND (lower(t.tenant_key) LIKE ? OR lower(t.name) LIKE ?)"
            like = f"%{q.strip().lower()}%"
            params.extend([like, like])
        rows = conn.execute(
            f"""
            SELECT
                t.*,
                (SELECT COUNT(*) FROM tenant_memberships tm WHERE tm.tenant_id = t.id) AS user_count,
                (SELECT COUNT(*) FROM api_keys ak WHERE ak.tenant_id = t.id AND ak.is_active = ?) AS api_key_count
            FROM tenants t
            {where}
            ORDER BY t.id
            """,
            (True, *params),
        ).fetchall()
    result = []
    for row in rows:
        item = row_to_tenant(dict(row))
        item["user_count"] = int(dict(row).get("user_count", 0) or 0)
        item["api_key_count"] = int(dict(row).get("api_key_count", 0) or 0)
        result.append(item)
    return result


def create_tenant(*, tenant_key: str, name: str, remark: str = "", status_value: str = "active") -> dict[str, Any]:
    normalized_key = tenant_key.strip()
    normalized_name = name.strip()
    normalized_status = status_value.strip().lower() or "active"
    if not normalized_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant key is required")
    if normalized_key == PLATFORM_TENANT_KEY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="platform tenant is reserved")
    if not normalized_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant name is required")
    if normalized_status not in {"active", "suspended"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid tenant status")
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        existing = conn.execute("SELECT id FROM tenants WHERE tenant_key = ?", (normalized_key,)).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="tenant key already exists")
        cursor = conn.execute(
            """
            INSERT INTO tenants (tenant_key, name, status, remark, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (normalized_key, normalized_name, normalized_status, remark.strip(), now, now),
        )
        tenant_id = int(getattr(cursor, "lastrowid", 0) or 0)
        if not tenant_id:
            row = conn.execute("SELECT id FROM tenants WHERE tenant_key = ?", (normalized_key,)).fetchone()
            tenant_id = int(row["id"])
        ensure_tenant_menu_defaults(conn, tenant_id)
        tenant = get_business_tenant_by_id(conn, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")
    return tenant


def update_tenant(tenant_id: int, *, name: str, remark: str = "", status_value: str = "active") -> dict[str, Any]:
    normalized_name = name.strip()
    normalized_status = status_value.strip().lower() or "active"
    if not normalized_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant name is required")
    if normalized_status not in {"active", "suspended"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid tenant status")
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute(
            "SELECT id FROM tenants WHERE id = ? AND tenant_key <> ?",
            (tenant_id, PLATFORM_TENANT_KEY),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        conn.execute(
            """
            UPDATE tenants
            SET name = ?, remark = ?, status = ?, update_time = ?
            WHERE id = ?
            """,
            (normalized_name, remark.strip(), normalized_status, now_iso(), tenant_id),
        )
        tenant = get_business_tenant_by_id(conn, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")
    return tenant


def set_tenant_status(tenant_id: int, status_value: str) -> dict[str, Any]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        tenant = get_business_tenant_by_id(conn, tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
    return update_tenant(
        tenant_id,
        name=str(tenant["name"]),
        remark=str(tenant.get("remark", "")),
        status_value=status_value,
    )


def memberships_for_user(user_id: int) -> list[dict[str, Any]]:
    if not user_id:
        return []
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        rows = conn.execute(
            """
            SELECT t.*, tm.is_tenant_admin
            FROM tenant_memberships tm
            JOIN tenants t ON t.id = tm.tenant_id
            WHERE tm.user_id = ?
              AND t.tenant_key <> ?
            ORDER BY t.id
            """,
            (user_id, PLATFORM_TENANT_KEY),
        ).fetchall()
    result = []
    for row in rows:
        item = row_to_tenant(dict(row))
        item["is_tenant_admin"] = bool(dict(row).get("is_tenant_admin", False))
        result.append(item)
    return result


def ensure_membership(conn: Any, *, tenant_id: int, user_id: int, is_tenant_admin: bool = False) -> None:
    existing = conn.execute(
        "SELECT 1 FROM tenant_memberships WHERE tenant_id = ? AND user_id = ?",
        (tenant_id, user_id),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE tenant_memberships
            SET is_tenant_admin = ?
            WHERE tenant_id = ? AND user_id = ?
            """,
            (bool(is_tenant_admin), tenant_id, user_id),
        )
        return
    conn.execute(
        """
        INSERT INTO tenant_memberships (tenant_id, user_id, is_tenant_admin, create_time)
        VALUES (?, ?, ?, ?)
        """,
        (tenant_id, user_id, bool(is_tenant_admin), now_iso()),
    )


def remove_membership(conn: Any, *, tenant_id: int, user_id: int) -> None:
    conn.execute(
        "DELETE FROM tenant_memberships WHERE tenant_id = ? AND user_id = ?",
        (tenant_id, user_id),
    )
