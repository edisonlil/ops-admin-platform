from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import add_column_if_missing, apply_sql_script, backend_name, column_exists, ddl_filename, table_exists


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_organization_schema(conn: Any) -> None:
    ensure_user_department_membership_shape(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
    ensure_user_department_membership_shape(conn)
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists():
        apply_sql_script(conn, seed_path)


def require_organization_schema(conn: Any) -> None:
    missing = [name for name in ("departments", "user_department_memberships") if not table_exists(conn, name)]
    if missing:
        raise RuntimeError(
            "organization storage is not initialized; run `python scripts/init_organization.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    if not column_exists(conn, "user_department_memberships", "active_marker"):
        raise RuntimeError(
            "organization storage is not initialized; run `python scripts/init_organization.py`"
            " (missing columns: user_department_memberships.active_marker)"
        )


def ensure_user_department_membership_shape(conn: Any) -> None:
    if not table_exists(conn, "user_department_memberships"):
        return
    add_column_if_missing(conn, "user_department_memberships", "active_marker", "BIGINT DEFAULT 1")
    conn.execute("UPDATE user_department_memberships SET active_marker = 1 WHERE deleted = 0 AND active_marker IS NULL")
    conn.execute("UPDATE user_department_memberships SET active_marker = NULL WHERE deleted <> 0")
    backend = backend_name(conn)
    if backend == "sqlite":
        ensure_sqlite_user_department_membership_unique_key(conn)
    elif backend == "postgres":
        ensure_postgres_user_department_membership_unique_key(conn)
    elif backend == "mysql":
        ensure_mysql_user_department_membership_unique_key(conn)


def ensure_sqlite_user_department_membership_unique_key(conn: Any) -> None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'user_department_memberships'",
    ).fetchone()
    table_sql = str(row["sql"] if row else "")
    if "UNIQUE (tenant_id, user_id, department_id, active_marker)" in table_sql:
        return
    conn.execute("DROP TABLE IF EXISTS user_department_memberships_migration")
    conn.execute(
        """
        CREATE TABLE user_department_memberships_migration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            department_id INTEGER NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 0,
            active_marker INTEGER DEFAULT 1,
            lock_version INTEGER NOT NULL DEFAULT 0,
            deleted INTEGER NOT NULL DEFAULT 0,
            create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            creator TEXT DEFAULT NULL,
            creator_id INTEGER DEFAULT NULL,
            update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            editor TEXT DEFAULT NULL,
            editor_id INTEGER DEFAULT NULL,
            UNIQUE (tenant_id, user_id, department_id, active_marker)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO user_department_memberships_migration (
            id, tenant_id, user_id, department_id, is_primary, active_marker, lock_version,
            deleted, create_time, creator, creator_id, update_time, editor, editor_id
        )
        SELECT id,
               tenant_id,
               user_id,
               department_id,
               is_primary,
               CASE WHEN deleted = 0 THEN 1 ELSE NULL END,
               lock_version,
               deleted,
               create_time,
               creator,
               creator_id,
               update_time,
               editor,
               editor_id
        FROM user_department_memberships
        """
    )
    conn.execute("DROP TABLE user_department_memberships")
    conn.execute("ALTER TABLE user_department_memberships_migration RENAME TO user_department_memberships")


def ensure_postgres_user_department_membership_unique_key(conn: Any) -> None:
    conn.execute(
        """
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT c.conname INTO constraint_name
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'user_department_memberships'
              AND c.contype = 'u'
              AND (
                  SELECT array_agg(a.attname ORDER BY key.ordinality)
                  FROM unnest(c.conkey) WITH ORDINALITY AS key(attnum, ordinality)
                  JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = key.attnum
              ) = ARRAY['tenant_id', 'user_id', 'department_id', 'deleted'];

            IF constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE user_department_memberships DROP CONSTRAINT %I', constraint_name);
            END IF;

            SELECT c.conname INTO constraint_name
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'user_department_memberships'
              AND c.contype = 'u'
              AND (
                  SELECT array_agg(a.attname ORDER BY key.ordinality)
                  FROM unnest(c.conkey) WITH ORDINALITY AS key(attnum, ordinality)
                  JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = key.attnum
              ) = ARRAY['tenant_id', 'user_id', 'department_id', 'active_marker'];

            IF constraint_name IS NULL THEN
                ALTER TABLE user_department_memberships
                ADD CONSTRAINT user_department_memberships_current_unique
                UNIQUE (tenant_id, user_id, department_id, active_marker);
            END IF;
        END $$;
        """
    )


def ensure_mysql_user_department_membership_unique_key(conn: Any) -> None:
    old_index = conn.execute(
        """
        SELECT index_name
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 'user_department_memberships'
          AND non_unique = 0
        GROUP BY index_name
        HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index) = 'tenant_id,user_id,department_id,deleted'
        LIMIT 1
        """
    ).fetchone()
    if old_index:
        conn.execute(f"ALTER TABLE user_department_memberships DROP INDEX `{old_index['index_name']}`")
    current_index = conn.execute(
        """
        SELECT index_name
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 'user_department_memberships'
          AND non_unique = 0
        GROUP BY index_name
        HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index) = 'tenant_id,user_id,department_id,active_marker'
        LIMIT 1
        """
    ).fetchone()
    if not current_index:
        conn.execute(
            """
            CREATE UNIQUE INDEX idx_user_department_memberships_current_unique
            ON user_department_memberships(tenant_id, user_id, department_id, active_marker)
            """
        )
