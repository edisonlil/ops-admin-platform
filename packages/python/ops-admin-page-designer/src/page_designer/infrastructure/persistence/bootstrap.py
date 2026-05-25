from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_page_designer_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists() and table_exists(conn, "permissions") and table_exists(conn, "menus"):
        apply_sql_script(conn, seed_path)


def require_page_designer_schema(conn: Any) -> None:
    required_tables = ("page_definitions", "page_versions", "page_menu_mounts")
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "page designer storage is not initialized; run `python scripts/init_page_designer.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
