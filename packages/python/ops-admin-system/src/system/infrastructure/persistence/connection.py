from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import parse_qsl, unquote, urlparse


@contextmanager
def connect(database_target: str | Path, *, readonly: bool) -> Iterator[Any]:
    backend = database_backend_for_target(database_target)
    if backend in {"postgres", "mysql"}:
        conn = connect_url(str(database_target), backend=backend, readonly=readonly)
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


class MySQLConnection:
    backend = "mysql"

    def __init__(self, database_url: str) -> None:
        try:
            import pymysql
            import pymysql.cursors
        except ImportError as exc:
            raise RuntimeError("PyMySQL is required for MySQL support") from exc

        parsed = urlparse(database_url)
        if not parsed.hostname:
            raise RuntimeError("MySQL database URL must include a host")
        database = unquote(parsed.path.lstrip("/"))
        if not database:
            raise RuntimeError("MySQL database URL must include a database name")
        options = dict(parse_qsl(parsed.query, keep_blank_values=True))
        connect_args: dict[str, Any] = {
            "host": parsed.hostname,
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "database": database,
            "charset": options.pop("charset", "utf8mb4"),
            "autocommit": False,
            "cursorclass": pymysql.cursors.DictCursor,
        }
        for key in ("ssl_ca", "ssl_cert", "ssl_key"):
            if key in options:
                connect_args.setdefault("ssl", {})[key.removeprefix("ssl_")] = options.pop(key)
        self._conn = pymysql.connect(**connect_args)

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> Any:
        cursor = self._conn.cursor()
        cursor.execute(to_percent_sql(sql), tuple(params or ()))
        return cursor

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def connect_url(database_url: str, *, backend: str, readonly: bool) -> Any:
    if backend == "postgres":
        return connect_postgres(database_url, readonly=readonly)
    if backend == "mysql":
        return connect_mysql(database_url, readonly=readonly)
    raise RuntimeError(f"unsupported database backend: {backend}")


def connect_postgres(database_url: str, *, readonly: bool) -> PostgresConnection:
    conn = PostgresConnection(database_url)
    if readonly:
        conn.execute("SET TRANSACTION READ ONLY")
    return conn


def connect_mysql(database_url: str, *, readonly: bool) -> MySQLConnection:
    conn = MySQLConnection(database_url)
    if readonly:
        conn.execute("SET TRANSACTION READ ONLY")
    return conn


def to_postgres_sql(sql: str) -> str:
    return to_percent_sql(sql)


def to_percent_sql(sql: str) -> str:
    return sql.replace("?", "%s")


def database_backend_for_target(database_target: str | Path) -> str:
    value = str(database_target)
    if value.startswith(("postgres://", "postgresql://")):
        return "postgres"
    if value.startswith(("mysql://", "mysql+pymysql://", "mysql+mysqlconnector://")):
        return "mysql"
    return "sqlite"


def is_database_url(value: str) -> bool:
    return database_backend_for_target(value) in {"postgres", "mysql"}
