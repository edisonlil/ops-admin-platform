"""
Run one module init script for a project.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..config import get_config
from ..project_config import application_config_path, legacy_database_config_path
from .setup import detect_project_from_dir, get_modules_from_ops_config, get_venv_python, get_module_init_scripts


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

    module_init_scripts = get_module_init_scripts(project_path)
    script_name = module_init_scripts.get(args.module)
    if not script_name:
        print(f"Unknown module: {args.module}")
        available = get_module_init_scripts(project_path)
        if available:
            print(f"Available modules: {', '.join(available.keys())}")
        else:
            print(f"Available modules: {', '.join(MODULE_INIT_SCRIPTS.keys())}")
        return

    script_path = project_path / "scripts" / script_name
    if not script_path.exists():
        print(f"Init script not found: {script_path}")
        return

    config_dir = project_path / "config"
    explicit_env = getattr(args, "env", None)
    app_config_path = None
    legacy_db_config_path = None

    if explicit_env:
        env_config_path = application_config_path(project_path, explicit_env)
        legacy_env_config_path = legacy_database_config_path(project_path, explicit_env)
        if env_config_path.exists():
            app_config_path = env_config_path
        elif legacy_env_config_path.exists():
            legacy_db_config_path = legacy_env_config_path
        else:
            print(f"Environment config not found: {env_config_path}")
            local_config = application_config_path(project_path)
            legacy_local_config = legacy_database_config_path(project_path)
            if local_config.exists():
                print(f"Falling back to local config: {local_config}")
                app_config_path = local_config
            elif legacy_local_config.exists():
                print(f"Falling back to legacy local config: {legacy_local_config}")
                legacy_db_config_path = legacy_local_config
            else:
                print("No application config found. Use --env with existing file or run setup first.")
                return
    else:
        local_config = application_config_path(project_path)
        legacy_local_config = legacy_database_config_path(project_path)
        if local_config.exists():
            app_config_path = local_config
        elif legacy_local_config.exists():
            legacy_db_config_path = legacy_local_config

    if explicit_env:
        print(f"Using environment: {explicit_env}")
    if app_config_path:
        print(f"Using application config: {app_config_path}")
    elif legacy_db_config_path:
        print(f"Using legacy DB config: {legacy_db_config_path}")

    python_exe = get_venv_python(project_path)
    if not python_exe.exists():
        fallback = "python"
        print(f"Project venv python not found at {python_exe}, using system python.")
        python_exe = Path(fallback)

    print(f"Running module init: {args.module} -> {script_name}")
    timeout_seconds = max(1, int(getattr(args, "init_timeout", 1800)))
    run_env = os.environ.copy()
    if app_config_path:
        run_env["OPS_ADMIN_APPLICATION_CONFIG"] = str(app_config_path.resolve())
        run_env.pop("FG_AGENT_DATABASE_CONFIG", None)
    elif legacy_db_config_path:
        run_env["FG_AGENT_DATABASE_CONFIG"] = str(legacy_db_config_path.resolve())
    try:
        result = subprocess.run(
            [str(python_exe), str(script_path)],
            cwd=project_path,
            text=True,
            timeout=timeout_seconds,
            env=run_env,
        )
    except subprocess.TimeoutExpired:
        print(f"Module '{args.module}' timed out after {timeout_seconds} seconds")
        return

    if result.returncode == 0:
        print(f"Module '{args.module}' reinitialized")
        return

    print(f"Module '{args.module}' failed with exit code {result.returncode}")
