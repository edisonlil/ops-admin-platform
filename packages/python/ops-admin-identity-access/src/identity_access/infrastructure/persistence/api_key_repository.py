from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from identity_access.infrastructure.persistence.common import (
    DEFAULT_TENANT_KEY,
    auth_database_target,
    connect,
    now_iso,
    require_auth_ready,
    row_to_api_key,
)
from identity_access.infrastructure.security import generate_api_key, hash_api_key
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, append_data_scope_sql
from system.application.sorting import build_order_by, parse_sort_params


API_KEY_RESOURCE = ResourceDescriptor(resource_key="identity.api-key")
API_KEY_SORT_COLUMNS = {
    "id": "id",
    "tenant_id": "tenant_id",
    "name": "name",
    "prefix": "prefix",
    "is_active": "is_active",
    "create_time": "create_time",
    "update_time": "update_time",
}


def create_api_key(
    *,
    name: str,
    creator: str,
    tenant_id: int | None = None,
    owner_user_id: int | None = None,
    owner_department_id: int | None = None,
) -> dict[str, Any]:
    key = generate_api_key()
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        if tenant_id is None:
            tenant_row = conn.execute("SELECT id FROM tenants WHERE tenant_key = ?", (DEFAULT_TENANT_KEY,)).fetchone()
            if not tenant_row:
                raise HTTPException(status_code=500, detail="default tenant missing")
            tenant_id = int(tenant_row["id"])
        cursor = conn.execute(
            """
            INSERT INTO api_keys (
                tenant_id, name, key_hash, key_plain, prefix, is_active, owner_user_id,
                owner_department_id, creator, creator_id, editor, editor_id,
                create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                name.strip(),
                hash_api_key(key),
                key,
                key[:12],
                True,
                owner_user_id,
                owner_department_id,
                creator,
                owner_user_id,
                creator,
                owner_user_id,
                now,
                now,
            ),
        )
        key_id = int(getattr(cursor, "lastrowid", 0) or 0)
        if not key_id:
            row = conn.execute("SELECT id FROM api_keys WHERE key_hash = ?", (hash_api_key(key),)).fetchone()
            key_id = int(row["id"])
        row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
    return {"key": key, "item": row_to_api_key(dict(row))}


def list_api_keys(
    *,
    tenant_id: int | None = None,
    data_scope: DataAccessPredicate | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> list[dict[str, Any]]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        filters = ["deleted = 0"]
        params: list[Any] = []
        if tenant_id is not None:
            filters.insert(0, "tenant_id = ?")
            params.insert(0, tenant_id)
        append_data_scope_sql(filters, params, data_scope, API_KEY_RESOURCE)
        where = f"WHERE {' AND '.join(filters)}"
        order_by = build_order_by(
            parse_sort_params(sort_by, sort_dir),
            allowed=API_KEY_SORT_COLUMNS,
            default="is_active DESC, create_time DESC, id DESC",
            tie_breaker="id DESC",
        )
        rows = conn.execute(
            f"""
            SELECT *
            FROM api_keys
            {where}
            ORDER BY {order_by}
            """,
            tuple(params),
        ).fetchall()
    return [row_to_api_key(dict(row)) for row in rows]


def revoke_api_key(key_id: int) -> dict[str, Any]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="api key not found")
        conn.execute(
            """
            UPDATE api_keys
            SET is_active = ?, deleted = ?, update_time = ?, editor = ?, lock_version = lock_version + 1
            WHERE id = ?
            """,
            (False, True, now_iso(), str(row["name"]), key_id),
        )
        row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
    return row_to_api_key(dict(row))


def update_api_key(key_id: int, *, name: str, editor: str = "", editor_id: int | None = None) -> dict[str, Any]:
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="api key name must not be blank")
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute("SELECT * FROM api_keys WHERE id = ? AND deleted = 0", (key_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="api key not found")
        conn.execute(
            """
            UPDATE api_keys
            SET name = ?, update_time = ?, editor = ?, editor_id = ?, lock_version = lock_version + 1
            WHERE id = ?
            """,
            (normalized_name, now_iso(), editor or None, editor_id, key_id),
        )
        row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
    return row_to_api_key(dict(row))


def get_api_key(key_id: int) -> dict[str, Any] | None:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
    return row_to_api_key(dict(row)) if row else None


def validate_api_key(api_key: str) -> dict[str, Any] | None:
    api_key = api_key.strip()
    if not api_key:
        return None
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        row = conn.execute(
            """
            SELECT ak.*, t.tenant_key, t.name AS tenant_name, t.status AS tenant_status
            FROM api_keys ak
            LEFT JOIN tenants t ON t.id = ak.tenant_id
            WHERE ak.key_hash = ? AND ak.is_active = ? AND ak.deleted = 0
            """,
            (hash_api_key(api_key), True),
        ).fetchone()
    if not row:
        return None
    item = row_to_api_key(dict(row))
    if str(dict(row).get("tenant_status", "active") or "active") != "active":
        return None
    return {
        "auth_type": "api_key",
        "api_key": item,
        "tenant_id": int(dict(row).get("tenant_id", 0) or 0),
        "current_tenant": {
            "id": int(dict(row).get("tenant_id", 0) or 0),
            "key": str(dict(row).get("tenant_key", DEFAULT_TENANT_KEY) or DEFAULT_TENANT_KEY),
            "tenant_key": str(dict(row).get("tenant_key", DEFAULT_TENANT_KEY) or DEFAULT_TENANT_KEY),
            "name": str(dict(row).get("tenant_name", "Default Tenant") or "Default Tenant"),
            "status": str(dict(row).get("tenant_status", "active") or "active"),
        },
    }
