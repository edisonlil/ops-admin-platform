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


def load_application_config() -> dict[str, Any]:
    for path in application_config_candidates():
        if not path.exists():
            continue
        return load_json_object(path, "application config")
    return {}


def application_config_candidates() -> list[Path]:
    configured = os.environ.get("OPS_ADMIN_APPLICATION_CONFIG", "").strip()
    if configured:
        return [Path(configured)]

    root = repo_root()
    config_dir = root / "config"
    return [
        config_dir / "application.local.json",
        config_dir / "application.json",
    ]


def section_config(config: dict[str, Any], *section_names: str) -> dict[str, Any]:
    for section_name in section_names:
        section = config.get(section_name)
        if isinstance(section, dict):
            return section
    return config


def config_string(config: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(config.get(key, "")).strip()
        if value:
            return value
    return ""


def config_bool(config: dict[str, Any], *keys: str) -> bool | None:
    for key in keys:
        if key not in config:
            continue
        value = config[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    return None


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload
