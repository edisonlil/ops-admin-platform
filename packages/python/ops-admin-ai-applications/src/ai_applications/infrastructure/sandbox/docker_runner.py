from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ai_applications.application.skill_runtime import SkillRuntimeError


DEFAULT_IMAGE = "python:3.11-slim"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MEMORY = "256m"
DEFAULT_CPUS = "1"
DEFAULT_PIDS_LIMIT = "64"
DEFAULT_USER = "65534:65534"
MAX_STDOUT_CHARS = 200_000


class DockerSkillSandboxRunner:
    def __init__(
        self,
        *,
        image: str = DEFAULT_IMAGE,
        docker_binary: str = "docker",
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        memory: str = DEFAULT_MEMORY,
        cpus: str = DEFAULT_CPUS,
        pids_limit: str = DEFAULT_PIDS_LIMIT,
        user: str = DEFAULT_USER,
        network: str = "none",
    ) -> None:
        self.image = image
        self.docker_binary = docker_binary
        self.timeout_seconds = max(1, min(300, int(timeout_seconds or DEFAULT_TIMEOUT_SECONDS)))
        self.memory = memory or DEFAULT_MEMORY
        self.cpus = cpus or DEFAULT_CPUS
        self.pids_limit = pids_limit or DEFAULT_PIDS_LIMIT
        self.user = user or DEFAULT_USER
        self.network = network or "none"

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        runtime_kind = str(request.get("runtime_kind") or "").strip().lower()
        if runtime_kind in {"sandbox_shell", "shell"}:
            return self._run_shell(request)
        return self._run_python(request)

    def _run_python(self, request: dict[str, Any]) -> dict[str, Any]:
        entrypoint = safe_entrypoint(request, default_name="main.py")
        with tempfile.TemporaryDirectory(prefix="ops_skill_sandbox_") as temp_dir:
            workspace = Path(temp_dir)
            write_common_inputs(workspace, request)
            script_path = workspace / entrypoint
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(str(request.get("content") or ""), encoding="utf-8")
            command = [
                "python",
                "/workspace/runner.py",
                "--script",
                f"/workspace/{entrypoint.as_posix()}",
                "--input",
                "/workspace/input.json",
                "--output",
                "/workspace/output.json",
            ]
            return self._run_container(workspace, command)

    def _run_shell(self, request: dict[str, Any]) -> dict[str, Any]:
        entrypoint = safe_entrypoint(request, default_name="main.sh")
        with tempfile.TemporaryDirectory(prefix="ops_skill_sandbox_") as temp_dir:
            workspace = Path(temp_dir)
            write_common_inputs(workspace, request)
            script_path = workspace / entrypoint
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(str(request.get("content") or ""), encoding="utf-8")
            command = [
                "python",
                "/workspace/runner.py",
                "--shell",
                f"/workspace/{entrypoint.as_posix()}",
                "--input",
                "/workspace/input.json",
                "--output",
                "/workspace/output.json",
            ]
            return self._run_container(workspace, command)

    def _run_container(self, workspace: Path, command: list[str]) -> dict[str, Any]:
        docker_command = [
            self.docker_binary,
            "run",
            "--rm",
            "--network",
            self.network,
            "--cpus",
            self.cpus,
            "--memory",
            self.memory,
            "--pids-limit",
            self.pids_limit,
            "--user",
            self.user,
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--security-opt",
            "no-new-privileges",
            "--cap-drop",
            "ALL",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-v",
            f"{workspace.resolve()}:/workspace:rw",
            "-w",
            "/workspace",
            self.image,
            *command,
        ]
        try:
            completed = subprocess.run(
                docker_command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as exc:
            raise SkillRuntimeError(f"skill sandbox timed out after {self.timeout_seconds}s") from exc
        except OSError as exc:
            raise SkillRuntimeError(f"skill sandbox runner failed to start: {exc}") from exc

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
        if output_payload:
            return normalize_runner_output(output_payload)
        return {"status": "success", "output": {"stdout": stdout, "stderr": stderr}}


def write_common_inputs(workspace: Path, request: dict[str, Any]) -> None:
    chmod_best_effort(workspace, 0o777)
    input_path = workspace / "input.json"
    runner_path = workspace / "runner.py"
    input_path.write_text(
        json.dumps(request.get("input") if isinstance(request.get("input"), dict) else {}, ensure_ascii=False),
        encoding="utf-8",
    )
    runner_path.write_text(RUNNER_SCRIPT, encoding="utf-8")
    chmod_best_effort(input_path, 0o644)
    chmod_best_effort(runner_path, 0o644)


def safe_entrypoint(request: dict[str, Any], *, default_name: str) -> Path:
    raw = str(request.get("entrypoint") or request.get("runtime_config", {}).get("entrypoint") or default_name).strip()
    normalized = raw.replace("\\", "/").lstrip("/")
    path = Path(normalized)
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise SkillRuntimeError("skill sandbox entrypoint path is unsafe")
    return Path(*parts)


def read_output(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillRuntimeError(f"skill sandbox output is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SkillRuntimeError("skill sandbox output must be a JSON object")
    return value


def chmod_best_effort(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        return


def normalize_runner_output(payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "success")
    if status != "success":
        raise SkillRuntimeError(str(payload.get("error_message") or "skill sandbox failed"))
    output = payload.get("output")
    return {"status": "success", "output": output if isinstance(output, dict) else {"result": output}}


def configured_runner_from_env() -> DockerSkillSandboxRunner | None:
    enabled = os.environ.get("OPS_ADMIN_SKILL_SANDBOX_ENABLED", "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return None
    return DockerSkillSandboxRunner(
        image=os.environ.get("OPS_ADMIN_SKILL_SANDBOX_IMAGE", DEFAULT_IMAGE).strip() or DEFAULT_IMAGE,
        docker_binary=os.environ.get("OPS_ADMIN_SKILL_SANDBOX_DOCKER_BIN", "docker").strip() or "docker",
        timeout_seconds=int(os.environ.get("OPS_ADMIN_SKILL_SANDBOX_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
        memory=os.environ.get("OPS_ADMIN_SKILL_SANDBOX_MEMORY", DEFAULT_MEMORY).strip() or DEFAULT_MEMORY,
        cpus=os.environ.get("OPS_ADMIN_SKILL_SANDBOX_CPUS", DEFAULT_CPUS).strip() or DEFAULT_CPUS,
        pids_limit=os.environ.get("OPS_ADMIN_SKILL_SANDBOX_PIDS_LIMIT", DEFAULT_PIDS_LIMIT).strip() or DEFAULT_PIDS_LIMIT,
        user=os.environ.get("OPS_ADMIN_SKILL_SANDBOX_USER", DEFAULT_USER).strip() or DEFAULT_USER,
        network=os.environ.get("OPS_ADMIN_SKILL_SANDBOX_NETWORK", "none").strip() or "none",
    )


RUNNER_SCRIPT = r'''
from __future__ import annotations

import argparse
import contextlib
import io
import json
import runpy
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script")
    parser.add_argument("--shell")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.input, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if args.shell:
        completed = subprocess.run(
            ["sh", args.shell],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
        write_output(args.output, {
            "status": "success" if completed.returncode == 0 else "failed",
            "output": {"stdout": completed.stdout, "stderr": completed.stderr, "returncode": completed.returncode},
            "error_message": completed.stderr.strip(),
        })
        return completed.returncode
    buffer = io.StringIO()
    namespace = {"input": payload, "result": None}
    try:
        with contextlib.redirect_stdout(buffer):
            namespace.update(runpy.run_path(args.script, init_globals=namespace))
    except Exception as exc:
        write_output(args.output, {
            "status": "failed",
            "output": {"stdout": buffer.getvalue()},
            "error_message": str(exc),
        })
        return 1
    result = namespace.get("result")
    if result is None:
        result = {"stdout": buffer.getvalue()}
    write_output(args.output, {"status": "success", "output": result})
    return 0


def write_output(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
'''
