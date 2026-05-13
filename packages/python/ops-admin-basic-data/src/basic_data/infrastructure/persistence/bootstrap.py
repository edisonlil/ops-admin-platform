from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_basic_data_schema(conn: Any) -> None:
    filename = "ddl.postgres.sql" if getattr(conn, "backend", "sqlite") == "postgres" else "ddl.sqlite.sql"
    apply_sql_script(conn, PERSISTENCE_DIR / filename)
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
