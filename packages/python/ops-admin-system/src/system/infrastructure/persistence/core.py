from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import MetaData, Table, and_, create_engine, insert, select, update
from sqlalchemy.engine import Connection, Engine

from system.application.tenancy import current_tenant_scope


metadata = MetaData()
_engines: dict[str, Engine] = {}


def engine_for(database_target: str) -> Engine:
    url = database_target
    if not url.startswith(("sqlite://", "postgres://", "postgresql://")):
        url = f"sqlite:///{database_target}"
    engine = _engines.get(url)
    if engine is None:
        engine = create_engine(url, future=True)
        _engines[url] = engine
    return engine


def now_text() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def scoped_select(table: Table, *where: Any, include_inactive_tenant: bool = False):
    scope = current_tenant_scope()
    clauses = list(where)
    if "tenant_id" in table.c:
        clauses.append(table.c.tenant_id == scope.tenant_id)
    return select(table).where(and_(*clauses)) if clauses else select(table)


def scoped_insert(conn: Connection, table: Table, values: dict[str, Any]):
    payload = dict(values)
    scope = current_tenant_scope()
    timestamp = now_text()
    if "tenant_id" in table.c and "tenant_id" not in payload:
        payload["tenant_id"] = scope.tenant_id
    if "created_at" in table.c and "created_at" not in payload:
        payload["created_at"] = timestamp
    if "updated_at" in table.c and "updated_at" not in payload:
        payload["updated_at"] = timestamp
    return conn.execute(insert(table).values(**payload))


def scoped_update(conn: Connection, table: Table, values: dict[str, Any], *where: Any):
    payload = dict(values)
    scope = current_tenant_scope()
    clauses = list(where)
    if "tenant_id" in table.c:
        clauses.append(table.c.tenant_id == scope.tenant_id)
    if "updated_at" in table.c and "updated_at" not in payload:
        payload["updated_at"] = now_text()
    return conn.execute(update(table).where(and_(*clauses)).values(**payload))
