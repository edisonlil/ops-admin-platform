"""
Project application config helpers for ops-cli.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def application_config_path(project_path: Path, env: str | None = None) -> Path:
    suffix = env if env else "local"
    return project_path / "config" / f"application.{suffix}.json"


def legacy_database_config_path(project_path: Path, env: str | None = None) -> Path:
    suffix = env if env else "local"
    return project_path / "config" / f"database.{suffix}.json"


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}


def read_application_config(project_path: Path, env: str | None = None) -> tuple[dict[str, Any], Path | None]:
    app_path = application_config_path(project_path, env)
    app_config = load_json_object(app_path)
    if app_config:
        return app_config, app_path
    return {}, None


def read_database_config(project_path: Path, env: str | None = None) -> tuple[dict[str, Any], Path | None]:
    app_path = application_config_path(project_path, env)
    app_config = load_json_object(app_path)
    database = app_config.get("database")
    if isinstance(database, dict):
        return database, app_path

    legacy_path = legacy_database_config_path(project_path, env)
    legacy_config = load_json_object(legacy_path)
    if legacy_config:
        legacy_database = legacy_config.get("database")
        if isinstance(legacy_database, dict):
            return legacy_database, legacy_path
        return legacy_config, legacy_path

    return {}, None


def write_database_config(project_path: Path, database: dict[str, Any], env: str | None = None) -> Path:
    config_dir = project_path / "config"
    config_dir.mkdir(exist_ok=True)

    config_path = application_config_path(project_path, env)
    app_config = load_json_object(config_path)
    app_config["database"] = database
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(app_config, f, indent=2, ensure_ascii=False)
    return config_path
