from __future__ import annotations

from pathlib import Path
from typing import Any

from datasets.domain.exceptions import DatasetDomainError
from system.application.database import connect, resolve_database_url, resolve_db_path


MAX_TABLES = 100
MAX_COLUMNS_PER_TABLE = 80
SYSTEM_TABLE_PREFIXES = ("sqlite_",)
SYSTEM_TABLE_NAMES = {
    "alembic_version",
    "dataset_query_runs",
}


class DatabaseSourceSchemaInspector:
    def inspect_source_schema(self) -> dict[str, Any]:
        try:
            with connect(database_target(), readonly=True) as conn:
                backend = str(getattr(conn, "backend", "sqlite"))
                return {
                    "backend": backend,
                    "tables": inspect_tables(conn, backend),
                }
        except Exception as exc:
            raise DatasetDomainError(f"dataset source schema inspect failed: {exc}") from exc


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def inspect_tables(conn: Any, backend: str) -> list[dict[str, Any]]:
    if backend == "postgres":
        return inspect_postgres_tables(conn)
    if backend == "mysql":
        return inspect_mysql_tables(conn)
    return inspect_sqlite_tables(conn)


def inspect_sqlite_tables(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        LIMIT ?
        """,
        (MAX_TABLES,),
    ).fetchall()
    tables: list[dict[str, Any]] = []
    for row in rows:
        table_name = str(read_value(row, "name") or "")
        if should_hide_table(table_name):
            continue
        columns = [
            {
                "name": str(read_value(column, "name") or ""),
                "data_type": str(read_value(column, "type") or ""),
                "nullable": not bool(read_value(column, "notnull")),
                "primary_key": bool(read_value(column, "pk")),
            }
            for column in conn.execute(f"PRAGMA table_info({quote_sqlite_identifier(table_name)})").fetchall()[:MAX_COLUMNS_PER_TABLE]
        ]
        tables.append({"name": table_name, "schema": "", "columns": columns})
    return tables


def inspect_postgres_tables(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
        LIMIT ?
        """,
        (MAX_TABLES,),
    ).fetchall()
    return [
        {
            "name": str(read_value(row, "table_name") or ""),
            "schema": str(read_value(row, "table_schema") or ""),
            "columns": inspect_information_schema_columns(
                conn,
                schema=str(read_value(row, "table_schema") or ""),
                table=str(read_value(row, "table_name") or ""),
            ),
        }
        for row in rows
        if not should_hide_table(str(read_value(row, "table_name") or ""))
    ]


def inspect_mysql_tables(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
          AND table_schema = DATABASE()
        ORDER BY table_name
        LIMIT ?
        """,
        (MAX_TABLES,),
    ).fetchall()
    return [
        {
            "name": str(read_value(row, "table_name") or ""),
            "schema": str(read_value(row, "table_schema") or ""),
            "columns": inspect_information_schema_columns(
                conn,
                schema=str(read_value(row, "table_schema") or ""),
                table=str(read_value(row, "table_name") or ""),
            ),
        }
        for row in rows
        if not should_hide_table(str(read_value(row, "table_name") or ""))
    ]


def inspect_information_schema_columns(conn: Any, *, schema: str, table: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        LIMIT ?
        """,
        (schema, table, MAX_COLUMNS_PER_TABLE),
    ).fetchall()
    return [
        {
            "name": str(read_value(row, "column_name") or ""),
            "data_type": str(read_value(row, "data_type") or ""),
            "nullable": str(read_value(row, "is_nullable") or "").upper() != "NO",
            "primary_key": False,
        }
        for row in rows
    ]


def should_hide_table(table_name: str) -> bool:
    return table_name in SYSTEM_TABLE_NAMES or table_name.startswith(SYSTEM_TABLE_PREFIXES)


def quote_sqlite_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def read_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, None)
