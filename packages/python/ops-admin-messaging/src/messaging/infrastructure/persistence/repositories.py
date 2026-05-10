from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from messaging.domain.models import (
    DELIVERY_STATUS_SENT,
    MESSAGE_STATUS_DISPATCHED,
    RECIPIENT_STATUS_READ,
    MessageIntent,
    MessageRecipient,
)
from messaging.infrastructure.persistence.bootstrap import require_messaging_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def create_in_app_message(
    *,
    tenant_id: int,
    title: str,
    content: str,
    recipient_user_ids: list[int],
    message_type: str,
    priority: str,
    payload: dict[str, Any],
    sender_user_id: int | None,
    sender_name: str,
    actor: str,
) -> MessageIntent:
    timestamp = now_iso()
    target = {"user_ids": recipient_user_ids}
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO message_intents (
                tenant_id, message_type, priority, title, content, payload_json,
                sender_user_id, sender_name, target_scope, target_json, status,
                creator, creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                message_type,
                priority,
                title,
                content,
                encode_json(payload),
                sender_user_id,
                sender_name,
                "users",
                encode_json(target),
                MESSAGE_STATUS_DISPATCHED,
                actor,
                sender_user_id,
                actor,
                sender_user_id,
                timestamp,
                timestamp,
            ),
        )
        message_id = inserted_id(conn, cursor, "message_intents", timestamp, actor)
        for user_id in recipient_user_ids:
            recipient_cursor = conn.execute(
                """
                INSERT INTO message_recipients (
                    tenant_id, message_id, recipient_user_id, recipient_name,
                    delivery_summary_json, creator, creator_id, editor, editor_id,
                    create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    message_id,
                    user_id,
                    "",
                    encode_json({"in_app": DELIVERY_STATUS_SENT}),
                    actor,
                    sender_user_id,
                    actor,
                    sender_user_id,
                    timestamp,
                    timestamp,
                ),
            )
            recipient_id = inserted_id(conn, recipient_cursor, "message_recipients", timestamp, actor)
            conn.execute(
                """
                INSERT INTO message_channel_deliveries (
                    tenant_id, message_id, recipient_id, channel, status, sent_time,
                    request_json, response_json, creator, creator_id, editor, editor_id,
                    create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    message_id,
                    recipient_id,
                    "in_app",
                    DELIVERY_STATUS_SENT,
                    timestamp,
                    encode_json({"recipient_user_id": user_id}),
                    encode_json({"visible": True}),
                    actor,
                    sender_user_id,
                    actor,
                    sender_user_id,
                    timestamp,
                    timestamp,
                ),
            )
        row = conn.execute("SELECT * FROM message_intents WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(dict(row))


def list_messages(*, tenant_id: int, page: int, page_size: int) -> tuple[list[MessageIntent], int]:
    offset = (page - 1) * page_size
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        total_row = conn.execute(
            "SELECT COUNT(*) AS total FROM message_intents WHERE tenant_id = ? AND deleted = 0",
            (tenant_id,),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT *
            FROM message_intents
            WHERE tenant_id = ? AND deleted = 0
            ORDER BY create_time DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (tenant_id, page_size, offset),
        ).fetchall()
    return [row_to_message(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def list_inbox(*, tenant_id: int, user_id: int, page: int, page_size: int) -> tuple[list[MessageRecipient], int]:
    offset = (page - 1) * page_size
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        total_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM message_recipients r
            JOIN message_intents m ON m.id = r.message_id
            WHERE r.tenant_id = ? AND r.recipient_user_id = ?
              AND r.deleted = 0 AND m.deleted = 0
              AND r.archive_status = 'active'
            """,
            (tenant_id, user_id),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT
                r.*,
                m.title,
                m.content,
                m.message_type,
                m.priority
            FROM message_recipients r
            JOIN message_intents m ON m.id = r.message_id
            WHERE r.tenant_id = ? AND r.recipient_user_id = ?
              AND r.deleted = 0 AND m.deleted = 0
              AND r.archive_status = 'active'
            ORDER BY r.create_time DESC, r.id DESC
            LIMIT ? OFFSET ?
            """,
            (tenant_id, user_id, page_size, offset),
        ).fetchall()
    return [row_to_recipient(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def unread_count(*, tenant_id: int, user_id: int) -> int:
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM message_recipients
            WHERE tenant_id = ? AND recipient_user_id = ?
              AND read_status = 'unread' AND deleted = 0
              AND archive_status = 'active'
            """,
            (tenant_id, user_id),
        ).fetchone()
    return int(row["total"] if row else 0)


def mark_read(*, tenant_id: int, user_id: int, recipient_id: int) -> MessageRecipient | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        existing = conn.execute(
            """
            SELECT id
            FROM message_recipients
            WHERE id = ? AND tenant_id = ? AND recipient_user_id = ? AND deleted = 0
            """,
            (recipient_id, tenant_id, user_id),
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE message_recipients
            SET read_status = ?,
                read_time = COALESCE(read_time, ?),
                editor_id = ?,
                update_time = ?
            WHERE id = ?
            """,
            (RECIPIENT_STATUS_READ, timestamp, user_id, timestamp, recipient_id),
        )
    return get_recipient(tenant_id=tenant_id, user_id=user_id, recipient_id=recipient_id)


def mark_all_read(*, tenant_id: int, user_id: int) -> int:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM message_recipients
            WHERE tenant_id = ? AND recipient_user_id = ?
              AND read_status = 'unread' AND deleted = 0
            """,
            (tenant_id, user_id),
        ).fetchone()
        total = int(row["total"] if row else 0)
        conn.execute(
            """
            UPDATE message_recipients
            SET read_status = ?,
                read_time = COALESCE(read_time, ?),
                editor_id = ?,
                update_time = ?
            WHERE tenant_id = ? AND recipient_user_id = ?
              AND read_status = 'unread' AND deleted = 0
            """,
            (RECIPIENT_STATUS_READ, timestamp, user_id, timestamp, tenant_id, user_id),
        )
    return total


def get_recipient(*, tenant_id: int, user_id: int, recipient_id: int) -> MessageRecipient | None:
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        row = conn.execute(
            """
            SELECT
                r.*,
                m.title,
                m.content,
                m.message_type,
                m.priority
            FROM message_recipients r
            JOIN message_intents m ON m.id = r.message_id
            WHERE r.id = ? AND r.tenant_id = ? AND r.recipient_user_id = ?
              AND r.deleted = 0 AND m.deleted = 0
            """,
            (recipient_id, tenant_id, user_id),
        ).fetchone()
    return row_to_recipient(dict(row)) if row else None


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


def row_to_message(row: dict[str, Any]) -> MessageIntent:
    return MessageIntent(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        message_type=str(row.get("message_type") or "system"),
        priority=str(row.get("priority") or "normal"),
        title=str(row.get("title") or ""),
        content=str(row.get("content") or ""),
        payload=decode_json(row.get("payload_json")),
        sender_user_id=int(row["sender_user_id"]) if row.get("sender_user_id") is not None else None,
        sender_name=str(row.get("sender_name") or ""),
        target_scope=str(row.get("target_scope") or "users"),
        target=decode_json(row.get("target_json")),
        status=str(row.get("status") or ""),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_recipient(row: dict[str, Any]) -> MessageRecipient:
    return MessageRecipient(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        message_id=int(row["message_id"]),
        recipient_user_id=int(row["recipient_user_id"]),
        recipient_name=str(row.get("recipient_name") or ""),
        read_status=str(row.get("read_status") or "unread"),
        read_time=str(row["read_time"]) if row.get("read_time") is not None else None,
        archive_status=str(row.get("archive_status") or "active"),
        pin_status=str(row.get("pin_status") or "normal"),
        delivery_summary=decode_json(row.get("delivery_summary_json")),
        title=str(row.get("title") or ""),
        content=str(row.get("content") or ""),
        message_type=str(row.get("message_type") or "system"),
        priority=str(row.get("priority") or "normal"),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


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
