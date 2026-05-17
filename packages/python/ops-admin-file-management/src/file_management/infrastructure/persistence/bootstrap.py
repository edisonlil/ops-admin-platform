from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import (
    add_column_if_missing,
    apply_sql_script,
    create_table_statement,
    column_exists,
    ddl_filename,
    ensure_soft_delete_active_marker_unique,
    table_exists,
)


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_file_management_schema(conn: Any) -> None:
    ensure_file_management_columns(conn)
    ensure_file_management_active_markers(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_file_management_active_markers(conn)


def require_file_management_schema(conn: Any) -> None:
    required_tables = (
        "file_libraries",
        "file_folders",
        "file_objects",
        "tenant_file_storage_quotas",
        "file_storage_profiles",
        "file_preview_profiles",
        "file_access_logs",
        "file_search_index_jobs",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "file management storage is not initialized; run `python scripts/init_file_management.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    missing_columns = []
    for table_name in ("file_libraries", "file_folders"):
        if not column_exists(conn, table_name, "active_marker"):
            missing_columns.append(f"{table_name}.active_marker")
    if missing_columns:
        raise RuntimeError(
            "file management storage is not initialized; run `python scripts/init_file_management.py`"
            + f" (missing columns: {', '.join(missing_columns)})"
        )

def ensure_file_management_columns(conn: Any) -> None:
    add_column_if_missing(conn, "file_objects", "folder_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "file_objects", "owner_user_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "file_objects", "owner_department_id", "BIGINT DEFAULT NULL")


def ensure_file_management_active_markers(conn: Any) -> None:
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="file_libraries",
        key_columns=("tenant_id", "name"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "file_libraries"),
        constraint_name="file_libraries_current_unique",
    )
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="file_folders",
        key_columns=("tenant_id", "library_id", "parent_id", "name"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "file_folders"),
        constraint_name="file_folders_current_unique",
    )
