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


def ensure_authorization_schema(conn: Any) -> None:
    drop_role_data_scopes(conn)
    ensure_authorization_descriptor_columns(conn)
    ensure_authorization_active_markers(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_authorization_descriptor_columns(conn)
    ensure_authorization_active_markers(conn)
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists():
        apply_sql_script(conn, seed_path)
    ensure_self_and_subordinates_scope(conn)


def require_authorization_schema(conn: Any) -> None:
    missing = [name for name in ("data_resource_descriptors", "data_access_policies") if not table_exists(conn, name)]
    if missing:
        raise RuntimeError(
            "authorization storage is not initialized; run `python scripts/init_authorization.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    missing_columns = []
    for column_name in AUTHORIZATION_DESCRIPTOR_COLUMNS:
        if not column_exists(conn, "data_resource_descriptors", column_name):
            missing_columns.append(f"data_resource_descriptors.{column_name}")
    if not column_exists(conn, "data_access_policies", "active_marker"):
        missing_columns.append("data_access_policies.active_marker")
    if missing_columns:
        raise RuntimeError(
            "authorization storage is not initialized; run `python scripts/init_authorization.py`"
            + f" (missing columns: {', '.join(missing_columns)})"
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


AUTHORIZATION_DESCRIPTOR_COLUMNS = {
    "resource_id_column": "VARCHAR(120) NOT NULL DEFAULT 'id'",
    "access_mode": "VARCHAR(40) NOT NULL DEFAULT 'owner_columns'",
    "relation_table": "VARCHAR(160) NOT NULL DEFAULT ''",
    "relation_resource_id_column": "VARCHAR(120) NOT NULL DEFAULT ''",
    "relation_user_column": "VARCHAR(120) NOT NULL DEFAULT ''",
    "relation_department_column": "VARCHAR(120) NOT NULL DEFAULT ''",
    "relation_tenant_column": "VARCHAR(120) NOT NULL DEFAULT 'tenant_id'",
    "relation_deleted_column": "VARCHAR(120) NOT NULL DEFAULT 'deleted'",
    "relation_resource_key_column": "VARCHAR(120) NOT NULL DEFAULT ''",
    "relation_resource_key_value": "VARCHAR(160) NOT NULL DEFAULT ''",
    "relation_subject_type_column": "VARCHAR(120) NOT NULL DEFAULT ''",
    "relation_subject_type_user_value": "VARCHAR(80) NOT NULL DEFAULT ''",
    "relation_subject_type_department_value": "VARCHAR(80) NOT NULL DEFAULT ''",
}


def ensure_authorization_descriptor_columns(conn: Any) -> None:
    if not table_exists(conn, "data_resource_descriptors"):
        return
    for column_name, definition in AUTHORIZATION_DESCRIPTOR_COLUMNS.items():
        add_column_if_missing(conn, "data_resource_descriptors", column_name, definition)


def ensure_self_and_subordinates_scope(conn: Any) -> None:
    if not table_exists(conn, "data_resource_descriptors"):
        return
    conn.execute(
        """
        UPDATE data_resource_descriptors
        SET supported_scopes_json = '["self","self_and_subordinates","department","department_and_children","custom_departments","tenant"]'
        WHERE deleted = FALSE
          AND supported_scopes_json LIKE '%"self"%'
          AND supported_scopes_json NOT LIKE '%"self_and_subordinates"%'
        """
    )
