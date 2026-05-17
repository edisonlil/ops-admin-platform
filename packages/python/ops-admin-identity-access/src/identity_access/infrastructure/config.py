from __future__ import annotations

from pathlib import Path

from system.infrastructure.config import (
    auth_secret,
    default_admin_password,
    default_admin_username,
    resolve_database_url,
    resolve_db_path,
)


def auth_database_target() -> str | Path:
    database_url = resolve_database_url()
    if database_url:
        return database_url
    db_path = resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path
