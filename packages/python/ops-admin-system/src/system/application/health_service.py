from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from system.infrastructure.config import resolve_database_url, resolve_db_path
from system.infrastructure.persistence.connection import connect, database_backend_for_target


def health_payload() -> dict[str, Any]:
    database_url = resolve_database_url()
    if database_url:
        backend = database_backend_for_target(database_url)
        healthy = check_database_connection(database_url)
        return {
            "status": "ok" if healthy else "degraded",
            "database_backend": backend,
            "database_source": database_source_label(backend),
            "database_detail": database_url_detail(database_url),
            "database_path": mask_database_url(database_url),
            "database_exists": healthy,
        }
    db_path = resolve_db_path()
    return {
        "status": "ok" if db_path.exists() else "degraded",
        "database_backend": "sqlite",
        "database_source": "Local SQLite",
        "database_detail": db_path.name,
        "database_path": str(db_path),
        "database_exists": db_path.exists(),
    }


def mask_database_url(database_url: str) -> str:
    if "@" not in database_url:
        return database_backend_for_target(database_url)
    scheme, _, rest = database_url.partition("://")
    _, _, host = rest.rpartition("@")
    return f"{scheme}://***@{host}" if scheme else f"***@{host}"


def database_source_label(backend: str) -> str:
    if backend == "postgres":
        return "Postgres"
    if backend == "mysql":
        return "MySQL"
    return "Database"


def database_url_detail(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = parsed.hostname or database_backend_for_target(database_url)
    port = f":{parsed.port}" if parsed.port else ""
    database = parsed.path.lstrip("/") or database_backend_for_target(database_url)
    return f"{host}{port}/{database}"


def check_database_connection(database_target: str | Path) -> bool:
    try:
        with connect(database_target, readonly=True) as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False
