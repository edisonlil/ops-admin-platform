from __future__ import annotations

from functools import lru_cache
from typing import Any

from ai_applications.application.sandbox_settings import SandboxSettings, resolve_sandbox_settings
from ai_applications.application.skill_runtime import SkillSandboxRunner, UnavailableSkillSandboxRunner
from ai_applications.infrastructure.sandbox.directory_runner import DirectorySkillSandboxRunner
from ai_applications.infrastructure.sandbox.docker_runner import DockerSkillSandboxRunner


def default_sandbox_runner() -> SkillSandboxRunner:
    settings = resolve_sandbox_settings({})
    if not settings.enabled:
        return UnavailableSkillSandboxRunner()
    return runner_from_settings(settings)


def resolve_request_sandbox_runner(request: dict[str, Any]) -> SkillSandboxRunner:
    settings = resolve_sandbox_settings(request)
    if not settings.enabled:
        return UnavailableSkillSandboxRunner()
    return runner_from_settings(settings)


@lru_cache(maxsize=16)
def _cached_runner(settings: SandboxSettings) -> SkillSandboxRunner:
    if settings.mode == "docker":
        return DockerSkillSandboxRunner(
            image=settings.docker_image,
            docker_binary=settings.docker_binary,
            timeout_seconds=settings.docker_timeout_seconds,
            memory=settings.docker_memory,
            cpus=settings.docker_cpus,
            pids_limit=settings.docker_pids_limit,
            user=settings.docker_user,
            network=settings.docker_network,
        )
    if settings.mode == "directory":
        return DirectorySkillSandboxRunner(
            sandbox_root=settings.directory_root,
            timeout_seconds=settings.directory_timeout_seconds,
            python_binary=settings.directory_python,
            keep_workspace=settings.directory_keep_workspace,
        )
    return UnavailableSkillSandboxRunner()


def runner_from_settings(settings: SandboxSettings) -> SkillSandboxRunner:
    return _cached_runner(settings)


def enrich_sandbox_request(request: dict[str, Any]) -> dict[str, Any]:
    settings = resolve_sandbox_settings(request)
    enriched = dict(request)
    enriched["sandbox_root"] = settings.directory_root
    enriched["sandbox_mode"] = settings.mode
    return enriched
