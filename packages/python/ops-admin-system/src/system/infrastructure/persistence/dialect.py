from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


def backend_name(conn: Any) -> str:
    return str(getattr(conn, "backend", "sqlite"))


def ddl_filename(conn: Any) -> str:
    return f"ddl.{backend_name(conn)}.sql"


def apply_sql_script(conn: Any, path: Path) -> None:
    sql = path.read_text(encoding="utf-8-sig")
    if backend_name(conn) == "sqlite" and hasattr(conn, "executescript"):
        conn.executescript(sql)
        return
    for statement in split_sql_statements(sql):
        if backend_name(conn) == "mysql":
            if is_existing_mysql_index(conn, statement):
                continue
            statement = mysql_index_statement(statement)
        conn.execute(statement)


def split_sql_statements(sql: str) -> Iterable[str]:
    for chunk in sql.split(";"):
        statement = chunk.strip().lstrip("\ufeff").strip()
        if not statement:
            continue
        if all(not line.strip() or line.strip().startswith("--") for line in statement.splitlines()):
            continue
        yield statement


def table_exists(conn: Any, table_name: str) -> bool:
    backend = backend_name(conn)
    if backend == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
        return bool(row)
    if backend == "mysql":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
        return bool(row)
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


def column_exists(conn: Any, table_name: str, column_name: str) -> bool:
    backend = backend_name(conn)
    if backend == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
            """,
            (table_name, column_name),
        ).fetchone()
        return bool(row)
    if backend == "mysql":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = ? AND column_name = ?
            """,
            (table_name, column_name),
        ).fetchone()
        return bool(row)
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(_column_name(row) == column_name for row in rows)


def _column_name(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("name", ""))
    try:
        return str(row["name"])
    except Exception:
        return str(row[1])


def text_json_type(conn: Any) -> str:
    backend = backend_name(conn)
    if backend == "postgres":
        return "JSONB"
    if backend == "mysql":
        return "LONGTEXT"
    return "TEXT"


def bigint_type(conn: Any) -> str:
    return "INTEGER" if backend_name(conn) == "sqlite" else "BIGINT"


def add_column_if_missing(conn: Any, table_name: str, column_name: str, definition: str) -> None:
    if not table_exists(conn, table_name) or column_exists(conn, table_name, column_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def ensure_index(conn: Any, index_name: str, statement: str) -> None:
    if backend_name(conn) == "mysql":
        if index_exists(conn, index_name):
            return
        statement = mysql_index_statement(statement)
    conn.execute(statement)


def ensure_soft_delete_active_marker_unique(
    conn: Any,
    *,
    table_name: str,
    key_columns: tuple[str, ...],
    sqlite_create_table_sql: str,
    constraint_name: str,
    active_marker_column: str = "active_marker",
) -> None:
    if not table_exists(conn, table_name):
        return
    add_column_if_missing(conn, table_name, active_marker_column, "BIGINT DEFAULT 1")
    conn.execute(f"UPDATE {table_name} SET {active_marker_column} = 1 WHERE deleted = 0 AND {active_marker_column} IS NULL")
    conn.execute(f"UPDATE {table_name} SET {active_marker_column} = NULL WHERE deleted <> 0")
    backend = backend_name(conn)
    if backend == "sqlite":
        ensure_sqlite_active_marker_unique(
            conn,
            table_name=table_name,
            key_columns=key_columns,
            sqlite_create_table_sql=sqlite_create_table_sql,
            active_marker_column=active_marker_column,
        )
    elif backend == "postgres":
        ensure_postgres_active_marker_unique(
            conn,
            table_name=table_name,
            key_columns=key_columns,
            constraint_name=constraint_name,
            active_marker_column=active_marker_column,
        )
    elif backend == "mysql":
        ensure_mysql_active_marker_unique(
            conn,
            table_name=table_name,
            key_columns=key_columns,
            index_name=constraint_name,
            active_marker_column=active_marker_column,
        )


def create_table_statement(sql_path: Path, table_name: str) -> str:
    sql = sql_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table_name)}\s*\(.*?\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(sql)
    if not match:
        raise RuntimeError(f"missing CREATE TABLE statement for {table_name}")
    return match.group(0)


def ensure_sqlite_active_marker_unique(
    conn: Any,
    *,
    table_name: str,
    key_columns: tuple[str, ...],
    sqlite_create_table_sql: str,
    active_marker_column: str,
) -> None:
    active_columns = (*key_columns, active_marker_column)
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)).fetchone()
    table_sql = str(row["sql"] if row else "")
    if _sqlite_unique_columns_present(table_sql, active_columns):
        return
    temp_table = f"{table_name}_active_marker_migration"
    conn.execute(f"DROP TABLE IF EXISTS {temp_table}")
    create_sql = re.sub(
        rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table_name)}\s*\(",
        f"CREATE TABLE {temp_table} (",
        sqlite_create_table_sql.strip().rstrip(";"),
        count=1,
        flags=re.IGNORECASE,
    )
    conn.execute(create_sql)
    old_columns = [_column_name(row) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    new_columns = [_column_name(row) for row in conn.execute(f"PRAGMA table_info({temp_table})").fetchall()]
    copied_columns = [column for column in new_columns if column in old_columns]
    column_list = ", ".join(copied_columns)
    conn.execute(f"INSERT INTO {temp_table} ({column_list}) SELECT {column_list} FROM {table_name}")
    conn.execute(f"DROP TABLE {table_name}")
    conn.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")


def _sqlite_unique_columns_present(table_sql: str, columns: tuple[str, ...]) -> bool:
    normalized = re.sub(r"\s+", " ", table_sql.lower())
    expected = ", ".join(column.lower() for column in columns)
    return f"unique ({expected})" in normalized


def ensure_postgres_active_marker_unique(
    conn: Any,
    *,
    table_name: str,
    key_columns: tuple[str, ...],
    constraint_name: str,
    active_marker_column: str,
) -> None:
    old_columns = list(key_columns) + ["deleted"]
    active_columns = list(key_columns) + [active_marker_column]
    conn.execute(
        """
        DO $$
        DECLARE
            existing_name text;
        BEGIN
            SELECT c.conname INTO existing_name
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = {table_name}
              AND c.contype = 'u'
              AND (
                  SELECT array_agg(a.attname ORDER BY key.ordinality)
                  FROM unnest(c.conkey) WITH ORDINALITY AS key(attnum, ordinality)
                  JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = key.attnum
              ) = {old_columns};

            IF existing_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', {table_name}, existing_name);
            END IF;

            SELECT c.conname INTO existing_name
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = {table_name}
              AND c.contype = 'u'
              AND (
                  SELECT array_agg(a.attname ORDER BY key.ordinality)
                  FROM unnest(c.conkey) WITH ORDINALITY AS key(attnum, ordinality)
                  JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = key.attnum
              ) = {active_columns};

            IF existing_name IS NULL THEN
                EXECUTE format(
                    'ALTER TABLE %I ADD CONSTRAINT %I UNIQUE ({columns})',
                    {table_name},
                    {constraint_name}
                );
            END IF;
        END $$;
        """.format(
            table_name=sql_literal(table_name),
            old_columns=postgres_text_array(old_columns),
            active_columns=postgres_text_array(active_columns),
            constraint_name=sql_literal(constraint_name),
            columns=", ".join(active_columns),
        )
    )


def ensure_mysql_active_marker_unique(
    conn: Any,
    *,
    table_name: str,
    key_columns: tuple[str, ...],
    index_name: str,
    active_marker_column: str,
) -> None:
    old_columns = ",".join((*key_columns, "deleted"))
    active_columns = ",".join((*key_columns, active_marker_column))
    old_index = conn.execute(
        """
        SELECT index_name
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = ?
          AND non_unique = 0
        GROUP BY index_name
        HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index) = ?
        LIMIT 1
        """,
        (table_name, old_columns),
    ).fetchone()
    if old_index:
        conn.execute(f"ALTER TABLE {table_name} DROP INDEX `{old_index['index_name']}`")
    current_index = conn.execute(
        """
        SELECT index_name
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = ?
          AND non_unique = 0
        GROUP BY index_name
        HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index) = ?
        LIMIT 1
        """,
        (table_name, active_columns),
    ).fetchone()
    if not current_index:
        conn.execute(f"CREATE UNIQUE INDEX {index_name} ON {table_name}({active_columns})")


def postgres_text_array(values: list[str]) -> str:
    return "ARRAY[" + ", ".join(sql_literal(value) for value in values) + "]"


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def index_exists(conn: Any, index_name: str) -> bool:
    backend = backend_name(conn)
    if backend == "mysql":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND index_name = ?
            LIMIT 1
            """,
            (index_name,),
        ).fetchone()
        return bool(row)
    if backend == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public' AND indexname = ?
            """,
            (index_name,),
        ).fetchone()
        return bool(row)
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?",
        (index_name,),
    ).fetchone()
    return bool(row)


def is_existing_mysql_index(conn: Any, statement: str) -> bool:
    match = re.match(r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_]+)\s+", statement, re.IGNORECASE)
    if not match:
        return False
    if index_exists(conn, match.group(1)):
        return True
    return False


def mysql_index_statement(statement: str) -> str:
    return re.sub(r"CREATE\s+(UNIQUE\s+)?INDEX\s+IF\s+NOT\s+EXISTS\s+", r"CREATE \1INDEX ", statement, flags=re.IGNORECASE)
