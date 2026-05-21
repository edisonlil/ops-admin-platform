"""
Configuration management for ops-cli.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# Default paths
DEFAULT_CONFIG_DIR = Path.home() / ".ops-cli"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_SCAFFOLD_URL = "https://github.com/edisonlil/ops-admin-platform.git"
DEFAULT_PROJECTS_DIR = Path.home() / "OpsPyProject"


class Config:
    """Configuration manager for ops-cli."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self._config: Optional[dict] = None

    @property
    def config_dir(self) -> Path:
        return self.config_path.parent

    def load(self) -> dict:
        """Load configuration from file."""
        if self._config is not None:
            return self._config

        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._config = self._default_config()

        return self._config

    def _default_config(self) -> dict:
        """Default configuration."""
        return {
            "scaffold_url": DEFAULT_SCAFFOLD_URL,
            "projects_dir": str(DEFAULT_PROJECTS_DIR),
            "projects": {},
            "current_project": None,
        }

    def save(self, config: Optional[dict] = None) -> None:
        """Save configuration to file."""
        if config is not None:
            self._config = config
        elif self._config is None:
            self._config = self._default_config()

        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.load().get(key, default)

    def set(self, key: str, value) -> None:
        """Set configuration value."""
        config = self.load()
        config[key] = value
        self.save(config)

    def get_projects(self) -> dict:
        """Get all projects."""
        return self.load().get("projects", {})

    def get_project(self, name: str) -> Optional[dict]:
        """Get project by name."""
        return self.get_projects().get(name)

    def find_project_for_path(self, path: Optional[Path] = None) -> Optional[tuple[str, dict]]:
        """Find the managed project that contains the given path."""
        target_path = self._normalize_path(path or Path.cwd())
        matches: list[tuple[int, str, dict]] = []

        for name, project_info in self.get_projects().items():
            project_path_value = project_info.get("path")
            if not project_path_value:
                continue

            project_path = self._normalize_path(Path(project_path_value))
            if self._is_same_or_parent(project_path, target_path):
                matches.append((len(project_path.parts), name, project_info))

        if not matches:
            return None

        _, name, project_info = max(matches, key=lambda item: item[0])
        return name, project_info

    def get_active_project_name(self) -> Optional[str]:
        """Get the project selected by the current directory or explicit switch."""
        detected = self.find_project_for_path()
        if detected:
            return detected[0]
        return self.load().get("current_project")

    def add_project(self, name: str, project_info: dict) -> None:
        """Add a new project."""
        config = self.load()
        config["projects"][name] = project_info
        self.save(config)

    def remove_project(self, name: str) -> None:
        """Remove a project."""
        config = self.load()
        if name in config["projects"]:
            del config["projects"][name]
        if config.get("current_project") == name:
            config["current_project"] = None
        self.save(config)

    def set_current_project(self, name: Optional[str]) -> None:
        """Set current project."""
        config = self.load()
        config["current_project"] = name
        self.save(config)

    def get_current_project(self) -> Optional[dict]:
        """Get current project info."""
        current = self.get_active_project_name()
        if current:
            return self.get_project(current)
        return None

    @staticmethod
    def _normalize_path(path: Path) -> Path:
        return path.expanduser().resolve(strict=False)

    @staticmethod
    def _is_same_or_parent(parent: Path, child: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
