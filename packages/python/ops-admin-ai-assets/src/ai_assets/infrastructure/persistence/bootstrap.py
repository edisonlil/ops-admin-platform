from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_ai_assets_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))


def require_ai_assets_schema(conn: Any) -> None:
    required_tables = (
        "prompt_assets",
        "prompt_versions",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "AI assets storage is not initialized; run `python scripts/init_ai_assets.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
