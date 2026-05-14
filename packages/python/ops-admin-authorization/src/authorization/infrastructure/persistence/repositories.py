from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from authorization.domain.exceptions import AuthorizationDomainError
from authorization.domain.models import ResourceDescriptorRecord, RoleDataScope, VALID_DATA_SCOPES
from authorization.infrastructure.persistence.bootstrap import require_authorization_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def list_resource_descriptors() -> list[ResourceDescriptorRecord]:
    with connect(database_target(), readonly=True) as conn:
        require_authorization_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM data_resource_descriptors
            WHERE deleted = 0
            ORDER BY resource_key
            """
        ).fetchall()
    return [row_to_resource_descriptor(dict(row)) for row in rows]


def get_resource_descriptor(resource_key: str) -> ResourceDescriptorRecord | None:
    with connect(database_target(), readonly=True) as conn:
        require_authorization_schema(conn)
        row = conn.execute(
            "SELECT * FROM data_resource_descriptors WHERE resource_key = ? AND deleted = 0",
            (resource_key.strip(),),
        ).fetchone()
    return row_to_resource_descriptor(dict(row)) if row else None


def upsert_resource_descriptor(payload: dict[str, Any], *, actor: str, actor_id: int | None) -> ResourceDescriptorRecord:
    resource_key = str(payload.get("resource_key") or "").strip()
    name = str(payload.get("name") or "").strip()
    if not resource_key:
        raise AuthorizationDomainError("resource key is required")
    if not name:
        raise AuthorizationDomainError("resource name is required")
    supported_scopes = normalize_scopes(payload.get("supported_scopes"))
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_authorization_schema(conn)
        existing = conn.execute(
            "SELECT id FROM data_resource_descriptors WHERE resource_key = ? AND deleted = 0",
            (resource_key,),
        ).fetchone()
        values = (
            name,
            str(payload.get("description") or "").strip(),
            str(payload.get("tenant_column") or "tenant_id").strip() or "tenant_id",
            str(payload.get("creator_column") or "creator_id").strip() or "creator_id",
            str(payload.get("owner_user_column") or "owner_user_id").strip() or "owner_user_id",
            str(payload.get("owner_department_column") or "owner_department_id").strip() or "owner_department_id",
            json.dumps(supported_scopes, ensure_ascii=False, separators=(",", ":")),
            bool(payload.get("requires_data_scope", False)),
            actor,
            actor_id,
            timestamp,
        )
        try:
            if existing:
                descriptor_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE data_resource_descriptors
                    SET name = ?, description = ?, tenant_column = ?, creator_column = ?,
                        owner_user_column = ?, owner_department_column = ?, supported_scopes_json = ?,
                        requires_data_scope = ?, editor = ?, editor_id = ?, update_time = ?,
                        lock_version = lock_version + 1
                    WHERE id = ?
                    """,
                    (*values, descriptor_id),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO data_resource_descriptors (
                        resource_key, name, description, tenant_column, creator_column,
                        owner_user_column, owner_department_column, supported_scopes_json,
                        requires_data_scope, creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        resource_key,
                        *values[:8],
                        actor,
                        actor_id,
                        actor,
                        actor_id,
                        timestamp,
                        timestamp,
                    ),
                )
                descriptor_id = inserted_id(conn, cursor, "data_resource_descriptors", timestamp, actor)
        except sqlite3.IntegrityError as exc:
            raise AuthorizationDomainError("resource descriptor already exists") from exc
    descriptor = next((item for item in list_resource_descriptors() if item.id == descriptor_id), None)
    if descriptor is None:
        raise RuntimeError("resource descriptor save failed")
    return descriptor


def list_role_data_scopes(*, role_key: str | None = None) -> list[RoleDataScope]:
    where = ["deleted = 0"]
    params: list[Any] = []
    if role_key:
        where.append("role_key = ?")
        params.append(role_key.strip())
    with connect(database_target(), readonly=True) as conn:
        require_authorization_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM role_data_scopes
            WHERE {" AND ".join(where)}
            ORDER BY role_key, resource_key, action
            """,
            tuple(params),
        ).fetchall()
    return [row_to_role_data_scope(dict(row)) for row in rows]


def save_role_data_scope(
    *,
    role_key: str,
    resource_key: str,
    action: str,
    scope: str,
    department_ids: list[int],
    actor: str,
    actor_id: int | None,
) -> RoleDataScope:
    normalized_role = role_key.strip()
    normalized_resource = resource_key.strip()
    normalized_action = action.strip() or "read"
    normalized_scope = scope.strip()
    if normalized_scope not in VALID_DATA_SCOPES:
        raise AuthorizationDomainError("unknown data scope")
    descriptor = get_resource_descriptor(normalized_resource)
    if descriptor and normalized_scope not in descriptor.supported_scopes:
        raise AuthorizationDomainError("scope is not supported by resource")
    ids = [int(value) for value in department_ids if int(value or 0)]
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_authorization_schema(conn)
        existing = conn.execute(
            """
            SELECT id
            FROM role_data_scopes
            WHERE role_key = ? AND resource_key = ? AND action = ? AND deleted = 0
            """,
            (normalized_role, normalized_resource, normalized_action),
        ).fetchone()
        values = (
            normalized_scope,
            json.dumps(ids, ensure_ascii=False, separators=(",", ":")),
            actor,
            actor_id,
            timestamp,
        )
        if existing:
            scope_id = int(existing["id"])
            conn.execute(
                """
                UPDATE role_data_scopes
                SET scope = ?, department_ids_json = ?, editor = ?, editor_id = ?,
                    update_time = ?, lock_version = lock_version + 1
                WHERE id = ?
                """,
                (*values, scope_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO role_data_scopes (
                    role_key, resource_key, action, scope, department_ids_json,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_role,
                    normalized_resource,
                    normalized_action,
                    normalized_scope,
                    values[1],
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
            scope_id = inserted_id(conn, cursor, "role_data_scopes", timestamp, actor)
    item = next((scope_item for scope_item in list_role_data_scopes(role_key=normalized_role) if scope_item.id == scope_id), None)
    if item is None:
        raise RuntimeError("role data scope save failed")
    return item


def delete_role_data_scope(scope_id: int) -> RoleDataScope | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_authorization_schema(conn)
        existing = conn.execute("SELECT * FROM role_data_scopes WHERE id = ? AND deleted = 0", (scope_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE role_data_scopes
            SET deleted = 1, update_time = ?, lock_version = lock_version + 1
            WHERE id = ?
            """,
            (timestamp, scope_id),
        )
    return row_to_role_data_scope(dict(existing))


def row_to_resource_descriptor(row: dict[str, Any]) -> ResourceDescriptorRecord:
    return ResourceDescriptorRecord(
        id=int(row["id"]),
        resource_key=str(row.get("resource_key") or ""),
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        tenant_column=str(row.get("tenant_column") or "tenant_id"),
        creator_column=str(row.get("creator_column") or "creator_id"),
        owner_user_column=str(row.get("owner_user_column") or "owner_user_id"),
        owner_department_column=str(row.get("owner_department_column") or "owner_department_id"),
        supported_scopes=tuple(normalize_scopes(row.get("supported_scopes_json"))),
        requires_data_scope=bool(row.get("requires_data_scope", False)),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_role_data_scope(row: dict[str, Any]) -> RoleDataScope:
    return RoleDataScope(
        id=int(row["id"]),
        role_key=str(row.get("role_key") or ""),
        resource_key=str(row.get("resource_key") or ""),
        action=str(row.get("action") or "read"),
        scope=str(row.get("scope") or "self"),
        department_ids=tuple(int(value) for value in decode_list(row.get("department_ids_json")) if int(value or 0)),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def normalize_scopes(value: Any) -> list[str]:
    items = decode_list(value)
    normalized = [str(item).strip() for item in items if str(item).strip() in VALID_DATA_SCOPES]
    return normalized or ["self", "department", "department_and_children", "custom_departments", "tenant"]


def decode_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if not value:
        return []
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def inserted_id(conn: Any, cursor: Any, table_name: str, timestamp: str, actor: str) -> int:
    row_id = int(getattr(cursor, "lastrowid", 0) or 0)
    if row_id:
        return row_id
    row = conn.execute(
        f"""
        SELECT id
        FROM {table_name}
        WHERE create_time = ? AND creator = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (timestamp, actor),
    ).fetchone()
    return int(row["id"])
