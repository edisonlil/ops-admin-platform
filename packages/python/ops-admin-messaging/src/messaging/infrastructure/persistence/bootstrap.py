from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import add_column_if_missing, apply_sql_script, ddl_filename, table_exists
from system.infrastructure.persistence.readiness import is_ready, mark_ready


PERSISTENCE_DIR = Path(__file__).resolve().parent
SCHEMA_NAME = "messaging"


def ensure_messaging_schema(conn: Any) -> None:
    ensure_messaging_columns(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_messaging_columns(conn)
    mark_ready(conn, SCHEMA_NAME)


def require_messaging_schema(conn: Any) -> None:
    if is_ready(conn, SCHEMA_NAME):
        return
    required_tables = (
        "message_intents",
        "message_templates",
        "message_recipients",
        "message_channel_accounts",
        "message_chat_bots",
        "message_channel_deliveries",
        "message_user_preferences",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "messaging storage is not initialized; run `python scripts/init_messaging.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    mark_ready(conn, SCHEMA_NAME)


def ensure_messaging_columns(conn: Any) -> None:
    if not table_exists(conn, "message_intents"):
        return
    add_column_if_missing(conn, "message_intents", "owner_user_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "message_intents", "owner_department_id", "BIGINT DEFAULT NULL")
