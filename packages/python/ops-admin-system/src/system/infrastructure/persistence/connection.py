from __future__ import annotations

import sqlite3
from contextlib import contextmanager
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator
from urllib.parse import parse_qsl, unquote, urlparse


SqlObserver = Callable[[str, tuple[Any, ...], float, bool, str, str, bool], None]
_sql_observer: SqlObserver | None = None


def configure_sql_observer(observer: SqlObserver | None) -> None:
    global _sql_observer
    _sql_observer = observer


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
    wrapped_conn = ObservedSqliteConnection(conn, readonly=readonly, database_identity=str(db_file.resolve()))
    try:
        yield wrapped_conn
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

    def __init__(self, database_url: str, *, readonly: bool = False) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("psycopg is required for Postgres support") from exc

        self._conn = psycopg.connect(database_url, row_factory=dict_row)
        self._readonly = readonly
        parsed = urlparse(database_url)
        host = parsed.hostname or ""
        port = parsed.port or 5432
        database = unquote(parsed.path.lstrip("/"))
        self.database_identity = f"{host}:{port}/{database}"

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> Any:
        cursor = self._conn.cursor()
        execute_params = tuple(params or ())
        started = time.perf_counter()
        try:
            cursor.execute(to_postgres_sql(sql), execute_params)
        except Exception as exc:
            notify_sql_observer(sql, execute_params, started, False, str(exc), self.backend, self._readonly)
            self._conn.rollback()
            raise
        notify_sql_observer(sql, execute_params, started, True, "", self.backend, self._readonly)
        return cursor

    def executemany(self, sql: str, params: Iterable[Iterable[Any]]) -> Any:
        cursor = self._conn.cursor()
        params_list = [tuple(row) for row in params]
        started = time.perf_counter()
        try:
            cursor.executemany(to_postgres_sql(sql), params_list)
        except Exception as exc:
            notify_sql_observer(sql, (), started, False, str(exc), self.backend, self._readonly)
            self._conn.rollback()
            raise
        notify_sql_observer(sql, (), started, True, "", self.backend, self._readonly)
        return cursor

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


class MySQLConnection:
    backend = "mysql"

    def __init__(self, database_url: str, *, readonly: bool = False) -> None:
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
        self._readonly = readonly
        self.database_identity = f"{parsed.hostname}:{parsed.port or 3306}/{database}"

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> Any:
        cursor = self._conn.cursor()
        execute_params = tuple(params or ())
        started = time.perf_counter()
        try:
            cursor.execute(to_percent_sql(sql), execute_params)
        except Exception as exc:
            notify_sql_observer(sql, execute_params, started, False, str(exc), self.backend, self._readonly)
            raise
        notify_sql_observer(sql, execute_params, started, True, "", self.backend, self._readonly)
        return cursor

    def executemany(self, sql: str, params: Iterable[Iterable[Any]]) -> Any:
        cursor = self._conn.cursor()
        params_list = [tuple(row) for row in params]
        started = time.perf_counter()
        try:
            cursor.executemany(to_percent_sql(sql), params_list)
        except Exception as exc:
            notify_sql_observer(sql, (), started, False, str(exc), self.backend, self._readonly)
            raise
        notify_sql_observer(sql, (), started, True, "", self.backend, self._readonly)
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
    conn = PostgresConnection(database_url, readonly=readonly)
    if readonly:
        conn.execute("SET TRANSACTION READ ONLY")
    return conn


def connect_mysql(database_url: str, *, readonly: bool) -> MySQLConnection:
    conn = MySQLConnection(database_url, readonly=readonly)
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


class ObservedSqliteConnection:
    backend = "sqlite"

    def __init__(self, conn: sqlite3.Connection, *, readonly: bool, database_identity: str) -> None:
        self._conn = conn
        self._readonly = readonly
        self.database_identity = database_identity

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> Any:
        execute_params = tuple(params or ())
        started = time.perf_counter()
        try:
            cursor = self._conn.execute(sql, execute_params)
        except Exception as exc:
            notify_sql_observer(sql, execute_params, started, False, str(exc), self.backend, self._readonly)
            raise
        notify_sql_observer(sql, execute_params, started, True, "", self.backend, self._readonly)
        return cursor

    def executemany(self, sql: str, params: Iterable[Iterable[Any]]) -> Any:
        params_list = list(params)
        started = time.perf_counter()
        try:
            cursor = self._conn.executemany(sql, params_list)
        except Exception as exc:
            notify_sql_observer(sql, (), started, False, str(exc), self.backend, self._readonly)
            raise
        notify_sql_observer(sql, (), started, True, "", self.backend, self._readonly)
        return cursor

    def executescript(self, sql_script: str) -> Any:
        return self._conn.executescript(sql_script)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def notify_sql_observer(
    sql: str,
    params: tuple[Any, ...],
    started: float,
    success: bool,
    error_message: str,
    backend: str,
    readonly: bool,
) -> None:
    if _sql_observer is None:
        return
    duration_ms = (time.perf_counter() - started) * 1000
    try:
        _sql_observer(sql, params, duration_ms, success, error_message, backend, readonly)
    except Exception:
        return
