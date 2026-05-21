"""
List command - list all managed projects.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..config import get_config


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str


def run_list(args) -> None:
    """List all projects."""
    config = get_config()
    projects = config.get_projects()
    current = config.get_active_project_name()

    if not projects:
        print("\nNo projects found.")
        print("Create your first project with: ops-cli init")
        return

    print("\n" + "=" * 70)
    print(f"{'Project Name':<25} {'Branch':<15} {'Modules':<20} Created")
    print("-" * 70)

    for name, info in projects.items():
        marker = "*" if name == current else " "
        branch = info.get("branch", "unknown")
        modules = info.get("modules", [])
        modules_str = ",".join(modules[:3])
        if len(modules) > 3:
            modules_str += f"...+{len(modules) - 3}"
        created = format_datetime(info.get("created_at", ""))

        print(f"{marker} {name:<24} {branch:<15} {modules_str:<20} {created}")

    print("-" * 70)
    print(f"Total: {len(projects)} project(s)")
    if current:
        print(f"Active: {current}")
    print()
