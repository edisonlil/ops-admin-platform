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


def actor_values() -> dict[str, Any]:
    scope = current_tenant_scope()
    principal_name = scope.principal_name or ("system" if scope.source == "system" else scope.source)
    return {
        "actor_id": scope.principal_id,
        "actor_name": principal_name,
    }


def scoped_select(table: Table, *where: Any, include_deleted: bool = False, include_inactive_tenant: bool = False):
    scope = current_tenant_scope()
    clauses = list(where)
    if "tenant_id" in table.c:
        clauses.append(table.c.tenant_id == scope.tenant_id)
    if "deleted" in table.c and not include_deleted:
        clauses.append(table.c.deleted == 0)
    return select(table).where(and_(*clauses)) if clauses else select(table)


def scoped_insert(conn: Connection, table: Table, values: dict[str, Any]):
    payload = dict(values)
    scope = current_tenant_scope()
    timestamp = now_text()
    actor = actor_values()
    if "tenant_id" in table.c and "tenant_id" not in payload:
        payload["tenant_id"] = scope.tenant_id
    if "lock_version" in table.c and "lock_version" not in payload:
        payload["lock_version"] = 0
    if "deleted" in table.c and "deleted" not in payload:
        payload["deleted"] = 0
    if "create_time" in table.c and "create_time" not in payload:
        payload["create_time"] = timestamp
    if "update_time" in table.c and "update_time" not in payload:
        payload["update_time"] = timestamp
    if "creator" in table.c and "creator" not in payload:
        payload["creator"] = actor["actor_name"]
    if "creator_id" in table.c and "creator_id" not in payload:
        payload["creator_id"] = actor["actor_id"]
    if "editor" in table.c and "editor" not in payload:
        payload["editor"] = actor["actor_name"]
    if "editor_id" in table.c and "editor_id" not in payload:
        payload["editor_id"] = actor["actor_id"]
    return conn.execute(insert(table).values(**payload))


def scoped_update(conn: Connection, table: Table, values: dict[str, Any], *where: Any):
    payload = dict(values)
    scope = current_tenant_scope()
    actor = actor_values()
    clauses = list(where)
    if "tenant_id" in table.c:
        clauses.append(table.c.tenant_id == scope.tenant_id)
    if "deleted" in table.c:
        clauses.append(table.c.deleted == 0)
    if "update_time" in table.c and "update_time" not in payload:
        payload["update_time"] = now_text()
    if "editor" in table.c and "editor" not in payload:
        payload["editor"] = actor["actor_name"]
    if "editor_id" in table.c and "editor_id" not in payload:
        payload["editor_id"] = actor["actor_id"]
    if "lock_version" in table.c and "lock_version" not in payload:
        payload["lock_version"] = table.c.lock_version + 1
    return conn.execute(update(table).where(and_(*clauses)).values(**payload))


def scoped_soft_delete(conn: Connection, table: Table, *where: Any):
    return scoped_update(conn, table, {"deleted": 1}, *where)
