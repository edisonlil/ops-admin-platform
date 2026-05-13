from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_basic_data_schema(conn: Any) -> None:
    filename = "ddl.postgres.sql" if getattr(conn, "backend", "sqlite") == "postgres" else "ddl.sqlite.sql"
    ensure_basic_data_columns(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / filename)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_business_dictionary_types_parent ON business_dictionary_types(tenant_id, parent_id, deleted)")
    seed_path = PERSISTENCE_DIR / "seed.sql"
    if seed_path.exists():
        apply_sql_script(conn, seed_path)


def require_basic_data_schema(conn: Any) -> None:
    required_tables = ("business_dictionary_types", "business_dictionary_items")
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "basic data storage is not initialized; run `python scripts/init_basic_data.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    if not column_exists(conn, "business_dictionary_types", "parent_id"):
        raise RuntimeError("basic data storage is not initialized; run `python scripts/init_basic_data.py` (missing columns: business_dictionary_types.parent_id)")


def ensure_basic_data_columns(conn: Any) -> None:
    if table_exists(conn, "business_dictionary_types") and not column_exists(conn, "business_dictionary_types", "parent_id"):
        conn.execute("ALTER TABLE business_dictionary_types ADD COLUMN parent_id BIGINT DEFAULT NULL")


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
    else:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        row = next((item for item in rows if str(item["name"]) == column_name), None)
    return bool(row)
