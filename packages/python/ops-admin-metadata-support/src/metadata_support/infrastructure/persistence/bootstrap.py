from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_metadata_support_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    apply_sql_script(conn, PERSISTENCE_DIR / "seed.sql")


def require_metadata_support_schema(conn: Any) -> None:
    required_tables = (
        "metadata_resource_types",
        "metadata_field_definitions",
        "metadata_tag_groups",
        "metadata_tags",
        "metadata_resource_metadata",
        "metadata_resource_metadata_entries",
        "metadata_resource_tags",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "metadata support storage is not initialized; run `python scripts/init_metadata_support.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
