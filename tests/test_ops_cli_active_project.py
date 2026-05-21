from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPS_CLI_ROOT = ROOT / "ops-cli"
sys.path.insert(0, str(OPS_CLI_ROOT))

from ops_cli.config import Config


def add_project(config: Config, name: str, path: Path) -> None:
    config.add_project(
        name,
        {
            "path": str(path),
            "branch": "main",
            "modules": [],
            "created_at": "2026-05-21T00:00:00",
        },
    )


def test_find_project_for_path_matches_child_directory(tmp_path: Path) -> None:
    config = Config(tmp_path / "config.json")
    project_path = tmp_path / "projects" / "alpha"
    child_path = project_path / "web" / "admin"
    child_path.mkdir(parents=True)
    add_project(config, "alpha", project_path)

    detected = config.find_project_for_path(child_path)

    assert detected is not None
    assert detected[0] == "alpha"


def test_find_project_for_path_prefers_longest_project_path(tmp_path: Path) -> None:
    config = Config(tmp_path / "config.json")
    parent_path = tmp_path / "projects"
    child_path = parent_path / "alpha"
    nested_path = child_path / "api"
    nested_path.mkdir(parents=True)
    add_project(config, "parent", parent_path)
    add_project(config, "alpha", child_path)

    detected = config.find_project_for_path(nested_path)

    assert detected is not None
    assert detected[0] == "alpha"


def test_current_project_uses_working_directory_before_switched_project(tmp_path: Path, monkeypatch) -> None:
    config = Config(tmp_path / "config.json")
    alpha_path = tmp_path / "alpha"
    beta_path = tmp_path / "beta"
    child_path = alpha_path / "api"
    child_path.mkdir(parents=True)
    beta_path.mkdir()
    add_project(config, "alpha", alpha_path)
    add_project(config, "beta", beta_path)
    config.set_current_project("beta")
    monkeypatch.chdir(child_path)

    assert config.get_active_project_name() == "alpha"
    assert config.get_current_project()["path"] == str(alpha_path)


def test_current_project_falls_back_to_switched_project(tmp_path: Path, monkeypatch) -> None:
    config = Config(tmp_path / "config.json")
    project_path = tmp_path / "alpha"
    outside_path = tmp_path / "outside"
    project_path.mkdir()
    outside_path.mkdir()
    add_project(config, "alpha", project_path)
    config.set_current_project("alpha")
    monkeypatch.chdir(outside_path)

    assert config.get_active_project_name() == "alpha"
    assert config.get_current_project()["path"] == str(project_path)
