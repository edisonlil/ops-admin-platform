from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, ddl_filename


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_identity_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))


def ensure_identity_seed(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / "seed.sql")
