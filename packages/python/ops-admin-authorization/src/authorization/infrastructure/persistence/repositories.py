from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from authorization.domain.exceptions import AuthorizationDomainError
from authorization.domain.models import DataAccessPolicy, ResourceDescriptorRecord, VALID_DATA_SCOPES, VALID_POLICY_SUBJECT_TYPES
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


def list_data_access_policies(
    *,
    tenant_id: int,
    subject_type: str | None = None,
    subject_id: int | None = None,
    resource_key: str | None = None,
) -> list[DataAccessPolicy]:
    where = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [int(tenant_id)]
    if subject_type:
        where.append("subject_type = ?")
        params.append(subject_type.strip())
    if subject_id:
        where.append("subject_id = ?")
        params.append(int(subject_id))
    if resource_key:
        where.append("resource_key = ?")
        params.append(resource_key.strip())
    with connect(database_target(), readonly=True) as conn:
        require_authorization_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM data_access_policies
            WHERE {" AND ".join(where)}
            ORDER BY subject_type, subject_id, resource_key, action, priority DESC
            """,
            tuple(params),
        ).fetchall()
    return [row_to_data_access_policy(dict(row)) for row in rows]


def save_data_access_policy(
    *,
    tenant_id: int,
    subject_type: str,
    subject_id: int,
    resource_key: str,
    action: str,
    scope: str,
    department_ids: list[int],
    priority: int,
    actor: str,
    actor_id: int | None,
) -> DataAccessPolicy:
    normalized_subject_type = subject_type.strip()
    normalized_subject_id = int(subject_id)
    normalized_resource = resource_key.strip()
    normalized_action = action.strip() or "read"
    normalized_scope = scope.strip()
    normalized_tenant_id = int(tenant_id)
    if not normalized_tenant_id:
        raise AuthorizationDomainError("tenant id is required")
    if normalized_subject_type not in VALID_POLICY_SUBJECT_TYPES:
        raise AuthorizationDomainError("unknown data policy subject")
    if not normalized_subject_id:
        raise AuthorizationDomainError("data policy subject id is required")
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
            FROM data_access_policies
            WHERE tenant_id = ? AND subject_type = ? AND subject_id = ? AND resource_key = ? AND action = ? AND deleted = 0
            """,
            (normalized_tenant_id, normalized_subject_type, normalized_subject_id, normalized_resource, normalized_action),
        ).fetchone()
        values = (
            normalized_scope,
            json.dumps(ids, ensure_ascii=False, separators=(",", ":")),
            int(priority),
            actor,
            actor_id,
            timestamp,
        )
        if existing:
            scope_id = int(existing["id"])
            conn.execute(
                """
                UPDATE data_access_policies
                SET scope = ?, department_ids_json = ?, priority = ?, editor = ?, editor_id = ?,
                    update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ?
                """,
                (*values, scope_id, normalized_tenant_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO data_access_policies (
                    tenant_id, subject_type, subject_id, resource_key, action, scope, department_ids_json, priority,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_tenant_id,
                    normalized_subject_type,
                    normalized_subject_id,
                    normalized_resource,
                    normalized_action,
                    normalized_scope,
                    values[1],
                    values[2],
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
            scope_id = inserted_id(conn, cursor, "data_access_policies", timestamp, actor)
    item = next(
        (
            policy
            for policy in list_data_access_policies(
                tenant_id=normalized_tenant_id,
                subject_type=normalized_subject_type,
                subject_id=normalized_subject_id,
                resource_key=normalized_resource,
            )
            if policy.id == scope_id
        ),
        None,
    )
    if item is None:
        raise RuntimeError("data access policy save failed")
    return item


def delete_data_access_policy(*, tenant_id: int, policy_id: int) -> DataAccessPolicy | None:
    timestamp = now_iso()
    normalized_tenant_id = int(tenant_id)
    with connect(database_target(), readonly=False) as conn:
        require_authorization_schema(conn)
        existing = conn.execute(
            "SELECT * FROM data_access_policies WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (policy_id, normalized_tenant_id),
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE data_access_policies
            SET deleted = 1, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ?
            """,
            (timestamp, policy_id, normalized_tenant_id),
        )
    return row_to_data_access_policy(dict(existing))


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


def row_to_data_access_policy(row: dict[str, Any]) -> DataAccessPolicy:
    return DataAccessPolicy(
        id=int(row["id"]),
        tenant_id=int(row.get("tenant_id") or 0),
        subject_type=str(row.get("subject_type") or ""),
        subject_id=int(row.get("subject_id") or 0),
        resource_key=str(row.get("resource_key") or ""),
        action=str(row.get("action") or "read"),
        scope=str(row.get("scope") or "self"),
        department_ids=tuple(int(value) for value in decode_list(row.get("department_ids_json")) if int(value or 0)),
        priority=int(row.get("priority") or 0),
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
