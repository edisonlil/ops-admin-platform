"""
Link command - link an existing project to ops-cli management.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..config import get_config


# Module detection: directory name -> module name
MODULE_MAP = {
    "ops-admin-system": "system",
    "ops-admin-cron": "cron",
    "ops-admin-identity-access": "identity_access",
    "ops-admin-organization": "organization",
    "ops-admin-authorization": "authorization",
    "ops-admin-basic-data": "basic_data",
    "ops-admin-file-management": "file_management",
    "ops-admin-messaging": "messaging",
    "ops-admin-llm-runtime": "llm_runtime",
    "ops-admin-ai-assets": "ai_assets",
    "ops-admin-ai-applications": "ai_applications",
    "ops-admin-ai-capabilities": "ai_capabilities",
    "ops-admin-appearance": "appearance",
}


def detect_project_structure(project_path: Path) -> dict:
    """Detect project structure and return info."""
    info = {
        "has_api": (project_path / "api").exists(),
        "has_packages": (project_path / "packages").exists(),
        "has_frontend": (project_path / "web" / "admin").exists(),
        "has_scripts": (project_path / "scripts").exists(),
        "has_dockerfile": (project_path / "Dockerfile").exists(),
        "modules": [],
    }
    
    # Detect modules from packages/python
    packages_dir = project_path / "packages" / "python"
    if packages_dir.exists():
        for pkg_dir in packages_dir.iterdir():
            if pkg_dir.is_dir():
                module_name = MODULE_MAP.get(pkg_dir.name)
                if module_name:
                    info["modules"].append(module_name)
    
    return info


def write_ops_config(project_path: Path, project_name: str, modules: list[str]) -> None:
    """Write or update .ops-config file."""
    config_path = project_path / ".ops-config"
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    else:
        existing = {}
    
    # Update config
    config = {
        "name": project_name,
        "modules": modules or list(MODULE_MAP.values()),
        "linked_at": datetime.now().isoformat(),
    }
    
    # Preserve branch if exists
    if "branch" in existing:
        config["branch"] = existing["branch"]
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"Project config saved to: {config_path}")


def run_link(args) -> None:
    """Link an existing project to ops-cli."""
    config = get_config()
    projects_dir = Path(config.get("projects_dir", "~/ops-projects")).expanduser()
    
    # Determine project path
    if args.path:
        project_path = Path(args.path).expanduser().resolve()
    else:
        # Use current directory
        project_path = Path.cwd()
    
    # Check if path exists
    if not project_path.exists():
        print(f"Error: Path does not exist: {project_path}")
        return
    
    if not project_path.is_dir():
        print(f"Error: Path is not a directory: {project_path}")
        return
    
    # Check if already linked (has .ops-config)
    ops_config_path = project_path / ".ops-config"
    if ops_config_path.exists():
        try:
            with open(ops_config_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            project_name = existing.get("name", project_path.name)
            print(f"Project '{project_name}' is already linked.")
            print(f"Path: {project_path}")
            return
        except Exception:
            pass
    
    # Detect project structure
    print("\nDetecting project structure...")
    info = detect_project_structure(project_path)
    
    if not info["has_api"] and not info["has_packages"]:
        print("Error: Not a recognized ops-admin project (no api/ or packages/ found).")
        return
    
    print(f"  ✓ API: {'yes' if info['has_api'] else 'no'}")
    print(f"  ✓ Frontend: {'yes' if info['has_frontend'] else 'no'}")
    print(f"  ✓ Dockerfile: {'yes' if info['has_dockerfile'] else 'no'}")
    print(f"  ✓ Modules: {', '.join(info['modules']) or 'none detected'}")
    
    # Determine project name
    if args.name:
        project_name = args.name
    else:
        # Use folder name
        project_name = project_path.name
    
    # Check if project name already exists in config
    existing_projects = config.get_projects()
    if project_name in existing_projects:
        existing_path = existing_projects[project_name].get("path", "")
        if Path(existing_path).resolve() != project_path.resolve():
            print(f"\nError: Project name '{project_name}' already exists.")
            print(f"  Existing path: {existing_path}")
            print(f"  Given path: {project_path}")
            print("\nUse --name to specify a different name.")
            return
        else:
            print(f"\nProject '{project_name}' is already managed (same path).")
            return
    
    # Write .ops-config
    print(f"\nLinking project: {project_name}")
    write_ops_config(project_path, project_name, info["modules"])
    
    # Add to config
    config.add_project(project_name, {
        "path": str(project_path),
        "modules": info["modules"],
        "linked_at": datetime.now().isoformat(),
    })
    config.set_current_project(project_name)
    
    print("\n" + "=" * 50)
    print("Project Linked Successfully!")
    print("=" * 50)
    print(f"Name:  {project_name}")
    print(f"Path:  {project_path}")
    print(f"Modules: {', '.join(info['modules']) or 'all'}")
    print()
    print(f"Use 'ops-cli list' to see all projects.")
    print(f"Use 'ops-cli switch {project_name}' to activate.")