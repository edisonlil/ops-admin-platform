from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_database_config() -> dict[str, Any]:
    config_path = os.environ.get("FG_AGENT_DATABASE_CONFIG", "").strip()
    candidates = [Path(config_path)] if config_path else [
        repo_root() / "config" / "database.local.json",
        repo_root() / "config" / "database.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            raise ValueError(f"database config must be a JSON object: {path}")
        return payload
    return {}


def resolve_database_url() -> str | None:
    for name in ("FG_AGENT_DATABASE_URL", "SUPABASE_DB_URL", "DATABASE_URL"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    config = load_database_config()
    for key in ("database_url", "url", "connection_string"):
        value = str(config.get(key, "")).strip()
        if value:
            return value
    supabase = config.get("supabase")
    if isinstance(supabase, dict):
        for key in ("database_url", "url", "connection_string"):
            value = str(supabase.get(key, "")).strip()
            if value:
                return value
    return None


def resolve_db_path() -> Path:
    configured = os.environ.get("FG_AGENT_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    config = load_database_config()
    configured = str(config.get("db_path", "") or config.get("sqlite_path", "")).strip()
    return Path(configured) if configured else repo_root() / "ops_admin.db"


def auth_database_target() -> str | Path:
    database_url = resolve_database_url()
    if database_url:
        return database_url
    db_path = resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def auth_secret() -> str:
    return os.environ.get("FG_AGENT_AUTH_SECRET", "fg-agent-dev-secret-change-me")


def default_admin_username() -> str:
    return os.environ.get("FG_AGENT_ADMIN_USERNAME", "admin").strip() or "admin"


def default_admin_password() -> str:
    return os.environ.get("FG_AGENT_ADMIN_PASSWORD", "edc3000")
