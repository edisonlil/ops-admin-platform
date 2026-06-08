from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_applications.application.sandbox_settings import (
    resolve_agent_workspace_root,
    resolve_default_sandbox_settings,
    resolve_sandbox_settings,
)
from ai_applications.infrastructure.sandbox.factory import (
    default_sandbox_runner,
    resolve_request_sandbox_runner,
    runner_from_settings,
)
from ai_applications.infrastructure.sandbox.directory_runner import DirectorySkillSandboxRunner
from ai_applications.infrastructure.sandbox.docker_runner import DockerSkillSandboxRunner


def _write_application_config(tmp_path: Path, payload: dict) -> str:
    config_path = tmp_path / "application.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return str(config_path)


def test_resolve_sandbox_settings_from_application_json(monkeypatch, tmp_path) -> None:
    config_path = _write_application_config(
        tmp_path,
        {
            "ai_applications": {
                "skill_sandbox": {
                    "mode": "directory",
                    "directory": {
                        "root": ".tmp/config-sandboxes",
                        "timeout_seconds": 45,
                        "python": "python3",
                        "keep_workspace": True,
                    },
                    "agent_workspace": {"root": ".tmp/config-agent-workspaces"},
                }
            }
        },
    )
    monkeypatch.setenv("OPS_ADMIN_APPLICATION_CONFIG", config_path)
    for key in (
        "OPS_ADMIN_SKILL_SANDBOX_ENABLED",
        "OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED",
        "OPS_ADMIN_AGENT_WORKSPACE_ROOT",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = resolve_default_sandbox_settings()

    assert settings.mode == "directory"
    assert settings.directory_root == ".tmp/config-sandboxes"
    assert settings.directory_timeout_seconds == 45
    assert settings.directory_python == "python3"
    assert settings.directory_keep_workspace is True
    assert settings.agent_workspace_root == ".tmp/config-agent-workspaces"


def test_env_overrides_application_json(monkeypatch, tmp_path) -> None:
    config_path = _write_application_config(
        tmp_path,
        {"ai_applications": {"skill_sandbox": {"mode": "directory"}}},
    )
    monkeypatch.setenv("OPS_ADMIN_APPLICATION_CONFIG", config_path)
    monkeypatch.setenv("OPS_ADMIN_SKILL_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("OPS_ADMIN_SKILL_SANDBOX_IMAGE", "sandbox:from-env")

    settings = resolve_default_sandbox_settings()

    assert settings.mode == "docker"
    assert settings.docker_image == "sandbox:from-env"


def test_request_runtime_config_overrides_platform_defaults(monkeypatch, tmp_path) -> None:
    config_path = _write_application_config(
        tmp_path,
        {
            "ai_applications": {
                "skill_sandbox": {
                    "mode": "docker",
                    "directory": {"root": ".tmp/platform-sandboxes"},
                }
            }
        },
    )
    monkeypatch.setenv("OPS_ADMIN_APPLICATION_CONFIG", config_path)
    monkeypatch.delenv("OPS_ADMIN_SKILL_SANDBOX_ENABLED", raising=False)
    monkeypatch.delenv("OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED", raising=False)

    settings = resolve_sandbox_settings(
        {
            "runtime_config": {
                "sandbox": {
                    "mode": "directory",
                    "root": ".tmp/app-sandboxes",
                }
            }
        }
    )

    assert settings.mode == "directory"
    assert settings.directory_root == ".tmp/app-sandboxes"


def test_resolve_agent_workspace_root_prefers_env_then_app_then_platform(monkeypatch, tmp_path) -> None:
    config_path = _write_application_config(
        tmp_path,
        {"ai_applications": {"skill_sandbox": {"agent_workspace": {"root": ".tmp/platform-agent"}}}},
    )
    monkeypatch.setenv("OPS_ADMIN_APPLICATION_CONFIG", config_path)
    monkeypatch.delenv("OPS_ADMIN_AGENT_WORKSPACE_ROOT", raising=False)

    app = {"runtime_config": {"sandbox": {"workspace_root": ".tmp/app-agent"}}}
    assert resolve_agent_workspace_root(app) == ".tmp/app-agent"

    monkeypatch.setenv("OPS_ADMIN_AGENT_WORKSPACE_ROOT", ".tmp/env-agent")
    assert resolve_agent_workspace_root(app) == ".tmp/env-agent"


def test_factory_builds_directory_runner_from_settings() -> None:
    settings = resolve_sandbox_settings(
        {"runtime_config": {"sandbox": {"mode": "directory", "root": ".tmp/factory-sandboxes"}}}
    )
    runner = runner_from_settings(settings)
    assert isinstance(runner, DirectorySkillSandboxRunner)
    assert runner.sandbox_root == Path(".tmp/factory-sandboxes")


def test_factory_builds_docker_runner_from_settings() -> None:
    settings = resolve_sandbox_settings({"runtime_config": {"sandbox": {"mode": "docker"}}})
    runner = runner_from_settings(settings)
    assert isinstance(runner, DockerSkillSandboxRunner)


def test_default_sandbox_runner_disabled_without_config(monkeypatch) -> None:
    monkeypatch.delenv("OPS_ADMIN_APPLICATION_CONFIG", raising=False)
    monkeypatch.delenv("OPS_ADMIN_SKILL_SANDBOX_ENABLED", raising=False)
    monkeypatch.delenv("OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED", raising=False)
    monkeypatch.setenv("OPS_ADMIN_APPLICATION_CONFIG", str(Path("missing-application.json")))

    from ai_applications.application.skill_runtime import UnavailableSkillSandboxRunner

    runner = default_sandbox_runner()
    assert isinstance(runner, UnavailableSkillSandboxRunner)


def test_resolve_request_sandbox_runner_uses_app_runtime_config(monkeypatch, tmp_path) -> None:
    config_path = _write_application_config(tmp_path, {"ai_applications": {"skill_sandbox": {"mode": "disabled"}}})
    monkeypatch.setenv("OPS_ADMIN_APPLICATION_CONFIG", config_path)
    monkeypatch.delenv("OPS_ADMIN_SKILL_SANDBOX_ENABLED", raising=False)
    monkeypatch.delenv("OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED", raising=False)

    runner = resolve_request_sandbox_runner(
        {
            "app_runtime_config": {
                "sandbox": {
                    "mode": "directory",
                    "root": ".tmp/request-sandboxes",
                }
            }
        }
    )

    assert isinstance(runner, DirectorySkillSandboxRunner)
