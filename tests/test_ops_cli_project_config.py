from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPS_CLI_ROOT = ROOT / "ops-cli"
sys.path.insert(0, str(OPS_CLI_ROOT))

from ops_cli.project_config import read_database_config  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_read_database_config_prefers_application_local(tmp_path: Path) -> None:
    write_json(
        tmp_path / "config" / "application.local.json",
        {"database": {"backend": "mysql", "database_url": "mysql://app"}},
    )
    write_json(
        tmp_path / "config" / "database.local.json",
        {"database": {"backend": "mysql", "database_url": "mysql://legacy"}},
    )

    database, source = read_database_config(tmp_path)

    assert database["database_url"] == "mysql://app"
    assert source == tmp_path / "config" / "application.local.json"


def test_read_database_config_accepts_wrapped_legacy_database_file(tmp_path: Path) -> None:
    write_json(
        tmp_path / "config" / "database.local.json",
        {
            "database": {
                "backend": "mysql",
                "database_url": "mysql://legacy",
            },
            "file_management": {"preview": {}},
        },
    )

    database, source = read_database_config(tmp_path)

    assert database == {"backend": "mysql", "database_url": "mysql://legacy"}
    assert source == tmp_path / "config" / "database.local.json"
