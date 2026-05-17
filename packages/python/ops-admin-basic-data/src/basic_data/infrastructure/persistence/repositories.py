from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from basic_data.domain.exceptions import BasicDataDomainError
from basic_data.domain.models import DictionaryItem, DictionaryType, Region, STATUS_ACTIVE, STATUS_DISABLED
from basic_data.infrastructure.persistence.bootstrap import require_basic_data_schema
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, append_data_scope_sql
from system.application.database import connect, resolve_database_url, resolve_db_path


DICTIONARY_RESOURCE = ResourceDescriptor(resource_key="basic-data.dictionary")
REGION_RESOURCE = ResourceDescriptor(resource_key="basic-data.region")


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
    data_scope: DataAccessPredicate | None = None,
) -> tuple[list[DictionaryType], int]:
    offset = (page - 1) * page_size
    where = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    append_data_scope(where, params, data_scope, DICTIONARY_RESOURCE)
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
                        owner_user_id, owner_department_id, creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        *values[:7],
                        payload.get("owner_user_id"),
                        payload.get("owner_department_id"),
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
    data_scope: DataAccessPredicate | None = None,
) -> tuple[list[DictionaryItem], int]:
    offset = (page - 1) * page_size
    where = ["i.tenant_id = ?", "i.type_id = ?", "i.deleted = 0"]
    params: list[Any] = [tenant_id, type_id]
    append_data_scope(where, params, data_scope, DICTIONARY_RESOURCE, alias="i")
    if keyword.strip():
        where.append("(i.code LIKE ? OR i.value LIKE ? OR i.description LIKE ?)")
        text = f"%{keyword.strip()}%"
        params.extend([text, text, text])
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
                    SET code = ?, value = ?, color = ?, description = ?,
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
                        tenant_id, type_id, code, value, color, description,
                        extra_json, status, sort_order, owner_user_id, owner_department_id, creator, creator_id, editor,
                        editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        type_id,
                        *values[:7],
                        payload.get("owner_user_id"),
                        payload.get("owner_department_id"),
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


def list_regions(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    keyword: str = "",
    status: str | None = None,
    level: str | None = None,
    parent_id: int | None = None,
    data_scope: DataAccessPredicate | None = None,
) -> tuple[list[Region], int]:
    offset = (page - 1) * page_size
    where = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    append_data_scope(where, params, data_scope, REGION_RESOURCE)
    if keyword.strip():
        where.append("(code LIKE ? OR name LIKE ? OR short_name LIKE ?)")
        text = f"%{keyword.strip()}%"
        params.extend([text, text, text])
    normalized_status = status_filter(status)
    if normalized_status:
        where.append("status = ?")
        params.append(normalized_status)
    if level:
        where.append("level = ?")
        params.append(level)
    if parent_id is not None:
        if parent_id:
            where.append("parent_id = ?")
            params.append(parent_id)
        else:
            where.append("parent_id IS NULL")
    where_sql = " AND ".join(where)
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        total_row = conn.execute(f"SELECT COUNT(*) AS total FROM business_regions WHERE {where_sql}", tuple(params)).fetchone()
        rows = conn.execute(
            f"""
            SELECT *
            FROM business_regions
            WHERE {where_sql}
            ORDER BY sort_order ASC, code ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, page_size, offset]),
        ).fetchall()
    return [row_to_region(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def list_all_regions(*, tenant_id: int, include_disabled: bool = True) -> list[Region]:
    where = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if not include_disabled:
        where.append("status = ?")
        params.append(STATUS_ACTIVE)
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM business_regions
            WHERE {" AND ".join(where)}
            ORDER BY sort_order ASC, code ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
    return [row_to_region(dict(row)) for row in rows]


def get_region(*, tenant_id: int, region_id: int) -> Region | None:
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        row = conn.execute(
            "SELECT * FROM business_regions WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (region_id, tenant_id),
        ).fetchone()
    return row_to_region(dict(row)) if row else None


def get_region_by_code(*, tenant_id: int, code: str) -> Region | None:
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        row = conn.execute(
            "SELECT * FROM business_regions WHERE code = ? AND tenant_id = ? AND deleted = 0",
            (code, tenant_id),
        ).fetchone()
    return row_to_region(dict(row)) if row else None


def save_region(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> Region:
    timestamp = now_iso()
    region_id = int(payload.get("id") or 0)
    parent_id = int(payload.get("parent_id") or 0) or None
    code = str(payload.get("code") or "").strip()
    with connect(database_target(), readonly=False) as conn:
        require_basic_data_schema(conn)
        parent = None
        if parent_id:
            parent_row = conn.execute(
                "SELECT * FROM business_regions WHERE id = ? AND tenant_id = ? AND deleted = 0",
                (parent_id, tenant_id),
            ).fetchone()
            parent = row_to_region(dict(parent_row)) if parent_row else None
        parent_code = parent.code if parent else ""
        path = build_region_path(parent.path if parent else "", code)
        values = (
            parent_id,
            parent_code,
            code,
            str(payload.get("name") or "").strip(),
            str(payload.get("short_name") or "").strip(),
            str(payload.get("level") or "").strip(),
            path,
            normalize_status(payload.get("status")),
            int(payload.get("sort_order") or 0),
            encode_json(payload.get("extra") if isinstance(payload.get("extra"), dict) else {}),
            actor,
            actor_id,
            timestamp,
        )
        try:
            if region_id:
                conn.execute(
                    """
                    UPDATE business_regions
                    SET parent_id = ?, parent_code = ?, code = ?, name = ?, short_name = ?, level = ?,
                        path = ?, status = ?, sort_order = ?, extra_json = ?, editor = ?, editor_id = ?,
                        update_time = ?, lock_version = lock_version + 1
                    WHERE id = ? AND tenant_id = ? AND deleted = 0
                    """,
                    (*values, region_id, tenant_id),
                )
                saved_id = region_id
                refresh_region_descendant_paths(conn, tenant_id=tenant_id, parent_id=saved_id, parent_path=path, actor=actor, actor_id=actor_id, timestamp=timestamp)
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO business_regions (
                        tenant_id, parent_id, parent_code, code, name, short_name, level, path, status,
                        sort_order, extra_json, creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, *values[:10], actor, actor_id, actor, actor_id, timestamp, timestamp),
                )
                saved_id = inserted_id(conn, cursor, "business_regions", timestamp, actor)
        except sqlite3.IntegrityError as exc:
            raise_unique_constraint_error(exc)
    item = get_region(tenant_id=tenant_id, region_id=saved_id)
    if item is None:
        raise RuntimeError("region save failed")
    return item


def delete_region(*, tenant_id: int, region_id: int, actor: str, actor_id: int | None) -> Region | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_basic_data_schema(conn)
        existing = conn.execute(
            "SELECT * FROM business_regions WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (region_id, tenant_id),
        ).fetchone()
        if not existing:
            return None
        region_ids = collect_region_descendant_ids(conn, tenant_id=tenant_id, root_region_id=region_id)
        placeholders = ", ".join("?" for _ in region_ids)
        conn.execute(
            f"""
            UPDATE business_regions
            SET code = {deleted_code_expression(conn)}, deleted = 1, status = ?, editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE id IN ({placeholders}) AND tenant_id = ?
            """,
            (STATUS_DISABLED, actor, actor_id, timestamp, *region_ids, tenant_id),
        )
    return row_to_region(dict(existing))


def list_region_children(*, tenant_id: int, parent_id: int | None, active_only: bool = True) -> list[Region]:
    where = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if parent_id:
        where.append("parent_id = ?")
        params.append(parent_id)
    else:
        where.append("parent_id IS NULL")
    if active_only:
        where.append("status = ?")
        params.append(STATUS_ACTIVE)
    with connect(database_target(), readonly=True) as conn:
        require_basic_data_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM business_regions
            WHERE {" AND ".join(where)}
            ORDER BY sort_order ASC, code ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
    return [row_to_region(dict(row)) for row in rows]


def collect_region_descendant_ids(conn: Any, *, tenant_id: int, root_region_id: int) -> list[int]:
    pending = [root_region_id]
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
            FROM business_regions
            WHERE tenant_id = ? AND parent_id = ? AND deleted = 0
            """,
            (tenant_id, current_id),
        ).fetchall()
        pending.extend(int(row["id"]) for row in rows)
    return collected


def refresh_region_descendant_paths(
    conn: Any,
    *,
    tenant_id: int,
    parent_id: int,
    parent_path: str,
    actor: str,
    actor_id: int | None,
    timestamp: str,
) -> None:
    rows = conn.execute(
        """
        SELECT *
        FROM business_regions
        WHERE tenant_id = ? AND parent_id = ? AND deleted = 0
        ORDER BY sort_order ASC, code ASC, id ASC
        """,
        (tenant_id, parent_id),
    ).fetchall()
    for row in rows:
        child = row_to_region(dict(row))
        child_path = build_region_path(parent_path, child.code)
        conn.execute(
            """
            UPDATE business_regions
            SET parent_code = ?, path = ?, editor = ?, editor_id = ?, update_time = ?,
                lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (parent_path.strip("/").split("/")[-1] if parent_path.strip("/") else "", child_path, actor, actor_id, timestamp, child.id, tenant_id),
        )
        refresh_region_descendant_paths(
            conn,
            tenant_id=tenant_id,
            parent_id=child.id,
            parent_path=child_path,
            actor=actor,
            actor_id=actor_id,
            timestamp=timestamp,
        )


def build_region_path(parent_path: str, code: str) -> str:
    normalized_parent = f"/{parent_path.strip('/')}/" if parent_path.strip("/") else "/"
    return f"{normalized_parent}{code.strip()}/"


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
        color=str(row.get("color") or ""),
        description=str(row.get("description") or ""),
        extra=decode_json(row.get("extra_json")),
        status=str(row.get("status") or STATUS_ACTIVE),
        sort_order=int(row.get("sort_order") or 0),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_region(row: dict[str, Any]) -> Region:
    return Region(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        parent_id=int(row["parent_id"]) if row.get("parent_id") not in (None, "") else None,
        parent_code=str(row.get("parent_code") or ""),
        code=str(row.get("code") or ""),
        name=str(row.get("name") or ""),
        short_name=str(row.get("short_name") or ""),
        level=str(row.get("level") or ""),
        path=str(row.get("path") or ""),
        status=str(row.get("status") or STATUS_ACTIVE),
        sort_order=int(row.get("sort_order") or 0),
        extra=decode_json(row.get("extra_json")),
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
    if getattr(conn, "backend", "sqlite") == "mysql":
        return "CONCAT('__deleted__', id)"
    return "'__deleted__' || id"


def append_data_scope(
    where: list[str],
    params: list[Any],
    data_scope: DataAccessPredicate | None,
    descriptor: ResourceDescriptor,
    *,
    alias: str = "",
) -> None:
    append_data_scope_sql(where, params, data_scope, descriptor, alias=alias)


def raise_unique_constraint_error(exc: Exception) -> None:
    message = str(exc).lower()
    if "business_dictionary_types" in message and ("unique" in message or "duplicate" in message):
        raise BasicDataDomainError("dictionary type code already exists") from exc
    if "business_dictionary_items" in message and ("unique" in message or "duplicate" in message):
        raise BasicDataDomainError("dictionary item code already exists") from exc
    if "business_regions" in message and ("unique" in message or "duplicate" in message):
        raise BasicDataDomainError("region code already exists") from exc
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
