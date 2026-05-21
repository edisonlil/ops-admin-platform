from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPS_CLI_ROOT = ROOT / "ops-cli"
sys.path.insert(0, str(OPS_CLI_ROOT))

from ops_cli.cli import create_parser  # noqa: E402
from ops_cli.commands import init as init_command  # noqa: E402


def parse_init_args(*args: str) -> argparse.Namespace:
    parser = create_parser()
    return parser.parse_args(("init", *args))


def test_init_reinit_git_defaults_to_prompt(monkeypatch) -> None:
    calls: list[tuple[str, bool]] = []

    def fake_ask_confirmation(message: str, default: bool = False) -> bool:
        calls.append((message, default))
        return False

    monkeypatch.setattr(init_command, "ask_confirmation", fake_ask_confirmation)

    args = parse_init_args()

    assert args.reinit_git is None
    assert init_command.should_reinitialize_git(args) is False
    assert calls == [("Reinitialize git for this project and configure a new remote?", True)]


def test_init_reinit_git_flags_skip_prompt(monkeypatch) -> None:
    def fail_if_prompted(*_args, **_kwargs) -> bool:
        raise AssertionError("confirmation prompt should not run for explicit flags")

    monkeypatch.setattr(init_command, "ask_confirmation", fail_if_prompted)

    assert init_command.should_reinitialize_git(parse_init_args("--reinit-git")) is True
    assert init_command.should_reinitialize_git(parse_init_args("--no-reinit-git")) is False
