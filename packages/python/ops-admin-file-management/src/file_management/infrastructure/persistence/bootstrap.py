from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_file_management_schema(conn: Any) -> None:
    filename = "ddl.postgres.sql" if getattr(conn, "backend", "sqlite") == "postgres" else "ddl.sqlite.sql"
    ensure_file_management_columns(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / filename)


def require_file_management_schema(conn: Any) -> None:
    required_tables = (
        "file_libraries",
        "file_folders",
        "file_objects",
        "tenant_file_storage_quotas",
        "file_storage_profiles",
        "file_access_logs",
        "file_search_index_jobs",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "file management storage is not initialized; run `python scripts/init_file_management.py`"
            + f" (missing tables: {', '.join(missing)})"
        )


def apply_sql_script(conn: Any, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    if getattr(conn, "backend", "sqlite") != "postgres" and hasattr(conn, "executescript"):
        conn.executescript(sql)
        return
    for statement in split_sql_statements(sql):
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
    if getattr(conn, "backend", "sqlite") == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
    return bool(row)


def ensure_file_management_columns(conn: Any) -> None:
    if not table_exists(conn, "file_objects"):
        return
    if column_exists(conn, "file_objects", "folder_id"):
        return
    conn.execute("ALTER TABLE file_objects ADD COLUMN folder_id INTEGER DEFAULT NULL")


def column_exists(conn: Any, table_name: str, column_name: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
            """,
            (table_name, column_name),
        ).fetchone()
        return bool(row)
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row["name"] if hasattr(row, "keys") else row[1]) == column_name for row in rows)
