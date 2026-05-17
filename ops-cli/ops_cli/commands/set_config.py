"""
Set command - set configuration values.
"""
from __future__ import annotations

from pathlib import Path

from ..config import get_config


def run_set(args) -> None:
    """Set configuration values."""
    config = get_config()

    if args.key == "projects_dir":
        new_path = Path(args.value).expanduser().resolve()
        if not new_path.exists():
            print(f"Directory does not exist: {new_path}")
            response = input("Create it? (y/n): ").strip().lower()
            if response == "y":
                new_path.mkdir(parents=True, exist_ok=True)
            else:
                return
        config.set("projects_dir", str(new_path))
        print(f"projects_dir set to: {new_path}")

    elif args.key == "scaffold_url":
        config.set("scaffold_url", args.value)
        print(f"scaffold_url set to: {args.value}")

    else:
        print(f"Unknown config key: {args.key}")
        print("Available keys: projects_dir, scaffold_url")