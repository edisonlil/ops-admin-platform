from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_llm_schema(conn: Any) -> None:
    filename = "ddl.postgres.sql" if getattr(conn, "backend", "sqlite") == "postgres" else "ddl.sqlite.sql"
    ensure_tenant_columns(conn)
    apply_sql_script(conn, PERSISTENCE_DIR / filename)
    ensure_tenant_columns(conn)


def require_llm_schema(conn: Any) -> None:
    required_tables = (
        "llm_configs",
        "llm_providers",
        "llm_models",
        "llm_tasks",
        "llm_routing_policies",
        "llm_routing_policy_entries",
        "llm_call_logs",
    )
    missing_tables = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    missing_tenant_columns = [
        table_name
        for table_name in required_tables
        if table_name not in missing_tables and not has_tenant_column(conn, table_name)
    ]
    if missing_tables or missing_tenant_columns:
        details: list[str] = []
        if missing_tables:
            details.append(f"missing tables: {', '.join(missing_tables)}")
        if missing_tenant_columns:
            details.append(f"missing tenant_id columns: {', '.join(missing_tenant_columns)}")
        raise RuntimeError(
            "llm_runtime storage is not initialized; run `python scripts/init_llm_runtime.py`"
            + f" ({'; '.join(details)})"
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


def ensure_tenant_columns(conn: Any) -> None:
    for table_name in (
        "llm_configs",
        "llm_providers",
        "llm_models",
        "llm_tasks",
        "llm_routing_policies",
        "llm_routing_policy_entries",
        "llm_call_logs",
    ):
        ensure_tenant_column(conn, table_name)


def ensure_tenant_column(conn: Any, table_name: str) -> None:
    if not table_exists(conn, table_name):
        return
    if getattr(conn, "backend", "sqlite") == "postgres":
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_tenant ON {table_name}(tenant_id)")
        return
    columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if "tenant_id" not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN tenant_id INTEGER NOT NULL DEFAULT 1")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_tenant ON {table_name}(tenant_id)")


def has_tenant_column(conn: Any, table_name: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ? AND column_name = 'tenant_id'
            """,
            (table_name,),
        ).fetchone()
        return bool(row)
    columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    return "tenant_id" in columns


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
