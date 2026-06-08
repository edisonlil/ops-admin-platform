"""Skill sandbox 配置解析。

配置优先级（高 → 低）：
1. 环境变量（OPS_ADMIN_SKILL_* / OPS_ADMIN_SKILL_DIR_*）
2. 单次请求中的应用级覆盖（runtime_config.sandbox 或 app_runtime_config.sandbox）
3. 平台 config/application.json → ai_applications.skill_sandbox
4. 内置默认值
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from system.application.config import config_bool, config_string, load_application_config, section_config


DEFAULT_DIRECTORY_ROOT = ".tmp/skill-sandboxes"
DEFAULT_AGENT_WORKSPACE_ROOT = ".tmp/ai-agent-workspaces"
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"
DEFAULT_DIRECTORY_TIMEOUT = 60
DEFAULT_DOCKER_TIMEOUT = 30


@dataclass(frozen=True, slots=True)
class SandboxSettings:
    mode: str  # "docker" | "directory" | "disabled"
    directory_root: str = DEFAULT_DIRECTORY_ROOT
    directory_timeout_seconds: int = DEFAULT_DIRECTORY_TIMEOUT
    directory_python: str = "python"
    directory_keep_workspace: bool = False
    docker_image: str = DEFAULT_DOCKER_IMAGE
    docker_binary: str = "docker"
    docker_timeout_seconds: int = DEFAULT_DOCKER_TIMEOUT
    docker_memory: str = "256m"
    docker_cpus: str = "1"
    docker_pids_limit: str = "64"
    docker_user: str = "65534:65534"
    docker_network: str = "bridge"
    agent_workspace_root: str = DEFAULT_AGENT_WORKSPACE_ROOT

    @property
    def enabled(self) -> bool:
        return self.mode in {"docker", "directory"}


def platform_sandbox_config() -> dict[str, Any]:
    app_config = load_application_config()
    ai_apps = section_config(app_config, "ai_applications")
    sandbox = ai_apps.get("skill_sandbox")
    return sandbox if isinstance(sandbox, dict) else {}


def resolve_default_sandbox_settings() -> SandboxSettings:
    return resolve_sandbox_settings({})


def resolve_sandbox_settings(request: dict[str, Any]) -> SandboxSettings:
    platform = platform_sandbox_config()
    override = request_sandbox_override(request)
    return _merge_settings(platform, override)


def resolve_agent_workspace_root(app: dict[str, Any] | None = None) -> str:
    """解析 Agent 文件工作空间根目录。"""
    env_root = os.environ.get("OPS_ADMIN_AGENT_WORKSPACE_ROOT", "").strip()
    if env_root:
        return env_root

    if isinstance(app, dict):
        runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
        sandbox = runtime_config.get("sandbox") if isinstance(runtime_config.get("sandbox"), dict) else {}
        agent = runtime_config.get("agent") if isinstance(runtime_config.get("agent"), dict) else {}
        for source in (sandbox, agent):
            root = config_string(source, "workspace_root", "root")
            if root:
                return root

    platform = platform_sandbox_config()
    agent_workspace = platform.get("agent_workspace")
    if isinstance(agent_workspace, dict):
        root = config_string(agent_workspace, "root")
        if root:
            return root

    return DEFAULT_AGENT_WORKSPACE_ROOT


def request_sandbox_override(request: dict[str, Any]) -> dict[str, Any]:
    for key in ("runtime_config", "app_runtime_config"):
        container = request.get(key)
        if not isinstance(container, dict):
            continue
        sandbox = container.get("sandbox")
        if isinstance(sandbox, dict):
            return sandbox
    direct = request.get("sandbox")
    return direct if isinstance(direct, dict) else {}


def _merge_settings(platform: dict[str, Any], override: dict[str, Any]) -> SandboxSettings:
    directory = _section(platform, "directory")
    docker = _section(platform, "docker")
    directory = {**directory, **{k: v for k, v in _section(override, "directory").items() if v is not None}}
    docker = {**docker, **{k: v for k, v in _section(override, "docker").items() if v is not None}}
    merged_override = {**override}
    merged_override.pop("directory", None)
    merged_override.pop("docker", None)

    mode = _resolve_mode(platform, override, merged_override)
    agent_workspace = _section(platform, "agent_workspace")
    agent_root = (
        config_string(override, "workspace_root", "root")
        or config_string(_section(override, "agent_workspace"), "root")
        or config_string(agent_workspace, "root")
        or DEFAULT_AGENT_WORKSPACE_ROOT
    )

    return SandboxSettings(
        mode=mode,
        directory_root=_env_or_config(
            "OPS_ADMIN_SKILL_DIR_SANDBOX_ROOT",
            config_string(merged_override, "root")
            or config_string(override, "root")
            or config_string(directory, "root"),
            DEFAULT_DIRECTORY_ROOT,
        ),
        directory_timeout_seconds=_env_int(
            "OPS_ADMIN_SKILL_DIR_SANDBOX_TIMEOUT_SECONDS",
            directory.get("timeout_seconds"),
            DEFAULT_DIRECTORY_TIMEOUT,
        ),
        directory_python=_env_or_config(
            "OPS_ADMIN_SKILL_DIR_SANDBOX_PYTHON",
            config_string(directory, "python"),
            "python",
        ),
        directory_keep_workspace=_env_bool(
            "OPS_ADMIN_SKILL_DIR_SANDBOX_KEEP_WORKSPACE",
            config_bool(directory, "keep_workspace"),
            False,
        ),
        docker_image=_env_or_config(
            "OPS_ADMIN_SKILL_SANDBOX_IMAGE",
            config_string(docker, "image"),
            DEFAULT_DOCKER_IMAGE,
        ),
        docker_binary=_env_or_config(
            "OPS_ADMIN_SKILL_SANDBOX_DOCKER_BIN",
            config_string(docker, "docker_binary", "binary"),
            "docker",
        ),
        docker_timeout_seconds=_env_int(
            "OPS_ADMIN_SKILL_SANDBOX_TIMEOUT_SECONDS",
            docker.get("timeout_seconds"),
            DEFAULT_DOCKER_TIMEOUT,
        ),
        docker_memory=_env_or_config(
            "OPS_ADMIN_SKILL_SANDBOX_MEMORY",
            config_string(docker, "memory"),
            "256m",
        ),
        docker_cpus=_env_or_config(
            "OPS_ADMIN_SKILL_SANDBOX_CPUS",
            config_string(docker, "cpus"),
            "1",
        ),
        docker_pids_limit=_env_or_config(
            "OPS_ADMIN_SKILL_SANDBOX_PIDS_LIMIT",
            config_string(docker, "pids_limit"),
            "64",
        ),
        docker_user=_env_or_config(
            "OPS_ADMIN_SKILL_SANDBOX_USER",
            config_string(docker, "user"),
            "65534:65534",
        ),
        docker_network=_env_or_config(
            "OPS_ADMIN_SKILL_SANDBOX_NETWORK",
            config_string(docker, "network"),
            "bridge",
        ),
        agent_workspace_root=agent_root,
    )


def _resolve_mode(platform: dict[str, Any], override: dict[str, Any], flat_override: dict[str, Any]) -> str:
    docker_env = _env_enabled("OPS_ADMIN_SKILL_SANDBOX_ENABLED")
    directory_env = _env_enabled("OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED")
    if docker_env is True:
        return "docker"
    if directory_env is True:
        return "directory"
    if docker_env is False and directory_env is False:
        return "disabled"

    for source in (flat_override, override, platform):
        raw_mode = config_string(source, "mode", "type")
        if raw_mode in {"docker", "directory", "disabled", "none", "off"}:
            return "directory" if raw_mode == "directory" else ("disabled" if raw_mode in {"disabled", "none", "off"} else "docker")
        enabled = config_bool(source, "enabled")
        if enabled is True:
            docker_enabled = config_bool(_section(source, "docker"), "enabled")
            directory_enabled = config_bool(_section(source, "directory"), "enabled")
            if docker_enabled is True:
                return "docker"
            if directory_enabled is True:
                return "directory"
            return config_string(source, "mode", "type") or "directory"
        if enabled is False:
            return "disabled"

    docker_cfg = _section(platform, "docker")
    directory_cfg = _section(platform, "directory")
    if config_bool(docker_cfg, "enabled") is True:
        return "docker"
    if config_bool(directory_cfg, "enabled") is True:
        return "directory"
    if config_string(platform, "mode", "type") in {"docker", "directory"}:
        return config_string(platform, "mode", "type")
    return "disabled"


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    section = config.get(name)
    return section if isinstance(section, dict) else {}


def _env_or_config(env_key: str, config_value: str, default: str) -> str:
    env_value = os.environ.get(env_key, "").strip()
    if env_value:
        return env_value
    if config_value:
        return config_value
    return default


def _env_int(env_key: str, config_value: Any, default: int) -> int:
    env_value = os.environ.get(env_key, "").strip()
    if env_value:
        try:
            return max(1, int(env_value))
        except ValueError:
            return default
    if config_value is not None:
        try:
            return max(1, int(config_value))
        except (TypeError, ValueError):
            return default
    return default


def _env_bool(env_key: str, config_value: bool | None, default: bool) -> bool:
    env_value = os.environ.get(env_key, "").strip().lower()
    if env_value in {"1", "true", "yes", "on"}:
        return True
    if env_value in {"0", "false", "no", "off"}:
        return False
    if config_value is not None:
        return config_value
    return default


def _env_enabled(env_key: str) -> bool | None:
    env_value = os.environ.get(env_key, "").strip().lower()
    if env_value in {"1", "true", "yes", "on"}:
        return True
    if env_value in {"0", "false", "no", "off"}:
        return False
    return None
