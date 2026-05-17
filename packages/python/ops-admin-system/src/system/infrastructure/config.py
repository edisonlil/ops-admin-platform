from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from system.application.config import config_bool, config_string, load_application_config, repo_root
from system.infrastructure.persistence.connection import database_backend_for_target


def load_database_config() -> dict[str, Any]:
    app_config = load_application_config()
    database = app_config.get("database")
    if isinstance(database, dict):
        return database
    return load_legacy_database_config()


def load_legacy_database_config() -> dict[str, Any]:
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
        value = config_string(config, key)
        if value:
            return value
    supabase = config.get("supabase")
    if isinstance(supabase, dict):
        for key in ("database_url", "url", "connection_string"):
            value = str(supabase.get(key, "")).strip()
            if value:
                return value
    return None


def database_backend() -> str:
    database_url = resolve_database_url()
    return database_backend_for_target(database_url) if database_url else "sqlite"


def default_use_keywords_recall() -> bool:
    configured = os.environ.get("FG_AGENT_USE_KEYWORDS_RECALL", "").strip()
    if configured:
        return configured.lower() in {"1", "true", "yes", "on"}

    config = load_database_config()
    for key in ("use_keywords_recall", "keywords_recall"):
        configured = config_bool(config, key)
        if configured is not None:
            return configured

    recommendation = config.get("recommendation")
    if isinstance(recommendation, dict):
        for key in ("use_keywords_recall", "keywords_recall"):
            configured = config_bool(recommendation, key)
            if configured is not None:
                return configured

    return True


def resolve_db_path() -> Path:
    configured = os.environ.get("FG_AGENT_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    config = load_database_config()
    configured = config_string(config, "db_path", "sqlite_path")
    return Path(configured) if configured else repo_root() / "ops_admin.db"


def admin_dist_path() -> Path:
    # Check environment variable first, then fall back to standard locations
    env_path = os.environ.get("FG_AGENT_ADMIN_DIST_PATH", "").strip()
    if env_path:
        return Path(env_path)
    
    # Try standard locations
    root = repo_root()
    candidates = [
        root / "dist",
        root / "web" / "admin" / "dist",
        Path("/app/dist"),
        Path("/app/web/admin/dist"),
    ]
    
    for path in candidates:
        if path.exists() and path.is_dir():
            # Check if it looks like a Vue SPA dist (has index.html)
            if (path / "index.html").exists():
                return path
    
    # Return default
    return Path("/app/dist")


def auth_secret() -> str:
    return os.environ.get("FG_AGENT_AUTH_SECRET", "fg-agent-dev-secret-change-me")


def default_admin_username() -> str:
    return os.environ.get("FG_AGENT_ADMIN_USERNAME", "admin").strip() or "admin"


def default_admin_password() -> str:
    return os.environ.get("FG_AGENT_ADMIN_PASSWORD", "edc3000")


def cors_origins() -> list[str]:
    configured = os.environ.get("FG_AGENT_CORS_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]
