from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import (
    add_column_if_missing,
    apply_sql_script,
    column_exists,
    create_table_statement,
    ddl_filename,
    ensure_soft_delete_active_marker_unique,
    table_exists,
)


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_ai_assets_schema(conn: Any) -> None:
    ensure_ai_assets_columns(conn)
    ensure_ai_assets_active_markers(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_ai_assets_columns(conn)
    ensure_ai_assets_active_markers(conn)


def require_ai_assets_schema(conn: Any) -> None:
    required_tables = (
        "prompt_assets",
        "prompt_versions",
        "skill_assets",
        "skill_versions",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "AI assets storage is not initialized; run `python scripts/init_ai_assets.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    missing_columns = []
    for table_name in ("prompt_assets", "prompt_versions", "skill_assets", "skill_versions"):
        if not column_exists(conn, table_name, "active_marker"):
            missing_columns.append(f"{table_name}.active_marker")
    if missing_columns:
        raise RuntimeError(
            "AI assets storage is not initialized; run `python scripts/init_ai_assets.py`"
            + f" (missing columns: {', '.join(missing_columns)})"
        )


def ensure_ai_assets_columns(conn: Any) -> None:
    if not table_exists(conn, "prompt_assets"):
        pass
    else:
        add_column_if_missing(conn, "prompt_assets", "owner_user_id", "BIGINT DEFAULT NULL")
        add_column_if_missing(conn, "prompt_assets", "owner_department_id", "BIGINT DEFAULT NULL")
    if table_exists(conn, "skill_assets"):
        add_column_if_missing(conn, "skill_assets", "owner_user_id", "BIGINT DEFAULT NULL")
        add_column_if_missing(conn, "skill_assets", "owner_department_id", "BIGINT DEFAULT NULL")


def ensure_ai_assets_active_markers(conn: Any) -> None:
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="prompt_assets",
        key_columns=("tenant_id", "prompt_key"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "prompt_assets"),
        constraint_name="prompt_assets_current_unique",
    )
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="prompt_versions",
        key_columns=("tenant_id", "prompt_id", "version"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "prompt_versions"),
        constraint_name="prompt_versions_current_unique",
    )
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="skill_assets",
        key_columns=("tenant_id", "skill_key"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "skill_assets"),
        constraint_name="skill_assets_current_unique",
    )
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="skill_versions",
        key_columns=("tenant_id", "skill_id", "version"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "skill_versions"),
        constraint_name="skill_versions_current_unique",
    )
