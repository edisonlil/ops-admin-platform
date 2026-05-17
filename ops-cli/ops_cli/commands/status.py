"""
Status command - show current project status.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import get_config


def run_status(args) -> None:
    """Show current project status."""
    config = get_config()

    # Get current project
    project_info = config.get_current_project()
    if not project_info:
        print("\nNo current project selected.")
        print("Use 'ops-cli list' to see available projects.")
        print("Use 'ops-cli switch <name>' to switch to a project.")
        return

    project_path = Path(project_info["path"])

    print("\n" + "=" * 50)
    print(f"Current Project: {config.load().get('current_project')}")
    print("=" * 50)

    # Basic info
    print(f"Path:     {project_info['path']}")
    print(f"Branch:   {project_info.get('branch', 'unknown')}")
    print(f"Modules:  {', '.join(project_info.get('modules', []))}")
    print(f"Created:  {project_info.get('created_at', 'unknown')}")
    print()

    # Check venv
    venv_path = project_path / ".venv"
    print(f"Virtual Environment: ", end="")
    if venv_path.exists():
        print("FOUND")
    else:
        print("NOT FOUND")
    print()

    # Check .ops-config
    ops_config = project_path / ".ops-config"
    print(f"Project Config (.ops-config): ", end="")
    if ops_config.exists():
        print("FOUND")
        try:
            with open(ops_config, "r", encoding="utf-8") as f:
                ops_conf = json.load(f)
            print("  Modules:", ", ".join(ops_conf.get("modules", [])))
        except Exception:
            pass
    else:
        print("NOT FOUND")
    print()

    # Check key files
    print("Key Files:")
    checks = [
        ("requirements.txt", "Python requirements"),
        ("api/main.py", "Main API entry"),
        ("web/admin/package.json", "Frontend package"),
        ("start-dev.bat", "Windows start script"),
        ("scripts/start-dev.ps1", "PowerShell start script"),
    ]

    for rel_path, label in checks:
        file_path = project_path / rel_path
        status = "FOUND" if file_path.exists() else "MISSING"
        print(f"  {label}: {status}")

    print()