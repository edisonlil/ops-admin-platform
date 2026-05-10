from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").exists() and (parent / "packages").exists() and (parent / "api").exists():
            return parent
    return Path.cwd()


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


def database_backend() -> str:
    return "postgres" if resolve_database_url() else "sqlite"


def default_use_keywords_recall() -> bool:
    configured = os.environ.get("FG_AGENT_USE_KEYWORDS_RECALL", "").strip()
    if configured:
        return configured.lower() in {"1", "true", "yes", "on"}

    config = load_database_config()
    for key in ("use_keywords_recall", "keywords_recall"):
        if key in config:
            return bool(config[key])

    recommendation = config.get("recommendation")
    if isinstance(recommendation, dict):
        for key in ("use_keywords_recall", "keywords_recall"):
            if key in recommendation:
                return bool(recommendation[key])

    return True


def resolve_db_path() -> Path:
    configured = os.environ.get("FG_AGENT_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    config = load_database_config()
    configured = str(config.get("db_path", "") or config.get("sqlite_path", "")).strip()
    return Path(configured) if configured else repo_root() / "ops_admin.db"


def admin_dist_path() -> Path:
    return repo_root() / "web" / "admin" / "dist"


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
