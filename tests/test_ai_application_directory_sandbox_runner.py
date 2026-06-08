"""DirectorySkillSandboxRunner 单元测试。

大多数测试通过 monkeypatch 替换 subprocess.run，避免实际执行任何系统命令；
少量集成级测试（需要真实 Python 环境）标记为 integration。
"""
from __future__ import annotations

import base64
import json
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from ai_applications.application.skill_runtime import SkillRuntimeError
from ai_applications.infrastructure.sandbox.directory_runner import (
    DirectorySkillSandboxRunner,
    configured_directory_runner_from_env,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _Completed:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _write_output(workspace_path: str, payload: dict) -> None:
    with open(f"{workspace_path}/output.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


# ---------------------------------------------------------------------------
# Basic run
# ---------------------------------------------------------------------------

def test_directory_runner_runs_python_skill(monkeypatch, tmp_path) -> None:
    captured: dict = {}

    def fake_run(command, **kwargs):
        # command 末尾是 --output <path>；在该路径写出 output.json
        output_idx = command.index("--output") + 1
        output_file = command[output_idx]
        Path(output_file).write_text(
            json.dumps({"status": "success", "output": {"answer": "ok"}}),
            encoding="utf-8",
        )
        captured["command"] = command
        captured["cwd"] = kwargs.get("cwd")
        return _Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DirectorySkillSandboxRunner(sandbox_root=tmp_path, keep_workspace=False)

    result = runner.run(
        {
            "runtime_kind": "sandbox_python",
            "entrypoint": "main.py",
            "content": "result = {'answer': input['name']}",
            "input": {"name": "ok"},
        }
    )

    assert result == {"status": "success", "output": {"answer": "ok"}}
    # cwd 应该是 sandbox 根目录下的子目录
    assert captured["cwd"].startswith(str(tmp_path))
    # sandbox 根目录仍存在，但执行子目录应已清理
    subdirs = list(tmp_path.rglob("output.json"))
    assert len(subdirs) == 0, "keep_workspace=False 时执行目录应被清理"


def test_directory_runner_runs_shell_skill(monkeypatch, tmp_path) -> None:
    def fake_run(command, **kwargs):
        output_idx = command.index("--output") + 1
        Path(command[output_idx]).write_text(
            json.dumps({"status": "success", "output": {"stdout": "hello"}}),
            encoding="utf-8",
        )
        return _Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DirectorySkillSandboxRunner(sandbox_root=tmp_path)

    result = runner.run(
        {
            "runtime_kind": "sandbox_shell",
            "entrypoint": "main.sh",
            "content": "echo hello",
            "input": {},
        }
    )

    assert result["status"] == "success"
    assert result["output"]["stdout"] == "hello"


# ---------------------------------------------------------------------------
# Package extraction
# ---------------------------------------------------------------------------

def test_directory_runner_extracts_package_payload(monkeypatch, tmp_path) -> None:
    package = BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("scripts/main.py", "result = {'answer': input['name']}")
    encoded = base64.b64encode(package.getvalue()).decode("ascii")

    captured: dict = {}

    def fake_run(command, **kwargs):
        output_idx = command.index("--output") + 1
        output_path = Path(command[output_idx])
        # 读取脚本内容验证
        script_idx = command.index("--script") + 1
        captured["script"] = Path(command[script_idx]).read_text(encoding="utf-8")
        output_path.write_text(
            json.dumps({"status": "success", "output": {"answer": "pkg"}}),
            encoding="utf-8",
        )
        return _Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DirectorySkillSandboxRunner(sandbox_root=tmp_path)

    result = runner.run(
        {
            "runtime_kind": "sandbox_python",
            "entrypoint": "scripts/main.py",
            "package_data_base64": encoded,
            "content": "this should not be used",
            "input": {"name": "pkg"},
        }
    )

    assert result == {"status": "success", "output": {"answer": "pkg"}}
    assert "input['name']" in captured["script"]


# ---------------------------------------------------------------------------
# Safety / error paths
# ---------------------------------------------------------------------------

def test_directory_runner_rejects_unsafe_entrypoint(tmp_path) -> None:
    runner = DirectorySkillSandboxRunner(sandbox_root=tmp_path)

    with pytest.raises(SkillRuntimeError):
        runner.run({"runtime_kind": "sandbox_python", "entrypoint": "../escape.py", "content": "", "input": {}})


def test_directory_runner_reports_timeout(monkeypatch, tmp_path) -> None:
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DirectorySkillSandboxRunner(sandbox_root=tmp_path, timeout_seconds=1)

    with pytest.raises(SkillRuntimeError, match="timed out"):
        runner.run({"runtime_kind": "sandbox_python", "entrypoint": "main.py", "content": "", "input": {}})


def test_directory_runner_reports_nonzero_exit(monkeypatch, tmp_path) -> None:
    def fake_run(command, **kwargs):
        return _Completed(returncode=1, stderr="something went wrong")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DirectorySkillSandboxRunner(sandbox_root=tmp_path)

    with pytest.raises(SkillRuntimeError, match="something went wrong"):
        runner.run({"runtime_kind": "sandbox_python", "entrypoint": "main.py", "content": "", "input": {}})


# ---------------------------------------------------------------------------
# Keep workspace
# ---------------------------------------------------------------------------

def test_directory_runner_keeps_workspace_when_configured(monkeypatch, tmp_path) -> None:
    def fake_run(command, **kwargs):
        output_idx = command.index("--output") + 1
        output_path = Path(command[output_idx])
        output_path.write_text(
            json.dumps({"status": "success", "output": {"kept": True}}),
            encoding="utf-8",
        )
        return _Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DirectorySkillSandboxRunner(sandbox_root=tmp_path, keep_workspace=True)

    runner.run({"runtime_kind": "sandbox_python", "entrypoint": "main.py", "content": "", "input": {}})

    # 执行目录应保留
    kept_outputs = list(tmp_path.rglob("output.json"))
    assert len(kept_outputs) == 1


# ---------------------------------------------------------------------------
# Workspace isolation: each run gets its own directory
# ---------------------------------------------------------------------------

def test_directory_runner_separate_workspace_per_run(monkeypatch, tmp_path) -> None:
    workdirs: list[str] = []

    def fake_run(command, **kwargs):
        workdirs.append(kwargs["cwd"])
        output_idx = command.index("--output") + 1
        Path(command[output_idx]).write_text(
            json.dumps({"status": "success", "output": {}}),
            encoding="utf-8",
        )
        return _Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = DirectorySkillSandboxRunner(sandbox_root=tmp_path, keep_workspace=True)
    request = {"runtime_kind": "sandbox_python", "entrypoint": "main.py", "content": "", "input": {}}

    runner.run(request)
    runner.run(request)

    assert len(workdirs) == 2
    assert workdirs[0] != workdirs[1], "每次 run 应使用不同的子目录"


# ---------------------------------------------------------------------------
# Environment variable configuration
# ---------------------------------------------------------------------------

def test_configured_directory_runner_from_env_is_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED", raising=False)
    assert configured_directory_runner_from_env() is None


def test_configured_directory_runner_from_env_reads_settings(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPS_ADMIN_SKILL_DIR_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("OPS_ADMIN_SKILL_DIR_SANDBOX_ROOT", str(tmp_path))
    monkeypatch.setenv("OPS_ADMIN_SKILL_DIR_SANDBOX_TIMEOUT_SECONDS", "120")
    monkeypatch.setenv("OPS_ADMIN_SKILL_DIR_SANDBOX_PYTHON", "python3")
    monkeypatch.setenv("OPS_ADMIN_SKILL_DIR_SANDBOX_KEEP_WORKSPACE", "true")

    runner = configured_directory_runner_from_env()

    assert isinstance(runner, DirectorySkillSandboxRunner)
    assert runner.sandbox_root == tmp_path
    assert runner.timeout_seconds == 120
    assert runner.python_binary == "python3"
    assert runner.keep_workspace is True
