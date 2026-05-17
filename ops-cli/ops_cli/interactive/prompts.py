"""
Prompts for interactive input.
"""
from __future__ import annotations

from typing import Optional


def ask_project_name(default: Optional[str] = None) -> Optional[str]:
    """Ask for project name."""
    prompt = "Project name"
    if default:
        prompt += f" [{default}]"

    while True:
        name = input(f"{prompt}: ").strip()
        if not name:
            if default:
                return default
            print("Project name cannot be empty.")
            continue

        # Validate name (alphanumeric, dash, underscore)
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            print("Project name can only contain letters, numbers, dash, and underscore.")
            continue

        return name


def ask_confirmation(message: str, default: bool = False) -> bool:
    """Ask for yes/no confirmation."""
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        response = input(f"{message}{suffix}: ").strip().lower()
        if not response:
            return default
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'")


def ask_with_choices(prompt: str, choices: list[str], default: Optional[str] = None) -> Optional[str]:
    """Ask with predefined choices."""
    choices_str = "/".join(choices)
    prompt_full = f"{prompt} ({choices_str})"

    if default:
        prompt_full += f" [{default}]"

    while True:
        response = input(f"{prompt_full}: ").strip().lower()
        if not response and default:
            return default
        if response in choices:
            return response
        print(f"Please enter one of: {choices_str}")