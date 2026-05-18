from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_audit_logging_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    apply_sql_script(conn, PERSISTENCE_DIR / "seed.sql")


def require_audit_logging_schema(conn: Any) -> None:
    required_tables = (
        "audit_system_logs",
        "audit_operation_logs",
        "audit_api_logs",
        "audit_sql_logs",
        "audit_visitor_logs",
        "audit_logging_settings",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "audit logging storage is not initialized; run `python scripts/init_audit_logging.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
