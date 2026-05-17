from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import add_column_if_missing, apply_sql_script, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_cron_schema(conn: Any) -> None:
    ensure_cron_columns(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_cron_columns(conn)
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists():
        apply_sql_script(conn, seed_path)


def require_cron_schema(conn: Any) -> None:
    required_tables = (
        "cron_tasks",
        "cron_schedules",
        "cron_runs",
        "cron_attempts",
        "cron_external_bindings",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "cron storage is not initialized; run `python scripts/init_cron.py`"
            + f" (missing tables: {', '.join(missing)})"
        )


def ensure_cron_columns(conn: Any) -> None:
    if not table_exists(conn, "cron_tasks"):
        return
    add_column_if_missing(conn, "cron_tasks", "owner_user_id", "BIGINT DEFAULT NULL")
    add_column_if_missing(conn, "cron_tasks", "owner_department_id", "BIGINT DEFAULT NULL")
