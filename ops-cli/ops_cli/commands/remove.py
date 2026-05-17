"""
Remove command - remove a project.
"""
from __future__ import annotations

import shutil

from ..config import get_config
from ..interactive.prompts import ask_confirmation


def run_remove(args) -> None:
    """Remove a project."""
    config = get_config()
    project_name = args.name

    if not project_name:
        # Show selection
        projects = config.get_projects()
        if not projects:
            print("No projects to remove.")
            return

        print("\nSelect a project to remove:")
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
                    break
                print(f"Please enter a number between 1 and {len(names)}")
            except ValueError:
                print("Please enter a valid number.")

    # Get project info
    project_info = config.get_project(project_name)
    if not project_info:
        print(f"Error: Project '{project_name}' not found.")
        return

    project_path = project_info["path"]

    print("\n" + "=" * 50)
    print(f"About to remove project: {project_name}")
    print("=" * 50)
    print(f"Path: {project_path}")
    print()

    # Confirmation
    if not ask_confirmation("Are you sure you want to remove this project?", default=False):
        print("Operation cancelled.")
        return

    # Also ask about deleting files
    delete_files = ask_confirmation(
        "Do you also want to DELETE the project files from disk? (no = keep files)",
        default=False,
    )

    # Remove from config
    config.remove_project(project_name)
    print(f"Project '{project_name}' removed from management.")

    # Delete files if requested
    if delete_files:
        from pathlib import Path

        path = Path(project_path)
        if path.exists():
            try:
                shutil.rmtree(path)
                print(f"Project files deleted: {project_path}")
            except Exception as e:
                print(f"Warning: Failed to delete project files: {e}")
                print(f"Please manually delete: {project_path}")
        else:
            print(f"Project path does not exist: {project_path}")

    print("\nDone.")