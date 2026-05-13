from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from basic_data.domain.exceptions import BasicDataDomainError
from basic_data.domain.models import DictionaryItem, DictionaryType, STATUS_ACTIVE, STATUS_DISABLED
from basic_data.infrastructure.persistence.bootstrap import require_basic_data_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def list_dictionary_types(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    keyword: str = "",
    status: str | None = None,
    category: str = "",
) -> tuple[list[DictionaryType], int]:
    offset = (page - 1) * page_size
    where = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if keyword.strip():
        where.append("(code LIKE ? OR name LIKE ? OR description LIKE ?)")
        text = f"%{keyword.strip()}%"
        params.extend([text, text, text])
    normalized_status = status_filter(status)
    if normalized_status:
        where.append("status = ?")
        params.append(normalized_status)
    if category.strip():
        where.append("category = ?")
        params.append(category.strip())
    where_sql = " AND ".join(where)
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        total_row = conn.execute(f"SELECT COUNT(*) AS total FROM business_dictionary_types WHERE {where_sql}", tuple(params)).fetchone()
        rows = conn.execute(
            f"""
            SELECT *
            FROM business_dictionary_types
            WHERE {where_sql}
            ORDER BY sort_order ASC, id DESC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, page_size, offset]),
        ).fetchall()
    return [row_to_dictionary_type(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def get_dictionary_type(*, tenant_id: int, type_id: int) -> DictionaryType | None:
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        row = conn.execute(
            "SELECT * FROM business_dictionary_types WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (type_id, tenant_id),
        ).fetchone()
    return row_to_dictionary_type(dict(row)) if row else None


def get_dictionary_type_by_code(*, tenant_id: int, code: str) -> DictionaryType | None:
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        row = conn.execute(
            "SELECT * FROM business_dictionary_types WHERE code = ? AND tenant_id = ? AND deleted = 0",
            (code, tenant_id),
        ).fetchone()
    return row_to_dictionary_type(dict(row)) if row else None


def save_dictionary_type(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> DictionaryType:
    timestamp = now_iso()
    type_id = int(payload.get("id") or 0)
    values = (
        int(payload.get("parent_id") or 0) or None,
        str(payload.get("code") or "").strip(),
        str(payload.get("name") or "").strip(),
        str(payload.get("category") or "general").strip() or "general",
        str(payload.get("description") or "").strip(),
        normalize_status(payload.get("status")),
        int(payload.get("sort_order") or 0),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_basic_data_schema(conn)
        try:
            if type_id:
                conn.execute(
                    """
                    UPDATE business_dictionary_types
                    SET parent_id = ?, code = ?, name = ?, category = ?, description = ?, status = ?,
                        sort_order = ?, editor = ?, editor_id = ?, update_time = ?,
                        lock_version = lock_version + 1
                    WHERE id = ? AND tenant_id = ? AND deleted = 0
                    """,
                    (*values, type_id, tenant_id),
                )
                saved_id = type_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO business_dictionary_types (
                        tenant_id, parent_id, code, name, category, description, status, sort_order,
                        creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        *values[:7],
                        actor,
                        actor_id,
                        actor,
                        actor_id,
                        timestamp,
                        timestamp,
                    ),
                )
                saved_id = inserted_id(conn, cursor, "business_dictionary_types", timestamp, actor)
        except sqlite3.IntegrityError as exc:
            raise_unique_constraint_error(exc)
    item = get_dictionary_type(tenant_id=tenant_id, type_id=saved_id)
    if item is None:
        raise RuntimeError("dictionary type save failed")
    return item


def delete_dictionary_type(*, tenant_id: int, type_id: int, actor: str, actor_id: int | None) -> DictionaryType | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_basic_data_schema(conn)
        existing = conn.execute(
            "SELECT * FROM business_dictionary_types WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (type_id, tenant_id),
        ).fetchone()
        if not existing:
            return None
        type_ids = collect_dictionary_type_descendant_ids(conn, tenant_id=tenant_id, root_type_id=type_id)
        placeholders = ", ".join("?" for _ in type_ids)
        conn.execute(
            f"""
            UPDATE business_dictionary_items
            SET code = {deleted_code_expression(conn)}, deleted = 1, status = ?, editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND type_id IN ({placeholders}) AND deleted = 0
            """,
            (STATUS_DISABLED, actor, actor_id, timestamp, tenant_id, *type_ids),
        )
        conn.execute(
            f"""
            UPDATE business_dictionary_types
            SET code = {deleted_code_expression(conn)}, deleted = 1, status = ?, editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE id IN ({placeholders}) AND tenant_id = ?
            """,
            (STATUS_DISABLED, actor, actor_id, timestamp, *type_ids, tenant_id),
        )
    return row_to_dictionary_type(dict(existing))


def collect_dictionary_type_descendant_ids(conn: Any, *, tenant_id: int, root_type_id: int) -> list[int]:
    pending = [root_type_id]
    collected: list[int] = []
    seen: set[int] = set()
    while pending:
        current_id = pending.pop(0)
        if current_id in seen:
            continue
        seen.add(current_id)
        collected.append(current_id)
        rows = conn.execute(
            """
            SELECT id
            FROM business_dictionary_types
            WHERE tenant_id = ? AND parent_id = ? AND deleted = 0
            """,
            (tenant_id, current_id),
        ).fetchall()
        pending.extend(int(row["id"]) for row in rows)
    return collected


def list_dictionary_items(
    *,
    tenant_id: int,
    type_id: int,
    page: int,
    page_size: int,
    keyword: str = "",
    status: str | None = None,
) -> tuple[list[DictionaryItem], int]:
    offset = (page - 1) * page_size
    where = ["i.tenant_id = ?", "i.type_id = ?", "i.deleted = 0"]
    params: list[Any] = [tenant_id, type_id]
    if keyword.strip():
        where.append("(i.code LIKE ? OR i.value LIKE ? OR i.label LIKE ? OR i.description LIKE ?)")
        text = f"%{keyword.strip()}%"
        params.extend([text, text, text, text])
    normalized_status = status_filter(status)
    if normalized_status:
        where.append("i.status = ?")
        params.append(normalized_status)
    where_sql = " AND ".join(where)
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        total_row = conn.execute(
            f"SELECT COUNT(*) AS total FROM business_dictionary_items i WHERE {where_sql}",
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            f"""
            SELECT i.*, t.code AS type_code
            FROM business_dictionary_items i
            JOIN business_dictionary_types t ON t.id = i.type_id AND t.tenant_id = i.tenant_id
            WHERE {where_sql}
            ORDER BY i.sort_order ASC, i.id ASC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, page_size, offset]),
        ).fetchall()
    return [row_to_dictionary_item(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def get_dictionary_item(*, tenant_id: int, item_id: int) -> DictionaryItem | None:
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        row = conn.execute(
            """
            SELECT i.*, t.code AS type_code
            FROM business_dictionary_items i
            JOIN business_dictionary_types t ON t.id = i.type_id AND t.tenant_id = i.tenant_id
            WHERE i.id = ? AND i.tenant_id = ? AND i.deleted = 0
            """,
            (item_id, tenant_id),
        ).fetchone()
    return row_to_dictionary_item(dict(row)) if row else None


def save_dictionary_item(
    *,
    tenant_id: int,
    type_id: int,
    payload: dict[str, Any],
    actor: str,
    actor_id: int | None,
) -> DictionaryItem:
    timestamp = now_iso()
    item_id = int(payload.get("id") or 0)
    values = (
        str(payload.get("code") or "").strip(),
        str(payload.get("value") or "").strip(),
        str(payload.get("label") or "").strip(),
        str(payload.get("color") or "").strip(),
        str(payload.get("description") or "").strip(),
        encode_json(payload.get("extra") if isinstance(payload.get("extra"), dict) else {}),
        normalize_status(payload.get("status")),
        int(payload.get("sort_order") or 0),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_basic_data_schema(conn)
        try:
            if item_id:
                conn.execute(
                    """
                    UPDATE business_dictionary_items
                    SET code = ?, value = ?, label = ?, color = ?, description = ?,
                        extra_json = ?, status = ?, sort_order = ?, editor = ?,
                        editor_id = ?, update_time = ?, lock_version = lock_version + 1
                    WHERE id = ? AND tenant_id = ? AND deleted = 0
                    """,
                    (*values, item_id, tenant_id),
                )
                saved_id = item_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO business_dictionary_items (
                        tenant_id, type_id, code, value, label, color, description,
                        extra_json, status, sort_order, creator, creator_id, editor,
                        editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        type_id,
                        *values[:8],
                        actor,
                        actor_id,
                        actor,
                        actor_id,
                        timestamp,
                        timestamp,
                    ),
                )
                saved_id = inserted_id(conn, cursor, "business_dictionary_items", timestamp, actor)
        except sqlite3.IntegrityError as exc:
            raise_unique_constraint_error(exc)
    item = get_dictionary_item(tenant_id=tenant_id, item_id=saved_id)
    if item is None:
        raise RuntimeError("dictionary item save failed")
    return item


def delete_dictionary_item(*, tenant_id: int, item_id: int, actor: str, actor_id: int | None) -> DictionaryItem | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_basic_data_schema(conn)
        existing = conn.execute(
            """
            SELECT i.*, t.code AS type_code
            FROM business_dictionary_items i
            JOIN business_dictionary_types t ON t.id = i.type_id AND t.tenant_id = i.tenant_id
            WHERE i.id = ? AND i.tenant_id = ? AND i.deleted = 0
            """,
            (item_id, tenant_id),
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE business_dictionary_items
            SET code = ?, deleted = 1, status = ?, editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ?
            """,
            (f"__deleted__{item_id}", STATUS_DISABLED, actor, actor_id, timestamp, item_id, tenant_id),
        )
    return row_to_dictionary_item(dict(existing))


def list_items_by_type_code(*, tenant_id: int, type_code: str, active_only: bool = True) -> list[DictionaryItem]:
    where = ["i.tenant_id = ?", "t.code = ?", "i.deleted = 0", "t.deleted = 0"]
    params: list[Any] = [tenant_id, type_code]
    if active_only:
        where.extend(["i.status = ?", "t.status = ?"])
        params.extend([STATUS_ACTIVE, STATUS_ACTIVE])
    where_sql = " AND ".join(where)
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        rows = conn.execute(
            f"""
            SELECT i.*, t.code AS type_code
            FROM business_dictionary_items i
            JOIN business_dictionary_types t ON t.id = i.type_id AND t.tenant_id = i.tenant_id
            WHERE {where_sql}
            ORDER BY i.sort_order ASC, i.id ASC
            """,
            tuple(params),
        ).fetchall()
    return [row_to_dictionary_item(dict(row)) for row in rows]


def row_to_dictionary_type(row: dict[str, Any]) -> DictionaryType:
    return DictionaryType(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        parent_id=int(row["parent_id"]) if row.get("parent_id") not in (None, "") else None,
        code=str(row.get("code") or ""),
        name=str(row.get("name") or ""),
        category=str(row.get("category") or "general"),
        description=str(row.get("description") or ""),
        status=str(row.get("status") or STATUS_ACTIVE),
        sort_order=int(row.get("sort_order") or 0),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_dictionary_item(row: dict[str, Any]) -> DictionaryItem:
    return DictionaryItem(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        type_id=int(row["type_id"]),
        type_code=str(row.get("type_code") or ""),
        code=str(row.get("code") or ""),
        value=str(row.get("value") or ""),
        label=str(row.get("label") or ""),
        color=str(row.get("color") or ""),
        description=str(row.get("description") or ""),
        extra=decode_json(row.get("extra_json")),
        status=str(row.get("status") or STATUS_ACTIVE),
        sort_order=int(row.get("sort_order") or 0),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def normalize_status(value: Any) -> str:
    status = str(value or STATUS_ACTIVE).strip() or STATUS_ACTIVE
    return status if status in {STATUS_ACTIVE, STATUS_DISABLED} else STATUS_ACTIVE


def status_filter(value: Any) -> str | None:
    status = str(value or "").strip()
    return status if status in {STATUS_ACTIVE, STATUS_DISABLED} else None


def deleted_code_expression(conn: Any) -> str:
    if getattr(conn, "backend", "sqlite") == "postgres":
        return "'__deleted__' || id::text"
    return "'__deleted__' || id"


def raise_unique_constraint_error(exc: Exception) -> None:
    message = str(exc).lower()
    if "business_dictionary_types" in message and ("unique" in message or "duplicate" in message):
        raise BasicDataDomainError("dictionary type code already exists") from exc
    if "business_dictionary_items" in message and ("unique" in message or "duplicate" in message):
        raise BasicDataDomainError("dictionary item code already exists") from exc
    raise exc


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
