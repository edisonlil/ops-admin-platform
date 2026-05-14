from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


def backend_name(conn: Any) -> str:
    return str(getattr(conn, "backend", "sqlite"))


def ddl_filename(conn: Any) -> str:
    return f"ddl.{backend_name(conn)}.sql"


def apply_sql_script(conn: Any, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
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
        statement = chunk.strip()
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
