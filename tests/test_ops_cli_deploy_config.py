from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPS_CLI_ROOT = ROOT / "ops-cli"
sys.path.insert(0, str(OPS_CLI_ROOT))

from ops_cli.cli import create_parser  # noqa: E402
from ops_cli.commands import deploy as deploy_command  # noqa: E402
from ops_cli.commands.deploy import (  # noqa: E402
    copy_deploy_environment,
    update_deploy_environment,
    _format_deploy_environment_preview,
    _has_database_connection_info,
    _load_db_config_for_target,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_deploy_target_uses_application_env_database_config(tmp_path: Path) -> None:
    write_json(
        tmp_path / "config" / "application.dev.json",
        {"database": {"backend": "mysql", "database_url": "mysql://app"}},
    )

    database, source = _load_db_config_for_target(tmp_path, "dev", {})

    assert database == {"backend": "mysql", "database_url": "mysql://app"}
    assert source == "config\\application.dev.json" or source == "config/application.dev.json"
    assert _has_database_connection_info(database)


def test_deploy_database_config_accepts_sqlite_without_database_url() -> None:
    assert _has_database_connection_info({"backend": "sqlite", "sqlite_path": "data/ops_admin.db"})
    assert _has_database_connection_info({"backend": "sqlite"})


def test_deploy_target_can_be_positional_name() -> None:
    args = create_parser().parse_args(["deploy", "dev", "--dry-run"])

    assert args.command == "deploy"
    assert args.subcommand == "dev"
    assert args.dry_run is True


def test_deploy_accepts_remote_path_and_container_port_options() -> None:
    args = create_parser().parse_args(
        [
            "deploy",
            "copy-env",
            "dev",
            "prod",
            "--remote-path",
            "/opt/ops-admin-prod",
            "--container-port",
            "9001",
        ]
    )

    assert args.subcommand == "copy-env"
    assert args.target == "dev"
    assert args.target_to == "prod"
    assert args.remote_path == "/opt/ops-admin-prod"
    assert args.container_port == 9001


def test_deploy_set_env_can_update_container_port() -> None:
    args = create_parser().parse_args(["deploy", "set-env", "prod", "--container-port", "9002"])

    assert args.subcommand == "set-env"
    assert args.target == "prod"
    assert args.container_port == 9002


def test_deploy_copy_env_can_be_subcommand_with_source_and_destination() -> None:
    args = create_parser().parse_args(["deploy", "copy-env", "dev"])

    assert args.command == "deploy"
    assert args.subcommand == "copy-env"
    assert args.target == "dev"

    args = create_parser().parse_args(["deploy", "copy-env", "dev", "prod"])

    assert args.command == "deploy"
    assert args.subcommand == "copy-env"
    assert args.target == "dev"
    assert args.target_to == "prod"


def test_copy_deploy_environment_creates_new_target_and_application_config(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".ops-deploy.json",
        {
            "dev": {
                "host": "10.0.0.8",
                "port": 22,
                "user": "ops",
                "remote_path": "/opt/ops-admin-dev",
                "container_port": 8000,
            }
        },
    )
    write_json(
        tmp_path / "config" / "application.dev.json",
        {"database": {"backend": "mysql", "database_url": "mysql://root:secret@db/dev"}},
    )

    ok, message = copy_deploy_environment(tmp_path, "dev", "prod")

    assert ok
    assert "application.dev.json" in message
    targets = json.loads((tmp_path / ".ops-deploy.json").read_text(encoding="utf-8"))
    assert targets["prod"] == targets["dev"]
    prod_config = json.loads((tmp_path / "config" / "application.prod.json").read_text(encoding="utf-8"))
    assert prod_config["database"]["database_url"] == "mysql://root:secret@db/dev"


def test_copy_deploy_environment_can_override_remote_path_and_container_port(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".ops-deploy.json",
        {
            "dev": {
                "host": "10.0.0.8",
                "port": 22,
                "user": "ops",
                "remote_path": "/opt/ops-admin-dev",
                "container_port": 8000,
            }
        },
    )

    ok, _message = copy_deploy_environment(
        tmp_path,
        "dev",
        "prod",
        overrides={"remote_path": "/opt/ops-admin-prod", "container_port": 9001},
    )

    assert ok
    targets = json.loads((tmp_path / ".ops-deploy.json").read_text(encoding="utf-8"))
    assert targets["prod"]["remote_path"] == "/opt/ops-admin-prod"
    assert targets["prod"]["container_port"] == 9001
    assert targets["dev"]["container_port"] == 8000


def test_copy_deploy_environment_refuses_overwrite(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".ops-deploy.json",
        {"dev": {"host": "dev.example.com"}, "prod": {"host": "prod.example.com"}},
    )

    ok, message = copy_deploy_environment(tmp_path, "dev", "prod")

    assert not ok
    assert "already exists" in message


def test_update_deploy_environment_updates_existing_target(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".ops-deploy.json",
        {
            "prod": {
                "host": "10.0.0.8",
                "port": 22,
                "user": "ops",
                "remote_path": "/opt/ops-admin-prod",
                "container_port": 9001,
            }
        },
    )

    ok, message = update_deploy_environment(
        tmp_path,
        "prod",
        {"container_port": 9002, "remote_path": "/opt/ops-admin-prod-v2"},
    )

    assert ok
    assert "container_port=9002" in message
    targets = json.loads((tmp_path / ".ops-deploy.json").read_text(encoding="utf-8"))
    assert targets["prod"]["container_port"] == 9002
    assert targets["prod"]["remote_path"] == "/opt/ops-admin-prod-v2"
    assert targets["prod"]["host"] == "10.0.0.8"


def test_update_deploy_environment_requires_at_least_one_update(tmp_path: Path) -> None:
    write_json(tmp_path / ".ops-deploy.json", {"prod": {"container_port": 9001}})

    ok, message = update_deploy_environment(tmp_path, "prod", {"container_port": None})

    assert not ok
    assert "No environment updates" in message


def test_deploy_environment_preview_masks_database_password() -> None:
    info = _format_deploy_environment_preview(
        "prod",
        {
            "host": "10.0.0.8",
            "port": 2222,
            "user": "ops",
            "remote_path": "/opt/ops-admin",
            "container_port": 9000,
            "ssh_key": "~/.ssh/prod",
        },
        {"backend": "mysql", "database_url": "mysql://root:secret@db.example.com:3306/ops"},
        "config/application.prod.json",
    )

    assert "Target: prod" in info
    assert "SSH: ops@10.0.0.8:2222" in info
    assert "Container name: ops-admin-backend-prod" in info
    assert "mysql://root:***@db.example.com:3306/ops" in info
    assert "secret" not in info


def test_interactive_first_deploy_target_reuses_application_env_database_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_json(
        tmp_path / "config" / "application.dev.json",
        {"database": {"backend": "mysql", "database_url": "mysql://app"}},
    )

    saved: dict = {}

    class FakeConfig:
        def get_current_project(self) -> dict:
            return {"path": str(tmp_path)}

    responses = iter(
        [
            "y",
            "10.217.19.163",
            "",
            "wps-tool",
            "2",
            "/opt/chattodo/ops-chattodo-admin",
            "8000",
        ]
    )

    monkeypatch.setattr(deploy_command, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(deploy_command, "get_deploy_targets", lambda project_path: {})
    monkeypatch.setattr(
        deploy_command,
        "save_deploy_targets",
        lambda targets, project_path: saved.update(targets),
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    deploy_command.run_deploy(SimpleNamespace(target="dev", password="sshpass"))

    assert saved["dev"]["host"] == "10.217.19.163"
    assert saved["dev"]["user"] == "wps-tool"
    assert saved["dev"]["remote_path"] == "/opt/chattodo/ops-chattodo-admin"
    assert "database_url" not in saved["dev"]


def test_deploy_add_uses_container_port_and_remote_path_options(tmp_path: Path, monkeypatch) -> None:
    saved: dict = {}

    class FakeConfig:
        def get_current_project(self) -> dict:
            return {"path": str(tmp_path)}

    responses = iter(
        [
            "prod",
            "10.0.0.8",
            "22",
            "ops",
            "2",
            "mysql://root:secret@db/prod",
        ]
    )

    monkeypatch.setattr(deploy_command, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(deploy_command, "get_deploy_targets", lambda project_path: {})
    monkeypatch.setattr(
        deploy_command,
        "save_deploy_targets",
        lambda targets, project_path: saved.update(targets),
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    args = SimpleNamespace(
        name=None,
        host=None,
        port=None,
        user=None,
        password="sshpass",
        remote_path="/opt/ops-admin-prod",
        container_port=9001,
    )

    deploy_command.run_deploy_add(args)

    assert saved["prod"]["remote_path"] == "/opt/ops-admin-prod"
    assert saved["prod"]["container_port"] == 9001
