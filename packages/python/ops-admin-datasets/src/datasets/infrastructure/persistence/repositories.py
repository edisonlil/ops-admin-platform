from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from datasets.domain.exceptions import DatasetDomainError
from datasets.domain.models import Dataset, DatasetField, DatasetVersion, STATUS_ACTIVE, VERSION_STATUS_PUBLISHED
from datasets.infrastructure.persistence.bootstrap import require_datasets_schema
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, append_data_scope_sql
from system.application.database import connect, resolve_database_url, resolve_db_path
from system.application.sorting import build_order_by, parse_sort_params


DATASET_RESOURCE = ResourceDescriptor(resource_key="dataset.definition")


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def is_mysql_target() -> bool:
    return str(database_target()).startswith(("mysql://", "mysql+pymysql://", "mysql+mysqlconnector://"))


def dataset_key_column(alias: str = "") -> str:
    column = "`key`" if is_mysql_target() else "key"
    return f"{alias}.{column}" if alias else column


def dataset_sort_columns() -> dict[str, str]:
    return {
        "id": "d.id",
        "key": dataset_key_column("d"),
        "name": "d.name",
        "dataset_type": "d.dataset_type",
        "status": "d.status",
        "create_time": "d.create_time",
        "update_time": "d.update_time",
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def list_datasets(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    keyword: str = "",
    status: str | None = None,
    dataset_type: str = "",
    sort_by: str | None = None,
    sort_dir: str | None = None,
    data_scope: DataAccessPredicate | None = None,
) -> tuple[list[Dataset], int]:
    offset = (page - 1) * page_size
    where = ["d.tenant_id = ?", "d.deleted = 0"]
    params: list[Any] = [tenant_id]
    append_data_scope(where, params, data_scope)
    if keyword.strip():
        where.append(f"({dataset_key_column('d')} LIKE ? OR d.name LIKE ? OR d.description LIKE ?)")
        text = f"%{keyword.strip()}%"
        params.extend([text, text, text])
    if status:
        where.append("d.status = ?")
        params.append(status)
    if dataset_type.strip():
        where.append("d.dataset_type = ?")
        params.append(dataset_type.strip())
    where_sql = " AND ".join(where)
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=dataset_sort_columns(),
        default="d.update_time DESC, d.id DESC",
        tie_breaker="d.id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_datasets_schema(conn)
        total_row = conn.execute(f"SELECT COUNT(*) AS total FROM datasets d WHERE {where_sql}", tuple(params)).fetchone()
        rows = conn.execute(
            f"""
            SELECT d.*,
                   COALESCE(field_counts.field_count, 0) AS field_count,
                   COALESCE(row_counts.row_count, 0) AS row_count
            FROM datasets d
            LEFT JOIN (
                SELECT tenant_id, dataset_id, COUNT(*) AS field_count
                FROM dataset_fields
                WHERE deleted = 0
                GROUP BY tenant_id, dataset_id
            ) field_counts ON field_counts.tenant_id = d.tenant_id AND field_counts.dataset_id = d.id
            LEFT JOIN (
                SELECT tenant_id, dataset_id, COUNT(*) AS row_count
                FROM dataset_rows
                WHERE deleted = 0
                GROUP BY tenant_id, dataset_id
            ) row_counts ON row_counts.tenant_id = d.tenant_id AND row_counts.dataset_id = d.id
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            tuple([*params, page_size, offset]),
        ).fetchall()
    return [row_to_dataset(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def get_dataset(*, tenant_id: int, dataset_id: int) -> Dataset | None:
    row = get_dataset_row(tenant_id=tenant_id, dataset_id=dataset_id)
    return row_to_dataset(row) if row else None


def get_dataset_row(*, tenant_id: int, dataset_id: int) -> dict[str, Any] | None:
    with connect(database_target(), readonly=True) as conn:
        require_datasets_schema(conn)
        row = conn.execute(
            """
            SELECT d.*,
                   COALESCE((SELECT COUNT(*) FROM dataset_fields f WHERE f.tenant_id = d.tenant_id AND f.dataset_id = d.id AND f.deleted = 0), 0) AS field_count,
                   COALESCE((SELECT COUNT(*) FROM dataset_rows r WHERE r.tenant_id = d.tenant_id AND r.dataset_id = d.id AND r.deleted = 0), 0) AS row_count
            FROM datasets d
            WHERE d.id = ? AND d.tenant_id = ? AND d.deleted = 0
            """,
            (dataset_id, tenant_id),
        ).fetchone()
    return dict(row) if row else None


def get_dataset_by_key(*, tenant_id: int, key: str) -> Dataset | None:
    with connect(database_target(), readonly=True) as conn:
        require_datasets_schema(conn)
        row = conn.execute(
            f"SELECT *, 0 AS field_count, 0 AS row_count FROM datasets WHERE tenant_id = ? AND {dataset_key_column()} = ? AND deleted = 0",
            (tenant_id, key),
        ).fetchone()
    return row_to_dataset(dict(row)) if row else None


def save_dataset(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> Dataset:
    timestamp = now_iso()
    dataset_id = int(payload.get("id") or 0)
    values = (
        str(payload.get("key") or "").strip(),
        str(payload.get("name") or "").strip(),
        str(payload.get("description") or "").strip(),
        str(payload.get("dataset_type") or "manual").strip() or "manual",
        str(payload.get("status") or "draft").strip() or "draft",
        str(payload.get("visibility") or "platform").strip() or "platform",
        encode_json(payload.get("query_config") if isinstance(payload.get("query_config"), dict) else {}),
        payload.get("published_version_id"),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_datasets_schema(conn)
        try:
            if dataset_id:
                conn.execute(
                    f"""
                    UPDATE datasets
                    SET {dataset_key_column()} = ?, name = ?, description = ?, dataset_type = ?, status = ?, visibility = ?,
                        query_config_json = ?, published_version_id = ?, editor = ?, editor_id = ?, update_time = ?,
                        lock_version = lock_version + 1
                    WHERE id = ? AND tenant_id = ? AND deleted = 0
                    """,
                    (*values, dataset_id, tenant_id),
                )
                saved_id = dataset_id
            else:
                cursor = conn.execute(
                    f"""
                    INSERT INTO datasets (
                        tenant_id, owner_user_id, owner_department_id, {dataset_key_column()}, name, description,
                        dataset_type, status, visibility, query_config_json, published_version_id,
                        creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        payload.get("owner_user_id"),
                        payload.get("owner_department_id"),
                        *values[:8],
                        actor,
                        actor_id,
                        actor,
                        actor_id,
                        timestamp,
                        timestamp,
                    ),
                )
                saved_id = inserted_id(conn, cursor, "datasets", timestamp, actor)
        except sqlite3.IntegrityError as exc:
            raise_unique_constraint_error(exc)
    item = get_dataset(tenant_id=tenant_id, dataset_id=saved_id)
    if item is None:
        raise RuntimeError("dataset save failed")
    return item


def delete_dataset(*, tenant_id: int, dataset_id: int, actor: str, actor_id: int | None) -> Dataset | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_datasets_schema(conn)
        existing = conn.execute(
            "SELECT *, 0 AS field_count, 0 AS row_count FROM datasets WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (dataset_id, tenant_id),
        ).fetchone()
        if not existing:
            return None
        for table_name in ("dataset_fields", "dataset_rows", "dataset_versions"):
            conn.execute(
                f"""
                UPDATE {table_name}
                SET deleted = 1, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE tenant_id = ? AND dataset_id = ? AND deleted = 0
                """,
                (actor, actor_id, timestamp, tenant_id, dataset_id),
            )
        conn.execute(
            """
            UPDATE datasets
            SET active_marker = NULL, deleted = 1, status = 'disabled', editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ?
            """,
            (actor, actor_id, timestamp, dataset_id, tenant_id),
        )
    return row_to_dataset(dict(existing))


def list_fields(*, tenant_id: int, dataset_id: int) -> list[DatasetField]:
    with connect(database_target(), readonly=True) as conn:
        require_datasets_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM dataset_fields
            WHERE tenant_id = ? AND dataset_id = ? AND deleted = 0
            ORDER BY sort_order ASC, id ASC
            """,
            (tenant_id, dataset_id),
        ).fetchall()
    return [row_to_field(dict(row)) for row in rows]


def replace_fields(*, tenant_id: int, dataset_id: int, fields: list[dict[str, Any]], actor: str, actor_id: int | None) -> list[DatasetField]:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_datasets_schema(conn)
        conn.execute(
            """
            UPDATE dataset_fields
            SET active_marker = NULL, deleted = 1, editor = ?, editor_id = ?, update_time = ?,
                lock_version = lock_version + 1
            WHERE tenant_id = ? AND dataset_id = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, tenant_id, dataset_id),
        )
        for index, item in enumerate(fields):
            conn.execute(
                """
                INSERT INTO dataset_fields (
                    tenant_id, dataset_id, field_key, label, data_type, semantic_type, unit, precision,
                    nullable, visible, sort_order, expression, config_json,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    dataset_id,
                    str(item.get("field_key") or "").strip(),
                    str(item.get("label") or "").strip(),
                    str(item.get("data_type") or "text").strip() or "text",
                    str(item.get("semantic_type") or "").strip(),
                    str(item.get("unit") or "").strip(),
                    item.get("precision"),
                    1 if bool(item.get("nullable", True)) else 0,
                    1 if bool(item.get("visible", True)) else 0,
                    int(item.get("sort_order") if item.get("sort_order") is not None else index),
                    str(item.get("expression") or "").strip(),
                    encode_json(item.get("config") if isinstance(item.get("config"), dict) else {}),
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
    return list_fields(tenant_id=tenant_id, dataset_id=dataset_id)


def replace_manual_rows(*, tenant_id: int, dataset_id: int, rows: list[dict[str, Any]], actor: str, actor_id: int | None) -> int:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_datasets_schema(conn)
        conn.execute(
            """
            UPDATE dataset_rows
            SET deleted = 1, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND dataset_id = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, tenant_id, dataset_id),
        )
        for index, row in enumerate(rows):
            row_key = str(row.get("row_key") or row.get("id") or "").strip()
            conn.execute(
                """
                INSERT INTO dataset_rows (
                    tenant_id, dataset_id, row_key, row_json, sort_order,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    dataset_id,
                    row_key,
                    encode_json(row),
                    index,
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
    return len(rows)


def list_manual_rows(*, tenant_id: int, dataset_id: int, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    offset = (page - 1) * page_size
    with connect(database_target(), readonly=True) as conn:
        require_datasets_schema(conn)
        total_row = conn.execute(
            "SELECT COUNT(*) AS total FROM dataset_rows WHERE tenant_id = ? AND dataset_id = ? AND deleted = 0",
            (tenant_id, dataset_id),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT row_json
            FROM dataset_rows
            WHERE tenant_id = ? AND dataset_id = ? AND deleted = 0
            ORDER BY sort_order ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            (tenant_id, dataset_id, page_size, offset),
        ).fetchall()
    return [decode_json_object(row["row_json"]) for row in rows], int(total_row["total"] if total_row else 0)


def publish_dataset(
    *,
    tenant_id: int,
    dataset_id: int,
    schema: dict[str, Any],
    query_config: dict[str, Any],
    sample_rows: list[dict[str, Any]],
    actor: str,
    actor_id: int | None,
) -> DatasetVersion:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_datasets_schema(conn)
        max_row = conn.execute(
            "SELECT MAX(version_no) AS version_no FROM dataset_versions WHERE tenant_id = ? AND dataset_id = ? AND deleted = 0",
            (tenant_id, dataset_id),
        ).fetchone()
        version_no = int(max_row["version_no"] or 0) + 1
        cursor = conn.execute(
            """
            INSERT INTO dataset_versions (
                tenant_id, dataset_id, version_no, status, schema_json, query_config_json, sample_rows_json,
                published_time, creator, creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                dataset_id,
                version_no,
                VERSION_STATUS_PUBLISHED,
                encode_json(schema),
                encode_json(query_config),
                encode_json(sample_rows),
                timestamp,
                actor,
                actor_id,
                actor,
                actor_id,
                timestamp,
                timestamp,
            ),
        )
        version_id = inserted_id(conn, cursor, "dataset_versions", timestamp, actor)
        conn.execute(
            """
            UPDATE datasets
            SET published_version_id = ?, status = ?, editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND id = ? AND deleted = 0
            """,
            (version_id, STATUS_ACTIVE, actor, actor_id, timestamp, tenant_id, dataset_id),
        )
    return get_version(tenant_id=tenant_id, version_id=version_id)


def get_version(*, tenant_id: int, version_id: int) -> DatasetVersion:
    with connect(database_target(), readonly=True) as conn:
        require_datasets_schema(conn)
        row = conn.execute(
            "SELECT * FROM dataset_versions WHERE tenant_id = ? AND id = ? AND deleted = 0",
            (tenant_id, version_id),
        ).fetchone()
    if not row:
        raise RuntimeError("dataset version save failed")
    return row_to_version(dict(row))


def append_data_scope(where: list[str], params: list[Any], data_scope: DataAccessPredicate | None) -> None:
    append_data_scope_sql(where, params, data_scope, DATASET_RESOURCE, alias="d")


def encode_json(value: Any) -> str:
    return json.dumps(sanitize_json_value(value), ensure_ascii=False, separators=(",", ":"))


def sanitize_json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json_value(item) for item in value]
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def decode_json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def decode_json_list(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def row_to_dataset(row: dict[str, Any]) -> Dataset:
    return Dataset(
        id=int(row.get("id") or 0),
        tenant_id=int(row.get("tenant_id") or 0),
        key=str(row.get("key") or ""),
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        dataset_type=str(row.get("dataset_type") or "manual"),
        status=str(row.get("status") or "draft"),
        visibility=str(row.get("visibility") or "platform"),
        query_config=decode_json_object(row.get("query_config_json")),
        owner_user_id=optional_int(row.get("owner_user_id")),
        owner_department_id=optional_int(row.get("owner_department_id")),
        published_version_id=optional_int(row.get("published_version_id")),
        field_count=int(row.get("field_count") or 0),
        row_count=int(row.get("row_count") or 0),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_field(row: dict[str, Any]) -> DatasetField:
    return DatasetField(
        id=int(row.get("id") or 0),
        tenant_id=int(row.get("tenant_id") or 0),
        dataset_id=int(row.get("dataset_id") or 0),
        field_key=str(row.get("field_key") or ""),
        label=str(row.get("label") or ""),
        data_type=str(row.get("data_type") or "text"),
        semantic_type=str(row.get("semantic_type") or ""),
        unit=str(row.get("unit") or ""),
        precision=optional_int(row.get("precision")),
        nullable=bool(row.get("nullable")),
        visible=bool(row.get("visible")),
        sort_order=int(row.get("sort_order") or 0),
        expression=str(row.get("expression") or ""),
        config=decode_json_object(row.get("config_json")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_version(row: dict[str, Any]) -> DatasetVersion:
    return DatasetVersion(
        id=int(row.get("id") or 0),
        tenant_id=int(row.get("tenant_id") or 0),
        dataset_id=int(row.get("dataset_id") or 0),
        version_no=int(row.get("version_no") or 0),
        status=str(row.get("status") or VERSION_STATUS_PUBLISHED),
        schema=decode_json_object(row.get("schema_json")),
        query_config=decode_json_object(row.get("query_config_json")),
        sample_rows=decode_json_list(row.get("sample_rows_json")),
        published_time=str(row.get("published_time") or "") or None,
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def inserted_id(conn: Any, cursor: Any, table_name: str, timestamp: str, actor: str) -> int:
    lastrowid = getattr(cursor, "lastrowid", None)
    if lastrowid:
        return int(lastrowid)
    row = conn.execute(
        f"SELECT id FROM {table_name} WHERE create_time = ? AND creator = ? ORDER BY id DESC LIMIT 1",
        (timestamp, actor),
    ).fetchone()
    if row:
        return int(row["id"])
    raise RuntimeError(f"{table_name} insert failed")


def raise_unique_constraint_error(exc: sqlite3.IntegrityError) -> None:
    message = str(exc).lower()
    if "unique" in message:
        raise DatasetDomainError("dataset key or field key already exists") from exc
    raise exc
