from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from messaging.domain.models import (
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_SENT,
    MESSAGE_STATUS_DISPATCHED,
    RECIPIENT_STATUS_READ,
    MessageChannelAccount,
    MessageIntent,
    MessageRecipient,
    MessageTemplate,
    MessageUserPreference,
)
from messaging.infrastructure.persistence.bootstrap import require_messaging_schema
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, append_data_scope_sql
from system.application.database import connect, resolve_database_url, resolve_db_path
from system.application.sorting import build_order_by, parse_sort_params


MESSAGE_SORT_COLUMNS = {
    "id": "id",
    "message_type": "message_type",
    "priority": "priority",
    "title": "title",
    "sender_name": "sender_name",
    "status": "status",
    "create_time": "create_time",
    "update_time": "update_time",
}
INBOX_SORT_COLUMNS = {
    "id": "r.id",
    "message_type": "m.message_type",
    "priority": "m.priority",
    "title": "m.title",
    "read_status": "r.read_status",
    "archive_status": "r.archive_status",
    "pin_status": "r.pin_status",
    "create_time": "r.create_time",
    "update_time": "r.update_time",
}
TEMPLATE_SORT_COLUMNS = {
    "id": "id",
    "template_key": "template_key",
    "name": "name",
    "status": "status",
    "create_time": "create_time",
    "update_time": "update_time",
}
CHANNEL_ACCOUNT_SORT_COLUMNS = {
    "id": "id",
    "channel": "channel",
    "name": "name",
    "enabled": "enabled",
    "is_default": "is_default",
    "create_time": "create_time",
    "update_time": "update_time",
}


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


MESSAGE_RESOURCE = ResourceDescriptor(resource_key="messaging.message")


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
    owner_department_id: int | None = None,
) -> MessageIntent:
    return create_message(
        tenant_id=tenant_id,
        title=title,
        content=content,
        recipient_user_ids=recipient_user_ids,
        message_type=message_type,
        priority=priority,
        payload=payload,
        sender_user_id=sender_user_id,
        sender_name=sender_name,
        actor=actor,
        template_id=None,
        channels=["in_app"],
        owner_department_id=owner_department_id,
    )


def create_message(
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
    template_id: int | None,
    channels: list[str],
    owner_department_id: int | None = None,
) -> MessageIntent:
    timestamp = now_iso()
    target = {"user_ids": recipient_user_ids}
    normalized_channels = normalize_channels(channels)
    delivery_summary = {
        channel: DELIVERY_STATUS_SENT if channel == "in_app" else DELIVERY_STATUS_PENDING
        for channel in normalized_channels
    }
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        channel_accounts = default_channel_accounts(conn, tenant_id=tenant_id, channels=normalized_channels)
        cursor = conn.execute(
            """
            INSERT INTO message_intents (
                tenant_id, message_type, priority, title, content, payload_json,
                sender_user_id, sender_name, target_scope, target_json, status, template_id,
                owner_user_id, owner_department_id, creator, creator_id, editor,
                editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                template_id,
                sender_user_id,
                owner_department_id,
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
                    encode_json(delivery_summary),
                    actor,
                    sender_user_id,
                    actor,
                    sender_user_id,
                    timestamp,
                    timestamp,
                ),
            )
            recipient_id = inserted_id(conn, recipient_cursor, "message_recipients", timestamp, actor)
            for channel in normalized_channels:
                status = DELIVERY_STATUS_SENT if channel == "in_app" else DELIVERY_STATUS_PENDING
                conn.execute(
                    """
                    INSERT INTO message_channel_deliveries (
                        tenant_id, message_id, recipient_id, channel, channel_account_id,
                        status, sent_time, request_json, response_json, creator, creator_id,
                        editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        message_id,
                        recipient_id,
                        channel,
                        channel_accounts.get(channel),
                        status,
                        timestamp if status == DELIVERY_STATUS_SENT else None,
                        encode_json({"recipient_user_id": user_id, "title": title, "content": content}),
                        encode_json(delivery_response(channel, status)),
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


def list_messages(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    data_scope: DataAccessPredicate | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[MessageIntent], int]:
    offset = (page - 1) * page_size
    filters = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    append_data_scope_sql(filters, params, data_scope, MESSAGE_RESOURCE)
    where_sql = " AND ".join(filters)
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=MESSAGE_SORT_COLUMNS,
        default="create_time DESC, id DESC",
        tie_breaker="id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        total_row = conn.execute(
            f"SELECT COUNT(*) AS total FROM message_intents WHERE {where_sql}",
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            f"""
            SELECT *
            FROM message_intents
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, offset),
        ).fetchall()
    return [row_to_message(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def list_inbox(
    *,
    tenant_id: int,
    user_id: int,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[MessageRecipient], int]:
    offset = (page - 1) * page_size
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=INBOX_SORT_COLUMNS,
        default="r.create_time DESC, r.id DESC",
        tie_breaker="r.id DESC",
    )
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
            f"""
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
            ORDER BY {order_by}
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


def list_templates(*, tenant_id: int, sort_by: str | None = None, sort_dir: str | None = None) -> list[MessageTemplate]:
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=TEMPLATE_SORT_COLUMNS,
        default="update_time DESC, id DESC",
        tie_breaker="id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM message_templates
            WHERE tenant_id = ? AND deleted = 0
            ORDER BY {order_by}
            """,
            (tenant_id,),
        ).fetchall()
    return [row_to_template(dict(row)) for row in rows]


def save_template(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MessageTemplate:
    timestamp = now_iso()
    template_id = int(payload.get("id") or 0)
    template_key = str(payload.get("template_key") or "").strip()
    values = (
        template_key,
        str(payload.get("name") or "").strip(),
        str(payload.get("description") or "").strip(),
        encode_json_list(payload.get("channels"), default=["in_app"]),
        str(payload.get("title_template") or "").strip(),
        str(payload.get("content_template") or "").strip(),
        encode_json(payload.get("variables_schema") if isinstance(payload.get("variables_schema"), dict) else {}),
        str(payload.get("status") or "draft").strip() or "draft",
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        if template_id:
            conn.execute(
                """
                UPDATE message_templates
                SET template_key = ?, name = ?, description = ?, channels_json = ?,
                    title_template = ?, content_template = ?, variables_schema_json = ?,
                    status = ?, editor = ?, editor_id = ?, update_time = ?
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (*values, template_id, tenant_id),
            )
            saved_id = template_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO message_templates (
                    tenant_id, template_key, name, description, channels_json,
                    title_template, content_template, variables_schema_json, status,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, *values[:8], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "message_templates", timestamp, actor)
        row = conn.execute("SELECT * FROM message_templates WHERE id = ?", (saved_id,)).fetchone()
    return row_to_template(dict(row))


def set_template_status(*, tenant_id: int, template_id: int, status: str, actor: str, actor_id: int | None) -> MessageTemplate | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        conn.execute(
            """
            UPDATE message_templates
            SET status = ?, editor = ?, editor_id = ?, update_time = ?
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (status, actor, actor_id, timestamp, template_id, tenant_id),
        )
        row = conn.execute(
            "SELECT * FROM message_templates WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (template_id, tenant_id),
        ).fetchone()
    return row_to_template(dict(row)) if row else None


def list_channel_accounts(*, tenant_id: int, sort_by: str | None = None, sort_dir: str | None = None) -> list[MessageChannelAccount]:
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=CHANNEL_ACCOUNT_SORT_COLUMNS,
        default="channel ASC, is_default DESC, id DESC",
        tie_breaker="id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM message_channel_accounts
            WHERE tenant_id = ? AND deleted = 0
            ORDER BY {order_by}
            """,
            (tenant_id,),
        ).fetchall()
    return [row_to_channel_account(dict(row)) for row in rows]


def save_channel_account(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MessageChannelAccount:
    timestamp = now_iso()
    account_id = int(payload.get("id") or 0)
    channel = str(payload.get("channel") or "").strip()
    is_default = bool(payload.get("is_default", False))
    values = (
        channel,
        str(payload.get("name") or "").strip(),
        encode_json(payload.get("config") if isinstance(payload.get("config"), dict) else {}),
        str(payload.get("secret_ref") or "").strip(),
        bool(payload.get("enabled", True)),
        is_default,
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        if is_default:
            conn.execute(
                """
                UPDATE message_channel_accounts
                SET is_default = 0, editor = ?, editor_id = ?, update_time = ?
                WHERE tenant_id = ? AND channel = ? AND deleted = 0
                """,
                (actor, actor_id, timestamp, tenant_id, channel),
            )
        if account_id:
            conn.execute(
                """
                UPDATE message_channel_accounts
                SET channel = ?, name = ?, config_json = ?, secret_ref = ?, enabled = ?,
                    is_default = ?, editor = ?, editor_id = ?, update_time = ?
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (*values, account_id, tenant_id),
            )
            saved_id = account_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO message_channel_accounts (
                    tenant_id, channel, name, config_json, secret_ref, enabled, is_default,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, *values[:6], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "message_channel_accounts", timestamp, actor)
        row = conn.execute("SELECT * FROM message_channel_accounts WHERE id = ?", (saved_id,)).fetchone()
    return row_to_channel_account(dict(row))


def set_channel_account_enabled(
    *, tenant_id: int, account_id: int, enabled: bool, actor: str, actor_id: int | None
) -> MessageChannelAccount | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        conn.execute(
            """
            UPDATE message_channel_accounts
            SET enabled = ?, editor = ?, editor_id = ?, update_time = ?
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (enabled, actor, actor_id, timestamp, account_id, tenant_id),
        )
        row = conn.execute(
            "SELECT * FROM message_channel_accounts WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (account_id, tenant_id),
        ).fetchone()
    return row_to_channel_account(dict(row)) if row else None


def get_channel_account(*, tenant_id: int, account_id: int) -> MessageChannelAccount | None:
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        row = conn.execute(
            "SELECT * FROM message_channel_accounts WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (account_id, tenant_id),
        ).fetchone()
    return row_to_channel_account(dict(row)) if row else None


def get_template_by_key(*, tenant_id: int, template_key: str) -> MessageTemplate | None:
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM message_templates
            WHERE tenant_id = ? AND template_key = ? AND deleted = 0
            """,
            (tenant_id, template_key),
        ).fetchone()
    return row_to_template(dict(row)) if row else None


def list_preferences(*, tenant_id: int, user_id: int) -> list[MessageUserPreference]:
    with connect(database_target(), readonly=True) as conn:
        require_messaging_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM message_user_preferences
            WHERE tenant_id = ? AND user_id = ? AND deleted = 0
            ORDER BY message_type ASC
            """,
            (tenant_id, user_id),
        ).fetchall()
    return [row_to_preference(dict(row)) for row in rows]


def save_preferences(
    *, tenant_id: int, user_id: int, preferences: list[dict[str, Any]], actor: str, actor_id: int | None
) -> list[MessageUserPreference]:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_messaging_schema(conn)
        for item in preferences:
            message_type = str(item.get("message_type") or "system").strip() or "system"
            existing = conn.execute(
                """
                SELECT id
                FROM message_user_preferences
                WHERE tenant_id = ? AND user_id = ? AND message_type = ? AND deleted = 0
                """,
                (tenant_id, user_id, message_type),
            ).fetchone()
            values = (
                encode_json_list(item.get("channels"), default=["in_app"]),
                encode_json(item.get("quiet_hours") if isinstance(item.get("quiet_hours"), dict) else {}),
                bool(item.get("enabled", True)),
                actor,
                actor_id,
                timestamp,
            )
            if existing:
                conn.execute(
                    """
                    UPDATE message_user_preferences
                    SET channels_json = ?, quiet_hours_json = ?, enabled = ?,
                        editor = ?, editor_id = ?, update_time = ?
                    WHERE id = ?
                    """,
                    (*values, int(existing["id"])),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO message_user_preferences (
                        tenant_id, user_id, message_type, channels_json, quiet_hours_json, enabled,
                        creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, user_id, message_type, *values[:3], actor, actor_id, actor, actor_id, timestamp, timestamp),
                )
    return list_preferences(tenant_id=tenant_id, user_id=user_id)


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


def row_to_template(row: dict[str, Any]) -> MessageTemplate:
    return MessageTemplate(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        template_key=str(row.get("template_key") or ""),
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        channels=decode_json_list(row.get("channels_json")),
        title_template=str(row.get("title_template") or ""),
        content_template=str(row.get("content_template") or ""),
        variables_schema=decode_json(row.get("variables_schema_json")),
        status=str(row.get("status") or "draft"),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_channel_account(row: dict[str, Any]) -> MessageChannelAccount:
    return MessageChannelAccount(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        channel=str(row.get("channel") or ""),
        name=str(row.get("name") or ""),
        config=mask_channel_config(decode_json(row.get("config_json"))),
        secret_ref=str(row.get("secret_ref") or ""),
        enabled=bool(row.get("enabled")),
        is_default=bool(row.get("is_default")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_preference(row: dict[str, Any]) -> MessageUserPreference:
    return MessageUserPreference(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        user_id=int(row["user_id"]),
        message_type=str(row.get("message_type") or "system"),
        channels=decode_json_list(row.get("channels_json")),
        quiet_hours=decode_json(row.get("quiet_hours_json")),
        enabled=bool(row.get("enabled")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def encode_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def normalize_channels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["in_app"]
    normalized: list[str] = []
    for item in value:
        channel = str(item or "").strip()
        if channel and channel not in normalized:
            normalized.append(channel)
    return normalized or ["in_app"]


def default_channel_accounts(conn: Any, *, tenant_id: int, channels: list[str]) -> dict[str, int | None]:
    channel_accounts: dict[str, int | None] = {channel: None for channel in channels}
    for channel in channels:
        row = conn.execute(
            """
            SELECT id
            FROM message_channel_accounts
            WHERE tenant_id = ? AND channel = ? AND enabled = TRUE AND deleted = 0
            ORDER BY is_default DESC, id DESC
            LIMIT 1
            """,
            (tenant_id, channel),
        ).fetchone()
        if row:
            channel_accounts[channel] = int(row["id"])
    return channel_accounts


def delivery_response(channel: str, status: str) -> dict[str, Any]:
    if channel == "in_app":
        return {"visible": True}
    return {"queued": True, "message": "外部渠道适配器尚未接入，已记录待投递台账"} if status == DELIVERY_STATUS_PENDING else {}


def encode_json_list(value: Any, *, default: list[str]) -> str:
    if not isinstance(value, list):
        return json.dumps(default, ensure_ascii=False, separators=(",", ":"))
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return json.dumps(normalized or default, ensure_ascii=False, separators=(",", ":"))


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


def decode_json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not value:
        return []
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload]


def mask_channel_config(config: dict[str, Any]) -> dict[str, Any]:
    masked = dict(config)
    for key in list(masked):
        normalized = key.lower()
        if any(token in normalized for token in ("secret", "token", "password", "key")):
            if masked.get(key):
                masked[key] = "******"
    return masked
