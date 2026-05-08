from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator


@contextmanager
def connect(database_target: str | Path, *, readonly: bool) -> Iterator[Any]:
    if is_database_url(str(database_target)):
        conn = connect_postgres(str(database_target), readonly=readonly)
        try:
            yield conn
            if not readonly:
                conn.commit()
        except Exception:
            if not readonly:
                conn.rollback()
            raise
        finally:
            conn.close()
        return

    db_file = Path(database_target)
    if readonly:
        uri = f"file:{db_file.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        if not readonly:
            conn.commit()
    except Exception:
        if not readonly:
            conn.rollback()
        raise
    finally:
        conn.close()


class PostgresConnection:
    backend = "postgres"

    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("psycopg is required for Postgres support") from exc

        self._conn = psycopg.connect(database_url, row_factory=dict_row)

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> Any:
        cursor = self._conn.cursor()
        cursor.execute(to_postgres_sql(sql), tuple(params or ()))
        return cursor

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def connect_postgres(database_url: str, *, readonly: bool) -> PostgresConnection:
    conn = PostgresConnection(database_url)
    if readonly:
        conn.execute("SET TRANSACTION READ ONLY")
    return conn


def to_postgres_sql(sql: str) -> str:
    return sql.replace("?", "%s")


def is_database_url(value: str) -> bool:
    return value.startswith(("postgres://", "postgresql://"))
