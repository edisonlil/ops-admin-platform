from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_messaging_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))


def require_messaging_schema(conn: Any) -> None:
    required_tables = (
        "message_intents",
        "message_templates",
        "message_recipients",
        "message_channel_accounts",
        "message_channel_deliveries",
        "message_user_preferences",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "messaging storage is not initialized; run `python scripts/init_messaging.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
