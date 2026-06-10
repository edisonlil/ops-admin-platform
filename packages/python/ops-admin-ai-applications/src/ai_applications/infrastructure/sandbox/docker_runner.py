from __future__ import annotations

import json
import os
import subprocess
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
import base64
from typing import Any

from ai_applications.application.skill_runtime import SkillRuntimeError


DEFAULT_IMAGE = "python:3.11-slim"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MEMORY = "256m"
DEFAULT_CPUS = "1"
DEFAULT_PIDS_LIMIT = "64"
DEFAULT_USER = "65534:65534"
MAX_STDOUT_CHARS = 200_000
MAX_WORKSPACE_FILES = 120
MAX_WORKSPACE_FILE_BYTES = 5 * 1024 * 1024
INTERNAL_WORKSPACE_NAMES = {"input.json", "output.json", "runner.py"}


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
        network: str = "bridge",
    ) -> None:
        self.image = image
        self.docker_binary = docker_binary
        self.timeout_seconds = max(1, min(300, int(timeout_seconds or DEFAULT_TIMEOUT_SECONDS)))
        self.memory = memory or DEFAULT_MEMORY
        self.cpus = cpus or DEFAULT_CPUS
        self.pids_limit = pids_limit or DEFAULT_PIDS_LIMIT
        self.user = user or DEFAULT_USER
        self.network = network or "bridge"

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
            prepare_skill_package(workspace, request, entrypoint)
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
            return self._run_container(workspace, command, entrypoint=entrypoint, return_workspace_files=return_workspace_files(request))

    def _run_shell(self, request: dict[str, Any]) -> dict[str, Any]:
        entrypoint = safe_entrypoint(request, default_name="main.sh")
        with tempfile.TemporaryDirectory(prefix="ops_skill_sandbox_") as temp_dir:
            workspace = Path(temp_dir)
            write_common_inputs(workspace, request)
            prepare_skill_package(workspace, request, entrypoint)
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
            return self._run_container(workspace, command, entrypoint=entrypoint, return_workspace_files=return_workspace_files(request))

    def _run_container(
        self,
        workspace: Path,
        command: list[str],
        *,
        entrypoint: Path,
        return_workspace_files: bool,
    ) -> dict[str, Any]:
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
            normalized = normalize_runner_output(output_payload)
            if return_workspace_files:
                normalized["output"]["workspace_files"] = collect_workspace_files(workspace, entrypoint=entrypoint)
            return normalized
        output = {"stdout": stdout, "stderr": stderr}
        if return_workspace_files:
            output["workspace_files"] = collect_workspace_files(workspace, entrypoint=entrypoint)
        return {"status": "success", "output": output}


def write_common_inputs(workspace: Path, request: dict[str, Any]) -> None:
    chmod_best_effort(workspace, 0o777)
    input_path = workspace / "input.json"
    runner_path = workspace / "runner.py"
    input_path.write_text(
        json.dumps(request.get("input") if isinstance(request.get("input"), dict) else {}, ensure_ascii=False),
        encoding="utf-8",
    )
    runner_path.write_text(RUNNER_SCRIPT, encoding="utf-8")
    materialize_workspace_files(workspace, request.get("workspace_files") if isinstance(request.get("workspace_files"), list) else [])
    chmod_best_effort(input_path, 0o644)
    chmod_best_effort(runner_path, 0o644)


def prepare_skill_package(workspace: Path, request: dict[str, Any], entrypoint: Path) -> None:
    package_data = str(request.get("package_data_base64") or "")
    if package_data:
        extract_package(workspace, package_data)
    else:
        script_path = workspace / entrypoint
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(str(request.get("content") or ""), encoding="utf-8")
    if not (workspace / entrypoint).exists():
        raise SkillRuntimeError(f"skill sandbox entrypoint not found: {entrypoint.as_posix()}")


def extract_package(workspace: Path, package_data_base64: str) -> None:
    try:
        package_bytes = base64.b64decode(package_data_base64)
    except ValueError as exc:
        raise SkillRuntimeError("skill package payload is not valid base64") from exc
    try:
        with zipfile.ZipFile(BytesIO(package_bytes)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                path = safe_archive_path(info.filename)
                target = workspace / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
                chmod_best_effort(target, 0o755 if path.suffix in {".sh", ".py"} else 0o644)
    except zipfile.BadZipFile as exc:
        raise SkillRuntimeError("skill package payload is not a valid ZIP archive") from exc


def safe_archive_path(name: str) -> Path:
    normalized = str(name or "").replace("\\", "/").strip("/")
    path = Path(normalized)
    if not normalized or any(part in {"", ".", ".."} or ":" in part for part in path.parts):
        raise SkillRuntimeError("skill package contains unsafe path")
    return Path(*path.parts)


def materialize_workspace_files(workspace: Path, files: list[Any]) -> None:
    for item in files[:MAX_WORKSPACE_FILES]:
        if not isinstance(item, dict):
            continue
        raw_path = str(item.get("path") or "").strip()
        content = item.get("content")
        encoded_payload = item.get("base64")
        if not raw_path or (not isinstance(content, str) and not isinstance(encoded_payload, str)):
            continue
        path = safe_archive_path(raw_path)
        if path.name in INTERNAL_WORKSPACE_NAMES or path.parts[0] == ".skill_deps":
            continue
        if isinstance(encoded_payload, str):
            try:
                data = base64.b64decode(encoded_payload)
            except ValueError:
                continue
        else:
            data = content.encode("utf-8")
        if len(data) > MAX_WORKSPACE_FILE_BYTES:
            continue
        target = workspace / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        chmod_best_effort(target, 0o644)


def return_workspace_files(request: dict[str, Any]) -> bool:
    value = request.get("return_workspace_files")
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def collect_workspace_files(workspace: Path, *, entrypoint: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    root = workspace.resolve()
    entrypoint_posix = entrypoint.as_posix()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        if relative == entrypoint_posix or path.name in INTERNAL_WORKSPACE_NAMES or relative.startswith(".skill_deps/"):
            continue
        if path.stat().st_size > MAX_WORKSPACE_FILE_BYTES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        files.append({"path": relative, "content": content})
        if len(files) >= MAX_WORKSPACE_FILES:
            break
    return files


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
        network=os.environ.get("OPS_ADMIN_SKILL_SANDBOX_NETWORK", "bridge").strip() or "bridge",
    )


RUNNER_SCRIPT = r'''
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
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
    install_requirements()
    workspace_dir = os.path.dirname(os.path.abspath(args.script)) if args.script else os.getcwd()
    if workspace_dir and workspace_dir not in sys.path:
        sys.path.insert(0, workspace_dir)
    if workspace_dir:
        os.chdir(workspace_dir)
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


def install_requirements() -> None:
    for candidate in ("requirements.txt", "scripts/requirements.txt"):
        if not os.path.exists(candidate):
            continue
        target = "/workspace/.skill_deps"
        os.makedirs(target, exist_ok=True)
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--target", target, "-r", candidate],
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "pip install failed")
        if target not in sys.path:
            sys.path.insert(0, target)
        return


if __name__ == "__main__":
    sys.exit(main())
'''
