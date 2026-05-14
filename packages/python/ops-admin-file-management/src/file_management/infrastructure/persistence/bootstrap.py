from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import (
    add_column_if_missing,
    apply_sql_script,
    column_exists,
    ddl_filename,
    table_exists,
)


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_file_management_schema(conn: Any) -> None:
    ensure_file_management_columns(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))


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

def ensure_file_management_columns(conn: Any) -> None:
    add_column_if_missing(conn, "file_objects", "folder_id", "BIGINT DEFAULT NULL")
