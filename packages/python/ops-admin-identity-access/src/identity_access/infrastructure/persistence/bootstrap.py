from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_identity_schema(conn: Any) -> None:
    filename = "ddl.postgres.sql" if getattr(conn, "backend", "sqlite") == "postgres" else "ddl.sqlite.sql"
    apply_sql_script(conn, PERSISTENCE_DIR / filename)


def ensure_identity_seed(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / "seed.sql")


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
