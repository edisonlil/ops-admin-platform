from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import (
    add_column_if_missing,
    apply_sql_script,
    column_exists,
    ddl_filename,
    ensure_index,
    table_exists,
)


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_basic_data_schema(conn: Any) -> None:
    ensure_basic_data_columns(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_index(
        conn,
        "idx_business_dictionary_types_parent",
        "CREATE INDEX IF NOT EXISTS idx_business_dictionary_types_parent ON business_dictionary_types(tenant_id, parent_id, deleted)",
    )
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists():
        apply_sql_script(conn, seed_path)


def require_basic_data_schema(conn: Any) -> None:
    required_tables = ("business_dictionary_types", "business_dictionary_items")
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "basic data storage is not initialized; run `python scripts/init_basic_data.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    if not column_exists(conn, "business_dictionary_types", "parent_id"):
        raise RuntimeError("basic data storage is not initialized; run `python scripts/init_basic_data.py` (missing columns: business_dictionary_types.parent_id)")


def ensure_basic_data_columns(conn: Any) -> None:
    add_column_if_missing(conn, "business_dictionary_types", "parent_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "business_dictionary_types", "owner_user_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "business_dictionary_types", "owner_department_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "business_dictionary_items", "owner_user_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "business_dictionary_items", "owner_department_id", "BIGINT DEFAULT NULL")
    if table_exists(conn, "business_dictionary_items") and column_exists(conn, "business_dictionary_items", "label"):
        conn.execute("ALTER TABLE business_dictionary_items DROP COLUMN label")
