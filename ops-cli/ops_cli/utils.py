"""
Utility functions for ops-cli.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional, List


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    capture_output: bool = True,
    check: bool = True,
    timeout: Optional[int] = 300,
) -> subprocess.CompletedProcess:
    """Run a shell command."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture_output,
        text=True,
        check=check,
        timeout=timeout,
    )
    return result


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32" or sys.platform == "cygwin"


def activate_venv_script(venv_path: Path) -> str:
    """Get the path to activate the virtual environment script."""
    if is_windows():
        return str(venv_path / "Scripts" / "activate.bat")
    else:
        return str(venv_path / "bin" / "activate")


def get_venv_python(venv_path: Path) -> Path:
    """Get the Python executable in a virtual environment."""
    if is_windows():
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def ensure_dir(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def read_json_file(path: Path) -> dict:
    """Read a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


import json  # Add json import