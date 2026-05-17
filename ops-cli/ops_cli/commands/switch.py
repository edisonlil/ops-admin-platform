"""
Switch command - switch to a different project.
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

from ..config import get_config


def get_venv_python(project_path: Path) -> Path:
    """Get the Python executable in the project's venv."""
    venv_path = project_path / ".venv"
    if is_windows():
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32" or sys.platform == "cygwin"


def run_switch(args) -> None:
    """Switch to a different project."""
    config = get_config()
    project_name = args.name

    # Get project info
    if project_name:
        project_info = config.get_project(project_name)
        if not project_info:
            print(f"Error: Project '{project_name}' not found.")
            print("Use 'ops-cli list' to see available projects.")
            return
    else:
        # Show selection if no name provided
        projects = config.get_projects()
        if not projects:
            print("No projects found.")
            return

        if len(projects) == 1:
            project_name = list(projects.keys())[0]
            project_info = projects[project_name]
        else:
            print("\nSelect a project to switch to:")
            print("-" * 40)
            for i, name in enumerate(projects.keys(), 1):
                print(f"  {i}. {name}")
            print("-" * 40)

            while True:
                try:
                    choice = input("Enter number: ").strip()
                    idx = int(choice) - 1
                    names = list(projects.keys())
                    if 0 <= idx < len(names):
                        project_name = names[idx]
                        project_info = projects[project_name]
                        break
                    print(f"Please enter a number between 1 and {len(names)}")
                except ValueError:
                    print("Please enter a valid number.")

    project_path = Path(project_info["path"])

    # Check if project path exists
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        return

    # Set current project
    config.set_current_project(project_name)

    # Check for venv
    venv_path = project_path / ".venv"
    python_path = get_venv_python(project_path)

    print("\n" + "=" * 50)
    print(f"Switched to project: {project_name}")
    print("=" * 50)
    print(f"Path:     {project_path}")
    print(f"Branch:   {project_info.get('branch', 'unknown')}")
    print(f"Modules:  {', '.join(project_info.get('modules', []))}")
    print()

    if venv_path.exists():
        print("Virtual environment: FOUND")
        if is_windows():
            activate_cmd = f"{venv_path}\\Scripts\\activate.bat"
        else:
            activate_cmd = f"source {venv_path}/bin/activate"
        print(f"Activate with: {activate_cmd}")
    else:
        print("Virtual environment: NOT FOUND")

    print()

    # Provide activation instructions
    if is_windows():
        print("To activate in current shell (CMD):")
        print(f"  {venv_path}\\Scripts\\activate.bat")
        print()
        print("To activate in current shell (PowerShell):")
        print(f"  {venv_path}\\Scripts\\Activate.ps1")
    else:
        print("To activate:")
        print(f"  source {venv_path}/bin/activate")

    print()
    print("To start this project:")
    print("  ops-cli run")