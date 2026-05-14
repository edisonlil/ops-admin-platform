from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, backend_name, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_authorization_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    migrate_role_data_scope_unique_key(conn)
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists():
        apply_sql_script(conn, seed_path)


def require_authorization_schema(conn: Any) -> None:
    missing = [name for name in ("data_resource_descriptors", "role_data_scopes") if not table_exists(conn, name)]
    if missing:
        raise RuntimeError(
            "authorization storage is not initialized; run `python scripts/init_authorization.py`"
            + f" (missing tables: {', '.join(missing)})"
        )


def migrate_role_data_scope_unique_key(conn: Any) -> None:
    if backend_name(conn) != "sqlite":
        return
    row = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = 'role_data_scopes'
        """
    ).fetchone()
    create_sql = str(row["sql"] if row else "")
    if "UNIQUE (role_key, resource_key, action, deleted)" not in create_sql:
        return
    conn.execute("ALTER TABLE role_data_scopes RENAME TO role_data_scopes_legacy_unique")
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    conn.execute(
        """
        INSERT INTO role_data_scopes (
            id, tenant_id, role_key, resource_key, action, scope, department_ids_json,
            lock_version, deleted, create_time, creator, creator_id, update_time, editor, editor_id
        )
        SELECT
            id, COALESCE(tenant_id, 1), role_key, resource_key, action, scope, department_ids_json,
            lock_version, deleted, create_time, creator, creator_id, update_time, editor, editor_id
        FROM role_data_scopes_legacy_unique
        """
    )
    conn.execute("DROP TABLE role_data_scopes_legacy_unique")
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
