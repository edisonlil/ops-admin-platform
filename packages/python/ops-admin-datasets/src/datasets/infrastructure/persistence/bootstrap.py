from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import (
    add_column_if_missing,
    apply_sql_script,
    backend_name,
    column_exists,
    create_table_statement,
    ddl_filename,
    ensure_soft_delete_active_marker_unique,
    table_exists,
)
from system.infrastructure.persistence.readiness import is_ready, mark_ready


PERSISTENCE_DIR = Path(__file__).resolve().parent
SCHEMA_NAME = "datasets"


def ensure_datasets_schema(conn: Any) -> None:
    ensure_datasets_columns(conn)
    ensure_datasets_active_markers(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_datasets_active_markers(conn)
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists():
        apply_sql_script(conn, seed_path)
    mark_ready(conn, SCHEMA_NAME)


def require_datasets_schema(conn: Any) -> None:
    if is_ready(conn, SCHEMA_NAME):
        return
    required_tables = (
        "datasets",
        "dataset_fields",
        "dataset_versions",
        "dataset_rows",
        "dataset_query_runs",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "dataset storage is not initialized; run `python scripts/init_datasets.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    missing_columns = []
    for table_name in ("datasets", "dataset_fields"):
        if not column_exists(conn, table_name, "active_marker"):
            missing_columns.append(f"{table_name}.active_marker")
    if not column_exists(conn, "datasets", "query_config_json"):
        missing_columns.append("datasets.query_config_json")
    if missing_columns:
        raise RuntimeError(
            "dataset storage is not initialized; run `python scripts/init_datasets.py`"
            + f" (missing columns: {', '.join(missing_columns)})"
        )
    mark_ready(conn, SCHEMA_NAME)


def ensure_datasets_columns(conn: Any) -> None:
    add_column_if_missing(conn, "datasets", "owner_user_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "datasets", "owner_department_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "datasets", "query_config_json", query_config_column_definition(conn))
    add_column_if_missing(conn, "datasets", "published_version_id", "BIGINT DEFAULT NULL")


def query_config_column_definition(conn: Any) -> str:
    if backend_name(conn) == "mysql":
        return "LONGTEXT"
    return "TEXT NOT NULL DEFAULT '{}'"


def ensure_datasets_active_markers(conn: Any) -> None:
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="datasets",
        key_columns=("tenant_id", "key"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "datasets"),
        constraint_name="datasets_current_unique",
    )
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="dataset_fields",
        key_columns=("tenant_id", "dataset_id", "field_key"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "dataset_fields"),
        constraint_name="dataset_fields_current_unique",
    )
