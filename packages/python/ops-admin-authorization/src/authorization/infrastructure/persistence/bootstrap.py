from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import (
    apply_sql_script,
    column_exists,
    create_table_statement,
    ddl_filename,
    ensure_soft_delete_active_marker_unique,
    table_exists,
)


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_authorization_schema(conn: Any) -> None:
    drop_role_data_scopes(conn)
    ensure_authorization_active_markers(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_authorization_active_markers(conn)
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists():
        apply_sql_script(conn, seed_path)


def require_authorization_schema(conn: Any) -> None:
    missing = [name for name in ("data_resource_descriptors", "data_access_policies") if not table_exists(conn, name)]
    if missing:
        raise RuntimeError(
            "authorization storage is not initialized; run `python scripts/init_authorization.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    if not column_exists(conn, "data_access_policies", "active_marker"):
        raise RuntimeError(
            "authorization storage is not initialized; run `python scripts/init_authorization.py`"
            " (missing columns: data_access_policies.active_marker)"
        )


def drop_role_data_scopes(conn: Any) -> None:
    if not table_exists(conn, "role_data_scopes"):
        return
    conn.execute("DROP TABLE role_data_scopes")


def ensure_authorization_active_markers(conn: Any) -> None:
    ensure_soft_delete_active_marker_unique(
        conn,
        table_name="data_access_policies",
        key_columns=("tenant_id", "subject_type", "subject_id", "resource_key", "action"),
        sqlite_create_table_sql=create_table_statement(PERSISTENCE_DIR / "ddl.sqlite.sql", "data_access_policies"),
        constraint_name="data_access_policies_current_unique",
    )
