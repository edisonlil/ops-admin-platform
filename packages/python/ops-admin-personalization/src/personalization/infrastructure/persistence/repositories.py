from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from personalization.domain.models import TableColumnPreference
from personalization.infrastructure.persistence.bootstrap import require_personalization_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def get_table_column_preference(*, tenant_id: int, user_id: int, view_key: str) -> TableColumnPreference | None:
    with connect(database_target(), readonly=True) as conn:
        require_personalization_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM personalization_table_column_preferences
            WHERE tenant_id = ? AND user_id = ? AND view_key = ? AND deleted = 0
            """,
            (tenant_id, user_id, view_key),
        ).fetchone()
    return row_to_table_column_preference(dict(row)) if row else None


def save_table_column_preference(
    *,
    tenant_id: int,
    user_id: int,
    view_key: str,
    visible_column_keys: list[str],
    column_order_keys: list[str],
    settings: dict[str, Any],
    actor: str,
    actor_id: int | None,
) -> TableColumnPreference:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_personalization_schema(conn)
        existing = conn.execute(
            """
            SELECT id
            FROM personalization_table_column_preferences
            WHERE tenant_id = ? AND user_id = ? AND view_key = ? AND deleted = 0
            """,
            (tenant_id, user_id, view_key),
        ).fetchone()
        values = (
            json_list(visible_column_keys),
            json_list(column_order_keys),
            json_object(settings),
            actor,
            actor_id,
            timestamp,
        )
        if existing:
            conn.execute(
                """
                UPDATE personalization_table_column_preferences
                SET visible_column_keys_json = ?,
                    column_order_keys_json = ?,
                    settings_json = ?,
                    editor = ?,
                    editor_id = ?,
                    update_time = ?,
                    lock_version = lock_version + 1
                WHERE id = ?
                """,
                (*values, int(existing["id"])),
            )
        else:
            conn.execute(
                """
                INSERT INTO personalization_table_column_preferences (
                    tenant_id, user_id, view_key, visible_column_keys_json, column_order_keys_json,
                    settings_json, creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    user_id,
                    view_key,
                    values[0],
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
    item = get_table_column_preference(tenant_id=tenant_id, user_id=user_id, view_key=view_key)
    if not item:
        raise RuntimeError("failed to save table column preference")
    return item


def delete_table_column_preference(
    *, tenant_id: int, user_id: int, view_key: str, actor: str, actor_id: int | None
) -> None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_personalization_schema(conn)
        conn.execute(
            """
            UPDATE personalization_table_column_preferences
            SET deleted = 1,
                active_marker = NULL,
                editor = ?,
                editor_id = ?,
                update_time = ?,
                lock_version = lock_version + 1
            WHERE tenant_id = ? AND user_id = ? AND view_key = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, tenant_id, user_id, view_key),
        )


def row_to_table_column_preference(row: dict[str, Any]) -> TableColumnPreference:
    return TableColumnPreference(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        user_id=int(row["user_id"]),
        view_key=str(row.get("view_key") or ""),
        visible_column_keys=parse_json_list(row.get("visible_column_keys_json")),
        column_order_keys=parse_json_list(row.get("column_order_keys_json")),
        settings=parse_json_object(row.get("settings_json")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def json_list(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_object(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def parse_json_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def parse_json_object(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
