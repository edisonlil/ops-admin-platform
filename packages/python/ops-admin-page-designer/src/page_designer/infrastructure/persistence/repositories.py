from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from page_designer.domain.exceptions import PageDesignerDomainError
from page_designer.domain.models import (
    DEFAULT_SCHEMA_VERSION,
    STATUS_DISABLED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    PageDefinition,
    PageVersion,
    default_dashboard_layout,
)
from page_designer.infrastructure.persistence.bootstrap import require_page_designer_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def list_pages(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    keyword: str = "",
    page_type: str | None = None,
    status: str | None = None,
) -> tuple[list[PageDefinition], int]:
    offset = (page - 1) * page_size
    where = ["p.tenant_id = ?", "p.deleted = 0"]
    params: list[Any] = [tenant_id]
    if keyword.strip():
        where.append("(p.page_key LIKE ? OR p.name LIKE ? OR p.description LIKE ?)")
        text = f"%{keyword.strip()}%"
        params.extend([text, text, text])
    if page_type:
        where.append("p.page_type = ?")
        params.append(page_type)
    if status:
        where.append("p.status = ?")
        params.append(status)
    where_sql = " AND ".join(where)
    with connect(database_target(), readonly=True) as conn:
        require_page_designer_schema(conn)
        total_row = conn.execute(f"SELECT COUNT(*) AS total FROM page_definitions p WHERE {where_sql}", tuple(params)).fetchone()
        rows = conn.execute(
            f"""
            SELECT p.*, m.menu_key AS mounted_menu_key
            FROM page_definitions p
            LEFT JOIN page_menu_mounts m ON m.page_id = p.id AND m.tenant_id = p.tenant_id AND m.deleted = 0 AND m.is_enabled = 1
            WHERE {where_sql}
            ORDER BY p.update_time DESC, p.id DESC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, page_size, offset]),
        ).fetchall()
    return [row_to_page(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def get_page(*, tenant_id: int, page_id: int) -> PageDefinition | None:
    with connect(database_target(), readonly=True) as conn:
        require_page_designer_schema(conn)
        row = conn.execute(
            """
            SELECT p.*, m.menu_key AS mounted_menu_key
            FROM page_definitions p
            LEFT JOIN page_menu_mounts m ON m.page_id = p.id AND m.tenant_id = p.tenant_id AND m.deleted = 0 AND m.is_enabled = 1
            WHERE p.id = ? AND p.tenant_id = ? AND p.deleted = 0
            """,
            (page_id, tenant_id),
        ).fetchone()
    return row_to_page(dict(row)) if row else None


def get_page_by_key(*, tenant_id: int, page_key: str) -> PageDefinition | None:
    with connect(database_target(), readonly=True) as conn:
        require_page_designer_schema(conn)
        row = conn.execute(
            """
            SELECT p.*, m.menu_key AS mounted_menu_key
            FROM page_definitions p
            LEFT JOIN page_menu_mounts m ON m.page_id = p.id AND m.tenant_id = p.tenant_id AND m.deleted = 0 AND m.is_enabled = 1
            WHERE p.page_key = ? AND p.tenant_id = ? AND p.deleted = 0
            """,
            (page_key, tenant_id),
        ).fetchone()
    return row_to_page(dict(row)) if row else None


def create_page(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> PageDefinition:
    timestamp = now_iso()
    page = PageDefinition(
        id=0,
        tenant_id=tenant_id,
        page_key=str(payload.get("page_key") or "").strip(),
        name=str(payload.get("name") or "").strip(),
        description=str(payload.get("description") or "").strip(),
        page_type=str(payload.get("page_type") or "dashboard").strip(),
        status=STATUS_DRAFT,
        settings=payload.get("settings") if isinstance(payload.get("settings"), dict) else {},
    )
    page.validate()
    with connect(database_target(), readonly=False) as conn:
        require_page_designer_schema(conn)
        try:
            cursor = conn.execute(
                """
                INSERT INTO page_definitions (
                    tenant_id, page_key, name, description, page_type, status, settings_json,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    page.page_key,
                    page.name,
                    page.description,
                    page.page_type,
                    STATUS_DRAFT,
                    encode_json(page.settings),
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
            page_id = inserted_id(conn, cursor, "page_definitions", timestamp, actor)
            conn.execute(
                """
                INSERT INTO page_versions (
                    tenant_id, page_id, version_no, schema_version, layout_json, components_json,
                    data_bindings_json, interactions_json, status, creator, creator_id, editor,
                    editor_id, create_time, update_time
                )
                VALUES (?, ?, 1, ?, ?, '[]', '{}', '{}', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    page_id,
                    DEFAULT_SCHEMA_VERSION,
                    encode_json(default_dashboard_layout()),
                    STATUS_DRAFT,
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise_unique_error(exc)
    saved = get_page(tenant_id=tenant_id, page_id=page_id)
    if not saved:
        raise RuntimeError("page save failed")
    return saved


def update_page(*, tenant_id: int, page_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> PageDefinition:
    existing = get_page(tenant_id=tenant_id, page_id=page_id)
    if not existing:
        return None  # type: ignore[return-value]
    updated = PageDefinition(
        id=existing.id,
        tenant_id=tenant_id,
        page_key=str(payload.get("page_key") or existing.page_key).strip(),
        name=str(payload.get("name") or existing.name).strip(),
        description=str(payload.get("description") if payload.get("description") is not None else existing.description).strip(),
        page_type=existing.page_type,
        status=existing.status,
        current_version_id=existing.current_version_id,
        thumbnail_file_id=int(payload.get("thumbnail_file_id") or 0) or existing.thumbnail_file_id,
        settings=payload.get("settings") if isinstance(payload.get("settings"), dict) else existing.settings,
    )
    updated.validate()
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_page_designer_schema(conn)
        try:
            conn.execute(
                """
                UPDATE page_definitions
                SET page_key = ?, name = ?, description = ?, thumbnail_file_id = ?, settings_json = ?,
                    editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (
                    updated.page_key,
                    updated.name,
                    updated.description,
                    updated.thumbnail_file_id,
                    encode_json(updated.settings),
                    actor,
                    actor_id,
                    timestamp,
                    page_id,
                    tenant_id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise_unique_error(exc)
    saved = get_page(tenant_id=tenant_id, page_id=page_id)
    if not saved:
        raise RuntimeError("page update failed")
    return saved


def delete_page(*, tenant_id: int, page_id: int, actor: str, actor_id: int | None) -> PageDefinition | None:
    existing = get_page(tenant_id=tenant_id, page_id=page_id)
    if not existing:
        return None
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_page_designer_schema(conn)
        conn.execute(
            f"""
            UPDATE page_menu_mounts
            SET menu_key = {deleted_text_expression(conn, 'menu_key', 'id')}, deleted = 1, is_enabled = 0,
                editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND page_id = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, tenant_id, page_id),
        )
        conn.execute(
            """
            UPDATE page_versions
            SET deleted = 1, status = ?, editor = ?, editor_id = ?, update_time = ?,
                lock_version = lock_version + 1
            WHERE tenant_id = ? AND page_id = ? AND deleted = 0
            """,
            (STATUS_DISABLED, actor, actor_id, timestamp, tenant_id, page_id),
        )
        conn.execute(
            f"""
            UPDATE page_definitions
            SET page_key = {deleted_text_expression(conn, 'page_key', 'id')}, deleted = 1, status = ?,
                editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND id = ? AND deleted = 0
            """,
            (STATUS_DISABLED, actor, actor_id, timestamp, tenant_id, page_id),
        )
    return existing


def save_draft_version(*, tenant_id: int, page_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> PageVersion:
    existing = get_page(tenant_id=tenant_id, page_id=page_id)
    if not existing:
        return None  # type: ignore[return-value]
    latest = latest_version(tenant_id=tenant_id, page_id=page_id, status=STATUS_DRAFT)
    version_no = latest.version_no if latest else next_version_no(tenant_id=tenant_id, page_id=page_id)
    version_id = latest.id if latest else 0
    version = PageVersion(
        id=version_id,
        tenant_id=tenant_id,
        page_id=page_id,
        version_no=version_no,
        schema_version=str(payload.get("schema_version") or DEFAULT_SCHEMA_VERSION),
        layout=payload.get("layout") if isinstance(payload.get("layout"), dict) else default_dashboard_layout(),
        components=payload.get("components") if isinstance(payload.get("components"), list) else [],
        data_bindings=payload.get("data_bindings") if isinstance(payload.get("data_bindings"), dict) else {},
        interactions=payload.get("interactions") if isinstance(payload.get("interactions"), dict) else {},
        status=STATUS_DRAFT,
    )
    version.validate(existing.page_type)
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_page_designer_schema(conn)
        if version_id:
            conn.execute(
                """
                UPDATE page_versions
                SET schema_version = ?, layout_json = ?, components_json = ?, data_bindings_json = ?,
                    interactions_json = ?, editor = ?, editor_id = ?, update_time = ?,
                    lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (
                    version.schema_version,
                    encode_json(version.layout),
                    encode_json(version.components),
                    encode_json(version.data_bindings),
                    encode_json(version.interactions),
                    actor,
                    actor_id,
                    timestamp,
                    version_id,
                    tenant_id,
                ),
            )
            saved_id = version_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO page_versions (
                    tenant_id, page_id, version_no, schema_version, layout_json, components_json,
                    data_bindings_json, interactions_json, status, creator, creator_id, editor,
                    editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    page_id,
                    version.version_no,
                    version.schema_version,
                    encode_json(version.layout),
                    encode_json(version.components),
                    encode_json(version.data_bindings),
                    encode_json(version.interactions),
                    STATUS_DRAFT,
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
            saved_id = inserted_id(conn, cursor, "page_versions", timestamp, actor)
    saved = get_version(tenant_id=tenant_id, version_id=saved_id)
    if not saved:
        raise RuntimeError("page version save failed")
    return saved


def get_version(*, tenant_id: int, version_id: int) -> PageVersion | None:
    with connect(database_target(), readonly=True) as conn:
        require_page_designer_schema(conn)
        row = conn.execute(
            "SELECT * FROM page_versions WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (version_id, tenant_id),
        ).fetchone()
    return row_to_version(dict(row)) if row else None


def latest_version(*, tenant_id: int, page_id: int, status: str | None = None) -> PageVersion | None:
    where = ["tenant_id = ?", "page_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id, page_id]
    if status:
        where.append("status = ?")
        params.append(status)
    with connect(database_target(), readonly=True) as conn:
        require_page_designer_schema(conn)
        row = conn.execute(
            f"""
            SELECT *
            FROM page_versions
            WHERE {" AND ".join(where)}
            ORDER BY version_no DESC, id DESC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
    return row_to_version(dict(row)) if row else None


def next_version_no(*, tenant_id: int, page_id: int) -> int:
    with connect(database_target(), readonly=True) as conn:
        require_page_designer_schema(conn)
        row = conn.execute(
            "SELECT MAX(version_no) AS max_version_no FROM page_versions WHERE tenant_id = ? AND page_id = ?",
            (tenant_id, page_id),
        ).fetchone()
    return int((row or {}).get("max_version_no") or 0) + 1


def publish_page(*, tenant_id: int, page_id: int, version_id: int, actor: str, actor_id: int | None) -> PageDefinition:
    version = get_version(tenant_id=tenant_id, version_id=version_id)
    if not version or version.page_id != page_id:
        return None  # type: ignore[return-value]
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_page_designer_schema(conn)
        conn.execute(
            """
            UPDATE page_versions
            SET status = ?, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND page_id = ? AND status = ? AND deleted = 0
            """,
            (STATUS_DISABLED, actor, actor_id, timestamp, tenant_id, page_id, STATUS_PUBLISHED),
        )
        conn.execute(
            """
            UPDATE page_versions
            SET status = ?, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND id = ? AND deleted = 0
            """,
            (STATUS_PUBLISHED, actor, actor_id, timestamp, tenant_id, version_id),
        )
        conn.execute(
            """
            UPDATE page_definitions
            SET status = ?, current_version_id = ?, editor = ?, editor_id = ?, update_time = ?,
                lock_version = lock_version + 1
            WHERE tenant_id = ? AND id = ? AND deleted = 0
            """,
            (STATUS_PUBLISHED, version_id, actor, actor_id, timestamp, tenant_id, page_id),
        )
    saved = get_page(tenant_id=tenant_id, page_id=page_id)
    if not saved:
        raise RuntimeError("page publish failed")
    return saved


def unpublish_page(*, tenant_id: int, page_id: int, actor: str, actor_id: int | None) -> PageDefinition:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_page_designer_schema(conn)
        conn.execute(
            """
            UPDATE page_versions
            SET status = ?, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND page_id = ? AND status = ? AND deleted = 0
            """,
            (STATUS_DISABLED, actor, actor_id, timestamp, tenant_id, page_id, STATUS_PUBLISHED),
        )
        conn.execute(
            """
            UPDATE page_definitions
            SET status = ?, current_version_id = NULL, editor = ?, editor_id = ?, update_time = ?,
                lock_version = lock_version + 1
            WHERE tenant_id = ? AND id = ? AND deleted = 0
            """,
            (STATUS_DRAFT, actor, actor_id, timestamp, tenant_id, page_id),
        )
    saved = get_page(tenant_id=tenant_id, page_id=page_id)
    if not saved:
        raise RuntimeError("page unpublish failed")
    return saved


def save_menu_mount(*, tenant_id: int, page_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> dict[str, Any]:
    timestamp = now_iso()
    menu_key = str(payload["menu_key"]).strip()
    with connect(database_target(), readonly=False) as conn:
        require_page_designer_schema(conn)
        existing = conn.execute(
            "SELECT * FROM page_menu_mounts WHERE tenant_id = ? AND page_id = ? AND deleted = 0",
            (tenant_id, page_id),
        ).fetchone()
        try:
            if existing:
                conn.execute(
                    """
                    UPDATE page_menu_mounts
                    SET menu_key = ?, parent_key = ?, path = ?, route_name = ?, permission_code = ?,
                        sort_order = ?, is_enabled = 1, editor = ?, editor_id = ?, update_time = ?,
                        lock_version = lock_version + 1
                    WHERE id = ?
                    """,
                    (
                        menu_key,
                        str(payload.get("parent_key") or ""),
                        str(payload["path"]),
                        str(payload["route_name"]),
                        str(payload.get("permission_code") or "page_designer:page:view"),
                        int(payload.get("sort_order") or 0),
                        actor,
                        actor_id,
                        timestamp,
                        int(existing["id"]),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO page_menu_mounts (
                        tenant_id, page_id, menu_key, parent_key, path, route_name, permission_code,
                        sort_order, is_enabled, creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        page_id,
                        menu_key,
                        str(payload.get("parent_key") or ""),
                        str(payload["path"]),
                        str(payload["route_name"]),
                        str(payload.get("permission_code") or "page_designer:page:view"),
                        int(payload.get("sort_order") or 0),
                        actor,
                        actor_id,
                        actor,
                        actor_id,
                        timestamp,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise_unique_error(exc)
    return get_menu_mount(tenant_id=tenant_id, page_id=page_id) or {}


def delete_menu_mount(*, tenant_id: int, page_id: int, actor: str, actor_id: int | None) -> dict[str, Any] | None:
    existing = get_menu_mount(tenant_id=tenant_id, page_id=page_id)
    if not existing:
        return None
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_page_designer_schema(conn)
        conn.execute(
            f"""
            UPDATE page_menu_mounts
            SET menu_key = {deleted_text_expression(conn, 'menu_key', 'id')}, deleted = 1, is_enabled = 0,
                editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE tenant_id = ? AND page_id = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, tenant_id, page_id),
        )
    return existing


def get_menu_mount(*, tenant_id: int, page_id: int) -> dict[str, Any] | None:
    with connect(database_target(), readonly=True) as conn:
        require_page_designer_schema(conn)
        row = conn.execute(
            "SELECT * FROM page_menu_mounts WHERE tenant_id = ? AND page_id = ? AND deleted = 0 AND is_enabled = 1",
            (tenant_id, page_id),
        ).fetchone()
    return dict(row) if row else None


def row_to_page(row: dict[str, Any]) -> PageDefinition:
    menu_key = str(row.get("mounted_menu_key") or "")
    return PageDefinition(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        page_key=str(row.get("page_key") or ""),
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        page_type=str(row.get("page_type") or "dashboard"),
        status=str(row.get("status") or STATUS_DRAFT),
        current_version_id=int(row["current_version_id"]) if row.get("current_version_id") not in (None, "") else None,
        thumbnail_file_id=int(row["thumbnail_file_id"]) if row.get("thumbnail_file_id") not in (None, "") else None,
        settings=decode_json_object(row.get("settings_json")),
        menu_mounted=bool(menu_key),
        menu_key=menu_key,
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_version(row: dict[str, Any]) -> PageVersion:
    return PageVersion(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        page_id=int(row["page_id"]),
        version_no=int(row.get("version_no") or 1),
        schema_version=str(row.get("schema_version") or DEFAULT_SCHEMA_VERSION),
        layout=decode_json_object(row.get("layout_json")),
        components=decode_json_list(row.get("components_json")),
        data_bindings=decode_json_object(row.get("data_bindings_json")),
        interactions=decode_json_object(row.get("interactions_json")),
        status=str(row.get("status") or STATUS_DRAFT),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def encode_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def decode_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def decode_json_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not value:
        return []
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


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


def deleted_text_expression(conn: Any, column_name: str, id_column: str) -> str:
    if getattr(conn, "backend", "sqlite") == "postgres":
        return f"('__deleted__' || {id_column}::text || '_' || {column_name})"
    if getattr(conn, "backend", "sqlite") == "mysql":
        return f"CONCAT('__deleted__', {id_column}, '_', {column_name})"
    return f"('__deleted__' || {id_column} || '_' || {column_name})"


def raise_unique_error(exc: Exception) -> None:
    message = str(exc).lower()
    if "page_definitions" in message:
        raise PageDesignerDomainError("页面标识已存在") from exc
    if "page_menu_mounts" in message:
        raise PageDesignerDomainError("菜单挂载已存在") from exc
    raise exc
