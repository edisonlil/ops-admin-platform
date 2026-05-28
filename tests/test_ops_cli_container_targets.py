from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPS_CLI_ROOT = ROOT / "ops-cli"
sys.path.insert(0, str(OPS_CLI_ROOT))

from ops_cli.commands import container as container_command  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_container_targets_use_active_project_deploy_file(tmp_path: Path, monkeypatch) -> None:
    project_path = tmp_path / "active"
    write_json(
        project_path / ".ops-deploy.json",
        {"dev": {"host": "project.example.com", "remote_path": "/opt/project-dev"}},
    )

    class FakeConfig:
        def get_current_project(self) -> dict:
            return {"path": str(project_path)}

        def load(self) -> dict:
            return {"deploy_targets": {"dev": {"host": "global.example.com"}}}

    monkeypatch.setattr(container_command, "get_config", lambda: FakeConfig())

    targets = container_command.get_deploy_targets()

    assert targets["dev"]["host"] == "project.example.com"
    assert targets["dev"]["remote_path"] == "/opt/project-dev"


class FakeChannel:
    def fileno(self) -> int:
        return 0

    def recv_exit_status(self) -> int:
        return 0

    def recv_ready(self) -> bool:
        return False

    def exit_status_ready(self) -> bool:
        return True


class FakeStream:
    def __init__(self) -> None:
        self.channel = FakeChannel()

    def read(self, *_args) -> bytes:
        return b""


class FakeClient:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def exec_command(self, command: str):
        self.commands.append(command)
        return FakeStream(), FakeStream(), FakeStream()

    def close(self) -> None:
        pass


def test_container_stop_uses_project_remote_path_and_compose_helper(tmp_path: Path, monkeypatch) -> None:
    project_path = tmp_path / "active"
    write_json(
        project_path / ".ops-deploy.json",
        {"dev": {"host": "project.example.com", "remote_path": "/opt/project-dev"}},
    )

    class FakeConfig:
        def get_current_project(self) -> dict:
            return {"path": str(project_path)}

    fake_client = FakeClient()
    monkeypatch.setattr(container_command, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(container_command, "ssh_connect", lambda target: fake_client)
    monkeypatch.setattr(container_command.select, "select", lambda readable, _writable, _errors: (readable, [], []))

    container_command.run_container_command(SimpleNamespace(command="stop", target="dev", lines=100, follow=False))

    assert len(fake_client.commands) == 1
    assert "/opt/project-dev/docker-compose.yml stop" in fake_client.commands[0]
    assert "docker compose" in fake_client.commands[0]


def test_container_restart_runs_restart_action(tmp_path: Path, monkeypatch) -> None:
    project_path = tmp_path / "active"
    write_json(
        project_path / ".ops-deploy.json",
        {"prod": {"host": "project.example.com", "remote_path": "/opt/project-prod"}},
    )

    class FakeConfig:
        def get_current_project(self) -> dict:
            return {"path": str(project_path)}

    fake_client = FakeClient()
    monkeypatch.setattr(container_command, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(container_command, "ssh_connect", lambda target: fake_client)
    monkeypatch.setattr(container_command.select, "select", lambda readable, _writable, _errors: (readable, [], []))

    container_command.run_container_command(SimpleNamespace(command="restart", target="prod", lines=100, follow=False))

    assert "/opt/project-prod/docker-compose.yml restart" in fake_client.commands[0]
