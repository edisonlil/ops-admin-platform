from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import (
    apply_sql_script,
    create_table_statement,
    ddl_filename,
    ensure_soft_delete_active_marker_unique,
    table_exists,
)


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_personalization_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_personalization_constraints(conn)


def require_personalization_schema(conn: Any) -> None:
    required_tables = ("personalization_table_column_preferences",)
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "personalization storage is not initialized; run `python scripts/init_personalization.py`"
            + f" (missing tables: {', '.join(missing)})"
        )


def ensure_personalization_constraints(conn: Any) -> None:
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="personalization_table_column_preferences",
        key_columns=("tenant_id", "user_id", "view_key"),
        sqlite_create_table_sql=create_table_statement(
            PERSISTENCE_DIR / "ddl.sqlite.sql",
            "personalization_table_column_preferences",
        ),
        constraint_name="uq_personalization_table_columns_active",
    )
