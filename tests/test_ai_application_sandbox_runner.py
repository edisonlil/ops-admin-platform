from __future__ import annotations

import base64
import json
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from ai_applications.application.skill_runtime import SkillRuntimeError
from ai_applications.infrastructure.sandbox.docker_runner import DockerSkillSandboxRunner
from ai_applications.infrastructure.sandbox.docker_runner import configured_runner_from_env


class Completed:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_docker_skill_sandbox_runner_uses_locked_down_container(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        volume = command[command.index("-v") + 1]
        workspace = volume.rsplit(":/workspace:rw", 1)[0]
        with open(f"{workspace}/output.json", "w", encoding="utf-8") as handle:
            json.dump({"status": "success", "output": {"answer": "ok"}}, handle)
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DockerSkillSandboxRunner(image="sandbox:local", timeout_seconds=9)

    result = runner.run(
        {
            "runtime_kind": "sandbox_python",
            "entrypoint": "main.py",
            "content": "result = {'answer': input['name']}",
            "input": {"name": "ok"},
        }
    )

    command = captured["command"]
    assert result == {"status": "success", "output": {"answer": "ok"}}
    assert command[:3] == ["docker", "run", "--rm"]
    assert command[command.index("--network") + 1] == "bridge"
    assert command[command.index("--memory") + 1] == "256m"
    assert command[command.index("--pids-limit") + 1] == "64"
    assert command[command.index("--user") + 1] == "65534:65534"
    assert "--read-only" in command
    assert "--cap-drop" in command
    assert "sandbox:local" in command
    assert captured["kwargs"]["timeout"] == 9


def test_docker_skill_sandbox_runner_extracts_package_payload(monkeypatch) -> None:
    captured: dict = {}

    package = BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("SKILL.md", "name: packaged")
        archive.writestr("scripts/main.py", "result = {'answer': input['name']}")
    encoded = base64.b64encode(package.getvalue()).decode("ascii")

    def fake_run(command, **kwargs):
        volume = command[command.index("-v") + 1]
        workspace = volume.rsplit(":/workspace:rw", 1)[0]
        captured["command"] = command
        with open(f"{workspace}/scripts/main.py", "r", encoding="utf-8") as handle:
            captured["script"] = handle.read()
        with open(f"{workspace}/output.json", "w", encoding="utf-8") as handle:
            json.dump({"status": "success", "output": {"answer": "ok"}}, handle)
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DockerSkillSandboxRunner(image="sandbox:local")

    result = runner.run(
        {
            "runtime_kind": "sandbox_python",
            "entrypoint": "scripts/main.py",
            "package_data_base64": encoded,
            "content": "this should not be used",
            "input": {"name": "ok"},
        }
    )

    assert result == {"status": "success", "output": {"answer": "ok"}}
    assert "input['name']" in captured["script"]
    assert captured["command"][captured["command"].index("--network") + 1] == "bridge"


def test_docker_skill_sandbox_runner_materializes_base64_workspace_files(monkeypatch) -> None:
    captured: dict = {}
    filename = "uploads/一线技术服务群风险预警&SLA告警方案.pdf"
    pdf_bytes = b"%PDF-1.7\n" + (b"x" * (1024 * 1024 + 1)) + b"\n%%EOF"

    def fake_run(command, **kwargs):
        volume = command[command.index("-v") + 1]
        workspace = Path(volume.rsplit(":/workspace:rw", 1)[0])
        uploaded = workspace / filename
        captured["exists"] = uploaded.exists()
        captured["content"] = uploaded.read_bytes() if uploaded.exists() else b""
        with open(workspace / "output.json", "w", encoding="utf-8") as handle:
            json.dump({"status": "success", "output": {"answer": "ok"}}, handle)
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DockerSkillSandboxRunner(image="sandbox:local")

    result = runner.run(
        {
            "runtime_kind": "sandbox_shell",
            "entrypoint": "main.sh",
            "content": "ls uploads",
            "input": {},
            "workspace_files": [
                {
                    "path": filename,
                    "base64": base64.b64encode(pdf_bytes).decode("ascii"),
                }
            ],
        }
    )

    assert result == {"status": "success", "output": {"answer": "ok"}}
    assert captured["exists"] is True
    assert captured["content"] == pdf_bytes


def test_docker_skill_sandbox_runner_rejects_unsafe_entrypoint() -> None:
    runner = DockerSkillSandboxRunner()

    with pytest.raises(SkillRuntimeError):
        runner.run({"runtime_kind": "sandbox_python", "entrypoint": "../main.py", "content": "", "input": {}})


def test_docker_skill_sandbox_runner_reports_timeout(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DockerSkillSandboxRunner(timeout_seconds=1)

    with pytest.raises(SkillRuntimeError, match="timed out"):
        runner.run({"runtime_kind": "sandbox_python", "entrypoint": "main.py", "content": "", "input": {}})


def test_configured_runner_from_env_is_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("OPS_ADMIN_SKILL_SANDBOX_ENABLED", raising=False)
    assert configured_runner_from_env() is None

    monkeypatch.setenv("OPS_ADMIN_SKILL_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("OPS_ADMIN_SKILL_SANDBOX_IMAGE", "sandbox:enabled")
    runner = configured_runner_from_env()

    assert isinstance(runner, DockerSkillSandboxRunner)
    assert runner.image == "sandbox:enabled"
