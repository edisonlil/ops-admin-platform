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
from ops_cli.commands.deploy import _has_database_connection_info, _load_db_config_for_target  # noqa: E402


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
