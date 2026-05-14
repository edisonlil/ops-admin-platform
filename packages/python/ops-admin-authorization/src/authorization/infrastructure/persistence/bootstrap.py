from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_authorization_schema(conn: Any) -> None:
    drop_role_data_scopes(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
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


def drop_role_data_scopes(conn: Any) -> None:
    if not table_exists(conn, "role_data_scopes"):
        return
    conn.execute("DROP TABLE role_data_scopes")
