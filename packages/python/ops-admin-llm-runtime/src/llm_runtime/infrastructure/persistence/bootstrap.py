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


def ensure_llm_schema(conn: Any) -> None:
    ensure_tenant_columns(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_tenant_columns(conn)


def require_llm_schema(conn: Any) -> None:
    required_tables = (
        "llm_configs",
        "llm_providers",
        "llm_models",
        "llm_tasks",
        "llm_routing_policies",
        "llm_routing_policy_entries",
        "llm_call_logs",
    )
    missing_tables = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    missing_tenant_columns = [
        table_name
        for table_name in required_tables
        if table_name not in missing_tables and not has_tenant_column(conn, table_name)
    ]
    if missing_tables or missing_tenant_columns:
        details: list[str] = []
        if missing_tables:
            details.append(f"missing tables: {', '.join(missing_tables)}")
        if missing_tenant_columns:
            details.append(f"missing tenant_id columns: {', '.join(missing_tenant_columns)}")
        raise RuntimeError(
            "llm_runtime storage is not initialized; run `python scripts/init_llm_runtime.py`"
            + f" ({'; '.join(details)})"
        )

def ensure_tenant_columns(conn: Any) -> None:
    for table_name in (
        "llm_configs",
        "llm_providers",
        "llm_models",
        "llm_tasks",
        "llm_routing_policies",
        "llm_routing_policy_entries",
        "llm_call_logs",
    ):
        ensure_tenant_column(conn, table_name)


def ensure_tenant_column(conn: Any, table_name: str) -> None:
    if not table_exists(conn, table_name):
        return
    add_column_if_missing(conn, table_name, "tenant_id", "BIGINT NOT NULL DEFAULT 1")
    if table_name in {"llm_configs", "llm_providers", "llm_models", "llm_tasks", "llm_routing_policies"}:
        add_column_if_missing(conn, table_name, "owner_user_id", "BIGINT DEFAULT NULL")
        add_column_if_missing(conn, table_name, "owner_department_id", "BIGINT DEFAULT NULL")
    if table_name == "llm_call_logs":
        add_column_if_missing(conn, table_name, "owner_department_id", "BIGINT DEFAULT NULL")
    ensure_index(conn, f"idx_{table_name}_tenant", f"CREATE INDEX IF NOT EXISTS idx_{table_name}_tenant ON {table_name}(tenant_id)")
    if table_name in {"llm_configs", "llm_providers", "llm_models", "llm_tasks", "llm_routing_policies"}:
        ensure_index(
            conn,
            f"idx_{table_name}_owner_user",
            f"CREATE INDEX IF NOT EXISTS idx_{table_name}_owner_user ON {table_name}(tenant_id, owner_user_id, deleted)",
        )
        ensure_index(
            conn,
            f"idx_{table_name}_owner_department",
            f"CREATE INDEX IF NOT EXISTS idx_{table_name}_owner_department ON {table_name}(tenant_id, owner_department_id, deleted)",
        )
    if table_name == "llm_call_logs":
        ensure_index(
            conn,
            "idx_llm_call_logs_creator",
            "CREATE INDEX IF NOT EXISTS idx_llm_call_logs_creator ON llm_call_logs(tenant_id, creator_id, deleted)",
        )
        ensure_index(
            conn,
            "idx_llm_call_logs_owner_department",
            "CREATE INDEX IF NOT EXISTS idx_llm_call_logs_owner_department ON llm_call_logs(tenant_id, owner_department_id, deleted)",
        )


def has_tenant_column(conn: Any, table_name: str) -> bool:
    return column_exists(conn, table_name, "tenant_id")
