"""
Run one module init script for a project.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..config import get_config
from .setup import MODULE_INIT_SCRIPTS, detect_project_from_dir, get_modules_from_ops_config, get_venv_python


def _resolve_project(config, projects_dir: Path, name: str | None) -> tuple[str, dict]:
    if name:
        project_info = config.get_project(name)
        if not project_info:
            raise ValueError(f"Project '{name}' not found.")
        project_path = Path(project_info["path"])
        return name, project_info

    current_project = config.get("current_project")
    if current_project:
        current_info = config.get_project(current_project)
        if current_info:
            return current_project, current_info

    detected = detect_project_from_dir(projects_dir)
    if detected:
        return detected

    raise ValueError("Project not specified and no current/linked project found.")


def run_rerun_module(args) -> None:
    config = get_config()
    projects_dir = Path(config.get("projects_dir", "~/OpsPyProject")).expanduser()

    _, project_info = _resolve_project(config, projects_dir, args.name)
    project_path = Path(project_info["path"])

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        return

    script_name = MODULE_INIT_SCRIPTS.get(args.module)
    if not script_name:
        print(f"Unknown module: {args.module}")
        available = get_modules_from_ops_config(project_path)
        if available:
            print(f"Available modules: {', '.join(available)}")
        else:
            print(f"Available modules: {', '.join(MODULE_INIT_SCRIPTS.keys())}")
        return

    script_path = project_path / "scripts" / script_name
    if not script_path.exists():
        print(f"Init script not found: {script_path}")
        return

    config_dir = project_path / "config"
    explicit_env = getattr(args, "env", None)
    db_config_path = None

    if explicit_env:
        env_config_path = config_dir / f"database.{explicit_env}.json"
        if not env_config_path.exists():
            print(f"Environment config not found: {env_config_path}")
            local_config = config_dir / "database.local.json"
            if local_config.exists():
                print(f"Falling back to local config: {local_config}")
                db_config_path = local_config
            else:
                print("No database config found. Use --env with existing file or run setup first.")
                return
        else:
            db_config_path = env_config_path
    else:
        local_config = config_dir / "database.local.json"
        if local_config.exists():
            db_config_path = local_config

    if explicit_env:
        print(f"Using environment: {explicit_env}")
    if db_config_path:
        print(f"Using DB config: {db_config_path}")

    python_exe = get_venv_python(project_path)
    if not python_exe.exists():
        fallback = "python"
        print(f"Project venv python not found at {python_exe}, using system python.")
        python_exe = Path(fallback)

    print(f"Running module init: {args.module} -> {script_name}")
    run_env = os.environ.copy()
    if db_config_path:
        run_env["FG_AGENT_DATABASE_CONFIG"] = str(db_config_path.resolve())
    result = subprocess.run(
        [str(python_exe), str(script_path)],
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=120,
        env=run_env,
    )

    if result.returncode == 0:
        print(f"Module '{args.module}' reinitialized")
        if result.stdout:
            print(result.stdout.strip())
        return

    msg = (result.stderr or result.stdout or "unknown error").strip()
    print(f"Module '{args.module}' failed: {msg}")
