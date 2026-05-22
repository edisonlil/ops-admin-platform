from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_ai_applications_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))


def require_ai_applications_schema(conn: Any) -> None:
    required_tables = (
        "ai_applications",
        "tenant_ai_quotas",
        "prompt_runtime_traces",
    )
    require_tables(conn, required_tables)


def require_ai_agent_schema(conn: Any) -> None:
    required_tables = (
        "ai_application_agent_conversations",
        "ai_application_agent_messages",
    )
    require_tables(conn, required_tables)


def require_tables(conn: Any, required_tables: tuple[str, ...]) -> None:
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "ai_applications storage is not initialized; run `python scripts/init_ai_applications.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
