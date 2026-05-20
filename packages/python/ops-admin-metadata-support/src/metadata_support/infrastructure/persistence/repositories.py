from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from metadata_support.domain.exceptions import MetadataSupportValidationError
from metadata_support.domain.models import (
    MetadataFieldDefinition,
    MetadataResourceType,
    MetadataTag,
    MetadataTagGroup,
    ResourceMetadata,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    VALUE_TYPE_BOOLEAN,
    VALUE_TYPE_DATETIME,
    VALUE_TYPE_NUMBER,
    VALUE_TYPE_STRING,
)
from metadata_support.infrastructure.persistence.bootstrap import require_metadata_support_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def list_resource_types(*, tenant_id: int, page: int, page_size: int, keyword: str, status: str | None) -> tuple[list[MetadataResourceType], int]:
    return list_simple(
        table="metadata_resource_types",
        mapper=row_to_resource_type,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        keyword_columns=("code", "name", "description", "owner_context"),
        status=status,
        order_by="code ASC, id DESC",
    )


def save_resource_type(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MetadataResourceType:
    saved_id = save_simple(
        table="metadata_resource_types",
        tenant_id=tenant_id,
        payload=payload,
        actor=actor,
        actor_id=actor_id,
        columns=("code", "name", "owner_context", "description", "status"),
    )
    item = get_by_id("metadata_resource_types", tenant_id=tenant_id, row_id=saved_id, mapper=row_to_resource_type)
    if not item:
        raise RuntimeError("resource type save failed")
    return item


def list_field_definitions(
    *, tenant_id: int, resource_type_code: str, page: int, page_size: int, keyword: str, status: str | None
) -> tuple[list[MetadataFieldDefinition], int]:
    offset = (page - 1) * page_size
    filters = ["tenant_id IN (0, ?)", "resource_type_code = ?", "deleted = 0"]
    params: list[Any] = [tenant_id, resource_type_code]
    if keyword.strip():
        filters.append("(field_key LIKE ? OR display_name LIKE ?)")
        like = f"%{keyword.strip()}%"
        params.extend([like, like])
    if status:
        filters.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_metadata_support_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM metadata_field_definitions WHERE {where_sql}", tuple(params)).fetchone())
        rows = conn.execute(
            f"""
            SELECT *
            FROM metadata_field_definitions
            WHERE {where_sql}
            ORDER BY sort_order ASC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, offset),
        ).fetchall()
    return [row_to_field_definition(dict(row)) for row in rows], total


def save_field_definition(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MetadataFieldDefinition:
    saved_id = save_simple(
        table="metadata_field_definitions",
        tenant_id=tenant_id,
        payload=payload,
        actor=actor,
        actor_id=actor_id,
        columns=("resource_type_code", "field_key", "display_name", "value_type", "required", "searchable", "sort_order", "status"),
    )
    item = get_by_id("metadata_field_definitions", tenant_id=tenant_id, row_id=saved_id, mapper=row_to_field_definition)
    if not item:
        raise RuntimeError("field definition save failed")
    return item


def list_tag_groups(*, tenant_id: int, page: int, page_size: int, keyword: str, status: str | None) -> tuple[list[MetadataTagGroup], int]:
    return list_simple(
        table="metadata_tag_groups",
        mapper=row_to_tag_group,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        keyword_columns=("code", "name", "description"),
        status=status,
        order_by="sort_order ASC, id DESC",
    )


def save_tag_group(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MetadataTagGroup:
    saved_id = save_simple(
        table="metadata_tag_groups",
        tenant_id=tenant_id,
        payload=payload,
        actor=actor,
        actor_id=actor_id,
        columns=("code", "name", "description", "sort_order", "status"),
    )
    item = get_by_id("metadata_tag_groups", tenant_id=tenant_id, row_id=saved_id, mapper=row_to_tag_group)
    if not item:
        raise RuntimeError("tag group save failed")
    return item


def list_tags(
    *, tenant_id: int, page: int, page_size: int, keyword: str, group_id: int | None, status: str | None
) -> tuple[list[MetadataTag], int]:
    offset = (page - 1) * page_size
    filters = ["tenant_id IN (0, ?)", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if keyword.strip():
        filters.append("(code LIKE ? OR name LIKE ? OR description LIKE ?)")
        like = f"%{keyword.strip()}%"
        params.extend([like, like, like])
    if group_id is not None:
        filters.append("group_id = ?")
        params.append(group_id)
    if status:
        filters.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_metadata_support_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM metadata_tags WHERE {where_sql}", tuple(params)).fetchone())
        rows = conn.execute(
            f"""
            SELECT *
            FROM metadata_tags
            WHERE {where_sql}
            ORDER BY sort_order ASC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, offset),
        ).fetchall()
    return [row_to_tag(dict(row)) for row in rows], total


def save_tag(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MetadataTag:
    saved_id = save_simple(
        table="metadata_tags",
        tenant_id=tenant_id,
        payload=payload,
        actor=actor,
        actor_id=actor_id,
        columns=("group_id", "code", "name", "color", "description", "sort_order", "status"),
    )
    item = get_by_id("metadata_tags", tenant_id=tenant_id, row_id=saved_id, mapper=row_to_tag)
    if not item:
        raise RuntimeError("tag save failed")
    return item


def ensure_tag(*, tenant_id: int, code: str, actor: str, actor_id: int | None) -> MetadataTag:
    with connect(database_target(), readonly=False) as conn:
        require_metadata_support_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM metadata_tags
            WHERE tenant_id = ? AND code = ? AND deleted = 0
            """,
            (tenant_id, code),
        ).fetchone()
        if row:
            return row_to_tag(dict(row))
        timestamp = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO metadata_tags (
                tenant_id, group_id, code, name, color, description, sort_order, status,
                creator, creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, None, code, code, "", "", 0, STATUS_ACTIVE, actor, actor_id, actor, actor_id, timestamp, timestamp),
        )
        saved_id = inserted_id(conn, cursor, "metadata_tags", timestamp, actor)
        row = conn.execute("SELECT * FROM metadata_tags WHERE id = ?", (saved_id,)).fetchone()
    return row_to_tag(dict(row))


def bind_resource(
    *,
    tenant_id: int,
    resource_type_code: str,
    resource_id: str,
    metadata: dict[str, Any],
    tag_codes: list[str],
    actor: str,
    actor_id: int | None,
) -> ResourceMetadata:
    timestamp = now_iso()
    tags = [ensure_tag(tenant_id=tenant_id, code=code, actor=actor, actor_id=actor_id) for code in tag_codes]
    with connect(database_target(), readonly=False) as conn:
        require_metadata_support_schema(conn)
        existing = conn.execute(
            """
            SELECT id
            FROM metadata_resource_metadata
            WHERE tenant_id = ? AND resource_type_code = ? AND resource_id = ? AND deleted = 0
            """,
            (tenant_id, resource_type_code, resource_id),
        ).fetchone()
        if existing:
            resource_metadata_id = int(existing["id"])
            conn.execute(
                """
                UPDATE metadata_resource_metadata
                SET metadata_json = ?, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE id = ?
                """,
                (encode_json(metadata), actor, actor_id, timestamp, resource_metadata_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO metadata_resource_metadata (
                    tenant_id, resource_type_code, resource_id, metadata_json,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, resource_type_code, resource_id, encode_json(metadata), actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            resource_metadata_id = inserted_id(conn, cursor, "metadata_resource_metadata", timestamp, actor)
        replace_metadata_entries(
            conn,
            tenant_id=tenant_id,
            resource_type_code=resource_type_code,
            resource_id=resource_id,
            metadata=metadata,
            actor=actor,
            actor_id=actor_id,
            timestamp=timestamp,
        )
        replace_resource_tags(
            conn,
            tenant_id=tenant_id,
            resource_type_code=resource_type_code,
            resource_id=resource_id,
            tags=tags,
            actor=actor,
            actor_id=actor_id,
            timestamp=timestamp,
        )
        row = conn.execute("SELECT * FROM metadata_resource_metadata WHERE id = ?", (resource_metadata_id,)).fetchone()
    return row_to_resource_metadata(dict(row))


def get_resource(*, tenant_id: int, resource_type_code: str, resource_id: str) -> tuple[ResourceMetadata | None, list[MetadataTag]]:
    with connect(database_target(), readonly=True) as conn:
        require_metadata_support_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM metadata_resource_metadata
            WHERE tenant_id = ? AND resource_type_code = ? AND resource_id = ? AND deleted = 0
            """,
            (tenant_id, resource_type_code, resource_id),
        ).fetchone()
        tag_rows = conn.execute(
            """
            SELECT t.*
            FROM metadata_resource_tags rt
            JOIN metadata_tags t ON t.id = rt.tag_id AND t.deleted = 0
            WHERE rt.tenant_id = ? AND rt.resource_type_code = ? AND rt.resource_id = ? AND rt.deleted = 0
            ORDER BY t.sort_order ASC, t.id DESC
            """,
            (tenant_id, resource_type_code, resource_id),
        ).fetchall()
    return (row_to_resource_metadata(dict(row)) if row else None, [row_to_tag(dict(item)) for item in tag_rows])


def search_resource_ids(
    *,
    tenant_id: int,
    resource_type_code: str,
    metadata_filters: list[dict[str, Any]],
    tag_codes: list[str],
    max_results: int,
    start: int,
) -> tuple[list[str], int]:
    filters = ["m.tenant_id = ?", "m.resource_type_code = ?", "m.deleted = 0"]
    params: list[Any] = [tenant_id, resource_type_code]
    for item in metadata_filters:
        exists_sql, exists_params = metadata_filter_exists_sql(item)
        filters.append(exists_sql)
        params.extend(exists_params)
    for code in tag_codes:
        filters.append(
            """
            EXISTS (
                SELECT 1
                FROM metadata_resource_tags rt
                WHERE rt.tenant_id = m.tenant_id
                  AND rt.resource_type_code = m.resource_type_code
                  AND rt.resource_id = m.resource_id
                  AND rt.tag_code = ?
                  AND rt.deleted = 0
            )
            """
        )
        params.append(code)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_metadata_support_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM metadata_resource_metadata m WHERE {where_sql}", tuple(params)).fetchone())
        rows = conn.execute(
            f"""
            SELECT m.resource_id
            FROM metadata_resource_metadata m
            WHERE {where_sql}
            ORDER BY m.update_time DESC, m.id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, max_results, start),
        ).fetchall()
    return [str(row["resource_id"]) for row in rows], total


def metadata_filter_exists_sql(item: dict[str, Any]) -> tuple[str, list[Any]]:
    field_key = str(item["field_key"])
    op = str(item["op"])
    value_type = str(item["value_type"])
    column = value_column(value_type)
    values = item.get("value")
    params: list[Any] = [field_key]
    if op == "between":
        if not isinstance(values, list | tuple) or len(values) != 2:
            raise MetadataSupportValidationError("between metadata filter requires two values")
        comparison = f"{column} BETWEEN ? AND ?"
        params.extend([normalize_index_value(value_type, values[0]), normalize_index_value(value_type, values[1])])
    elif op == "contains":
        comparison = f"{column} LIKE ?"
        params.append(f"%{str(values)}%")
    else:
        sql_op = {"eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[op]
        comparison = f"{column} {sql_op} ?"
        params.append(normalize_index_value(value_type, values))
    return (
        f"""
        EXISTS (
            SELECT 1
            FROM metadata_resource_metadata_entries e
            WHERE e.tenant_id = m.tenant_id
              AND e.resource_type_code = m.resource_type_code
              AND e.resource_id = m.resource_id
              AND e.field_key = ?
              AND e.deleted = 0
              AND {comparison}
        )
        """,
        params,
    )


def replace_metadata_entries(
    conn: Any,
    *,
    tenant_id: int,
    resource_type_code: str,
    resource_id: str,
    metadata: dict[str, Any],
    actor: str,
    actor_id: int | None,
    timestamp: str,
) -> None:
    conn.execute(
        """
        UPDATE metadata_resource_metadata_entries
        SET deleted = 1, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
        WHERE tenant_id = ? AND resource_type_code = ? AND resource_id = ? AND deleted = 0
        """,
        (actor, actor_id, timestamp, tenant_id, resource_type_code, resource_id),
    )
    for key, value in flatten_metadata(metadata):
        value_type = infer_value_type(value)
        value_text = normalize_index_value(VALUE_TYPE_STRING, value) if value_type == VALUE_TYPE_STRING else None
        value_number = normalize_index_value(VALUE_TYPE_NUMBER, value) if value_type == VALUE_TYPE_NUMBER else None
        value_datetime = normalize_index_value(VALUE_TYPE_DATETIME, value) if value_type == VALUE_TYPE_DATETIME else None
        value_boolean = normalize_index_value(VALUE_TYPE_BOOLEAN, value) if value_type == VALUE_TYPE_BOOLEAN else None
        conn.execute(
            """
            INSERT INTO metadata_resource_metadata_entries (
                tenant_id, resource_type_code, resource_id, field_key, value_type,
                value_text, value_number, value_datetime, value_boolean,
                creator, creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                resource_type_code,
                resource_id,
                key,
                value_type,
                value_text,
                value_number,
                value_datetime,
                value_boolean,
                actor,
                actor_id,
                actor,
                actor_id,
                timestamp,
                timestamp,
            ),
        )


def replace_resource_tags(
    conn: Any,
    *,
    tenant_id: int,
    resource_type_code: str,
    resource_id: str,
    tags: list[MetadataTag],
    actor: str,
    actor_id: int | None,
    timestamp: str,
) -> None:
    conn.execute(
        """
        UPDATE metadata_resource_tags
        SET deleted = 1, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
        WHERE tenant_id = ? AND resource_type_code = ? AND resource_id = ? AND deleted = 0
        """,
        (actor, actor_id, timestamp, tenant_id, resource_type_code, resource_id),
    )
    for tag in tags:
        conn.execute(
            """
            INSERT INTO metadata_resource_tags (
                tenant_id, resource_type_code, resource_id, tag_id, tag_code,
                creator, creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, resource_type_code, resource_id, tag.id, tag.code, actor, actor_id, actor, actor_id, timestamp, timestamp),
        )


def list_simple(
    *,
    table: str,
    mapper: Any,
    tenant_id: int,
    page: int,
    page_size: int,
    keyword: str,
    keyword_columns: tuple[str, ...],
    status: str | None,
    order_by: str,
) -> tuple[list[Any], int]:
    offset = (page - 1) * page_size
    filters = ["tenant_id IN (0, ?)", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if keyword.strip():
        filters.append("(" + " OR ".join(f"{column} LIKE ?" for column in keyword_columns) + ")")
        params.extend([f"%{keyword.strip()}%" for _ in keyword_columns])
    if status:
        filters.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_metadata_support_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM {table} WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT *
            FROM {table}
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, offset),
        ).fetchall()
    return [mapper(dict(row)) for row in rows], total


def save_simple(
    *,
    table: str,
    tenant_id: int,
    payload: dict[str, Any],
    actor: str,
    actor_id: int | None,
    columns: tuple[str, ...],
) -> int:
    timestamp = now_iso()
    row_id = int(payload.get("id") or 0)
    values = [payload.get(column) for column in columns]
    with connect(database_target(), readonly=False) as conn:
        require_metadata_support_schema(conn)
        try:
            if row_id:
                assignments = ", ".join(f"{column} = ?" for column in columns)
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET {assignments}, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                    WHERE id = ? AND tenant_id = ? AND deleted = 0
                    """,
                    (*values, actor, actor_id, timestamp, row_id, tenant_id),
                )
                return row_id
            column_list = ", ".join(("tenant_id", *columns, "creator", "creator_id", "editor", "editor_id", "create_time", "update_time"))
            placeholders = ", ".join("?" for _ in ("tenant_id", *columns, "creator", "creator_id", "editor", "editor_id", "create_time", "update_time"))
            cursor = conn.execute(
                f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
                (tenant_id, *values, actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            return inserted_id(conn, cursor, table, timestamp, actor)
        except sqlite3.IntegrityError as exc:
            raise_unique_constraint_error(exc)


def get_by_id(table: str, *, tenant_id: int, row_id: int, mapper: Any) -> Any | None:
    with connect(database_target(), readonly=True) as conn:
        require_metadata_support_schema(conn)
        row = conn.execute(
            f"SELECT * FROM {table} WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (row_id, tenant_id),
        ).fetchone()
    return mapper(dict(row)) if row else None


def flatten_metadata(metadata: dict[str, Any], *, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for key, value in metadata.items():
        field_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            rows.extend(flatten_metadata(value, prefix=field_key))
        elif isinstance(value, list):
            for item in value:
                if is_scalar(item):
                    rows.append((field_key, item))
        elif is_scalar(value):
            rows.append((field_key, value))
    return rows


def is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def infer_value_type(value: Any) -> str:
    if isinstance(value, bool):
        return VALUE_TYPE_BOOLEAN
    if isinstance(value, int | float) and not isinstance(value, bool):
        return VALUE_TYPE_NUMBER
    text = str(value or "").strip()
    if looks_like_datetime(text):
        return VALUE_TYPE_DATETIME
    return VALUE_TYPE_STRING


def looks_like_datetime(value: str) -> bool:
    if len(value) < 10:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def value_column(value_type: str) -> str:
    return {
        VALUE_TYPE_STRING: "e.value_text",
        VALUE_TYPE_NUMBER: "e.value_number",
        VALUE_TYPE_DATETIME: "e.value_datetime",
        VALUE_TYPE_BOOLEAN: "e.value_boolean",
    }[value_type]


def normalize_index_value(value_type: str, value: Any) -> Any:
    if value_type == VALUE_TYPE_NUMBER:
        return float(value)
    if value_type == VALUE_TYPE_BOOLEAN:
        return 1 if bool(value) else 0
    if value_type == VALUE_TYPE_DATETIME:
        return str(value)
    return "" if value is None else str(value)


def row_to_resource_type(row: dict[str, Any]) -> MetadataResourceType:
    return MetadataResourceType(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        code=str(row.get("code") or ""),
        name=str(row.get("name") or ""),
        owner_context=str(row.get("owner_context") or ""),
        description=str(row.get("description") or ""),
        status=str(row.get("status") or STATUS_ACTIVE),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_field_definition(row: dict[str, Any]) -> MetadataFieldDefinition:
    return MetadataFieldDefinition(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        resource_type_code=str(row.get("resource_type_code") or ""),
        field_key=str(row.get("field_key") or ""),
        display_name=str(row.get("display_name") or ""),
        value_type=str(row.get("value_type") or VALUE_TYPE_STRING),
        required=bool(row.get("required")),
        searchable=bool(row.get("searchable")),
        sort_order=int(row.get("sort_order") or 0),
        status=str(row.get("status") or STATUS_ACTIVE),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_tag_group(row: dict[str, Any]) -> MetadataTagGroup:
    return MetadataTagGroup(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        code=str(row.get("code") or ""),
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        sort_order=int(row.get("sort_order") or 0),
        status=str(row.get("status") or STATUS_ACTIVE),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_tag(row: dict[str, Any]) -> MetadataTag:
    return MetadataTag(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        group_id=int(row["group_id"]) if row.get("group_id") is not None else None,
        code=str(row.get("code") or ""),
        name=str(row.get("name") or ""),
        color=str(row.get("color") or ""),
        description=str(row.get("description") or ""),
        sort_order=int(row.get("sort_order") or 0),
        status=str(row.get("status") or STATUS_ACTIVE),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_resource_metadata(row: dict[str, Any]) -> ResourceMetadata:
    return ResourceMetadata(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        resource_type_code=str(row.get("resource_type_code") or ""),
        resource_id=str(row.get("resource_id") or ""),
        metadata=decode_json(row.get("metadata_json")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def count_row(row: Any) -> int:
    return int(row["total"] if row else 0)


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


def raise_unique_constraint_error(exc: Exception) -> None:
    message = str(exc).lower()
    if "unique" in message or "duplicate" in message:
        raise MetadataSupportValidationError("metadata support code already exists") from exc
    raise exc


def encode_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def decode_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
