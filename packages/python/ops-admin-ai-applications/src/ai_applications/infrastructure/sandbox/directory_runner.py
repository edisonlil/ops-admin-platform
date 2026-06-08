"""DirectorySkillSandboxRunner — 本地目录沙箱执行器

每次 Skill 执行都在宿主机本地一个独立的子目录中运行。执行进程在该目录内
启动，所有文件操作（读、写）均被约定限制在该目录范围内。

重要安全说明
------------
本执行器**不提供操作系统级进程隔离**。脚本代码在 FastAPI 服务进程的同一
用户权限下运行，理论上可以访问宿主机其他路径。仅适合：
  - 受信任的内部开发/调试环境
  - 脚本代码本身可信的场景

如需生产级隔离，请使用 DockerSkillSandboxRunner。

配置（环境变量）
----------------
OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED        = true
OPS_ADMIN_SKILL_DIR_SANDBOX_ROOT           = /opt/skill-workspaces   （默认 .tmp/skill-sandboxes）
OPS_ADMIN_SKILL_DIR_SANDBOX_TIMEOUT_SECONDS = 60
OPS_ADMIN_SKILL_DIR_SANDBOX_PYTHON         = python3                 （默认 python）
OPS_ADMIN_SKILL_DIR_SANDBOX_KEEP_WORKSPACE = false                   （调试时设为 true 保留目录）
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from ai_applications.application.skill_runtime import SkillRuntimeError
from ai_applications.infrastructure.sandbox.docker_runner import (
    MAX_STDOUT_CHARS,
    MAX_WORKSPACE_FILE_BYTES,
    MAX_WORKSPACE_FILES,
    INTERNAL_WORKSPACE_NAMES,
    RUNNER_SCRIPT,
    collect_workspace_files,
    extract_package,
    normalize_runner_output,
    read_output,
    return_workspace_files,
    safe_entrypoint,
    write_common_inputs,
    prepare_skill_package,
)


DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_PYTHON = "python"
DEFAULT_SANDBOX_ROOT = ".tmp/skill-sandboxes"


class DirectorySkillSandboxRunner:
    """在本地目录工作空间中运行 Skill 脚本。

    每次调用 :meth:`run` 时创建一个隔离子目录（``<root>/<tenant>/<skill>/<run_id>``），
    脚本在该目录内执行，执行完成后根据 ``keep_workspace`` 配置决定是否清理。
    """

    def __init__(
        self,
        *,
        sandbox_root: str | Path | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        python_binary: str = DEFAULT_PYTHON,
        keep_workspace: bool = False,
    ) -> None:
        raw_root = sandbox_root or DEFAULT_SANDBOX_ROOT
        self.sandbox_root = Path(raw_root)
        self.timeout_seconds = max(1, min(600, int(timeout_seconds or DEFAULT_TIMEOUT_SECONDS)))
        self.python_binary = python_binary or DEFAULT_PYTHON
        self.keep_workspace = bool(keep_workspace)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        runtime_kind = str(request.get("runtime_kind") or "").strip().lower()
        if runtime_kind in {"sandbox_shell", "shell"}:
            return self._run_shell(request)
        return self._run_python(request)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sandbox_root(self, request: dict[str, Any]) -> Path:
        override = str(request.get("sandbox_root") or "").strip()
        return Path(override) if override else self.sandbox_root

    def _allocate_workspace(self, request: dict[str, Any]) -> tuple[Path, bool]:
        """返回 (workspace, should_cleanup)。"""
        conversation_workspace = str(request.get("conversation_workspace") or "").strip()
        if conversation_workspace:
            workspace = Path(conversation_workspace)
            workspace.mkdir(parents=True, exist_ok=True)
            return workspace, False
        tenant_part = _safe_dir_part(f"tenant_{request.get('tenant_id') or 0}", fallback="tenant_0")
        skill_part = _safe_dir_part(request.get("skill_key") or "skill", fallback="skill")
        conversation_part = _safe_dir_part(request.get("conversation_key"), fallback="")
        run_id = uuid.uuid4().hex
        parts = [tenant_part, skill_part]
        if conversation_part:
            parts.append(conversation_part)
        parts.append(run_id)
        workspace = self._sandbox_root(request).joinpath(*parts)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace, not self.keep_workspace

    def _run_python(self, request: dict[str, Any]) -> dict[str, Any]:
        entrypoint = safe_entrypoint(request, default_name="main.py")
        workspace, should_cleanup = self._allocate_workspace(request)
        try:
            write_common_inputs(workspace, request)
            prepare_skill_package(workspace, request, entrypoint)
            command = [
                self.python_binary,
                str(workspace / "runner.py"),
                "--script",
                str(workspace / entrypoint),
                "--input",
                str(workspace / "input.json"),
                "--output",
                str(workspace / "output.json"),
            ]
            return self._run_process(workspace, command, entrypoint=entrypoint, request=request)
        finally:
            if should_cleanup:
                _rmtree_best_effort(workspace)

    def _run_shell(self, request: dict[str, Any]) -> dict[str, Any]:
        entrypoint = safe_entrypoint(request, default_name="main.sh")
        workspace, should_cleanup = self._allocate_workspace(request)
        try:
            write_common_inputs(workspace, request)
            prepare_skill_package(workspace, request, entrypoint)
            command = [
                self.python_binary,
                str(workspace / "runner.py"),
                "--shell",
                str(workspace / entrypoint),
                "--input",
                str(workspace / "input.json"),
                "--output",
                str(workspace / "output.json"),
            ]
            return self._run_process(workspace, command, entrypoint=entrypoint, request=request)
        finally:
            if should_cleanup:
                _rmtree_best_effort(workspace)

    def _run_process(
        self,
        workspace: Path,
        command: list[str],
        *,
        entrypoint: Path,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            # 让脚本知道自己的工作目录，但不做强制约束
            "OPS_SKILL_WORKSPACE": str(workspace.resolve()),
        }
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                encoding="utf-8",
                errors="replace",
                cwd=str(workspace),
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise SkillRuntimeError(
                f"skill sandbox timed out after {self.timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise SkillRuntimeError(
                f"skill directory sandbox failed to start process: {exc}"
            ) from exc

        stdout = (completed.stdout or "")[:MAX_STDOUT_CHARS]
        stderr = (completed.stderr or "")[:MAX_STDOUT_CHARS]
        output_path = workspace / "output.json"
        output_payload = read_output(output_path)
        if completed.returncode != 0:
            raise SkillRuntimeError(
                output_payload.get("error_message")
                or stderr.strip()
                or stdout.strip()
                or f"skill sandbox exited with code {completed.returncode}"
            )
        need_files = return_workspace_files(request)
        if output_payload:
            normalized = normalize_runner_output(output_payload)
            if need_files:
                normalized["output"]["workspace_files"] = collect_workspace_files(
                    workspace, entrypoint=entrypoint
                )
            return normalized
        output: dict[str, Any] = {"stdout": stdout, "stderr": stderr}
        if need_files:
            output["workspace_files"] = collect_workspace_files(workspace, entrypoint=entrypoint)
        return {"status": "success", "output": output}


# ------------------------------------------------------------------
# Factory / env configuration
# ------------------------------------------------------------------


def configured_directory_runner_from_env() -> DirectorySkillSandboxRunner | None:
    """从环境变量读取配置，返回 runner 实例；未启用时返回 None。"""
    enabled = os.environ.get("OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED", "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return None
    raw_root = os.environ.get("OPS_ADMIN_SKILL_DIR_SANDBOX_ROOT", "").strip()
    timeout = int(os.environ.get("OPS_ADMIN_SKILL_DIR_SANDBOX_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    python_bin = os.environ.get("OPS_ADMIN_SKILL_DIR_SANDBOX_PYTHON", DEFAULT_PYTHON).strip() or DEFAULT_PYTHON
    keep_raw = os.environ.get("OPS_ADMIN_SKILL_DIR_SANDBOX_KEEP_WORKSPACE", "").strip().lower()
    keep = keep_raw in {"1", "true", "yes", "on"}
    return DirectorySkillSandboxRunner(
        sandbox_root=raw_root or None,
        timeout_seconds=timeout,
        python_binary=python_bin,
        keep_workspace=keep,
    )


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------


def _safe_dir_part(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)
    cleaned = cleaned.strip("._-")[:80]
    return cleaned or fallback


def _rmtree_best_effort(path: Path) -> None:
    try:
        shutil.rmtree(path)
    except OSError:
        pass
