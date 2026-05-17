"""
Init command - create a new project from scaffold.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ..config import get_config
from ..interactive.selector import select_from_list, select_multiple_from_list
from ..interactive.prompts import ask_project_name
from ..utils import run_command, ensure_dir, is_windows


# Available modules from the scaffold
AVAILABLE_MODULES = [
    "system",
    "cron",
    "identity_access",
    "organization",
    "authorization",
    "basic_data",
    "file_management",
    "messaging",
    "llm_runtime",
    "ai_assets",
    "ai_applications",
    "ai_capabilities",
    "appearance",
]


def fetch_branches(scaffold_url: str) -> list[str]:
    """Fetch all remote branches from the scaffold repository."""
    print(f"Fetching branches from {scaffold_url}...")
    try:
        # Use git ls-remote to get branches
        result = run_command(
            ["git", "ls-remote", "--heads", "--tags", scaffold_url],
            capture_output=True,
            check=True,
        )
        branches = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t")
                if len(parts) == 2:
                    ref = parts[1]
                    if ref.startswith("refs/heads/"):
                        branches.append(ref.replace("refs/heads/", ""))
                    elif ref.startswith("refs/tags/"):
                        branches.append(ref.replace("refs/tags/", ""))

        # Remove duplicates and sort
        branches = sorted(set(branches))
        # Put main and develop at top
        priority = ["main", "master", "develop", "dev"]
        branches.sort(key=lambda x: priority.index(x) if x in priority else 999)
        return branches
    except Exception as e:
        print(f"Failed to fetch branches: {e}")
        return ["main", "develop"]  # Fallback


def clone_repo(scaffold_url: str, branch: str, target_path: Path) -> bool:
    """Clone the scaffold repository."""
    print(f"Cloning {scaffold_url} (branch: {branch})...")
    try:
        run_command(
            ["git", "clone", "-b", branch, "--depth", "1", scaffold_url, str(target_path)],
            capture_output=False,
            check=True,
            timeout=300,
        )
        return True
    except Exception as e:
        print(f"Failed to clone repository: {e}")
        return False


def setup_new_git(target_path: Path) -> None:
    """Initialize git and optionally set new remote."""
    print("Initializing new git repository...")
    
    git_dir = target_path / ".git"
    if git_dir.exists():
        import time
        import shutil
        time.sleep(0.5)
        try:
            if sys.platform == "win32":
                import tempfile
                temp_dir = Path(tempfile.gettempdir()) / f"tmp_del_{os.getpid()}"
                temp_dir.mkdir(exist_ok=True)
                subprocess.run(
                    ["robocopy", str(temp_dir), str(git_dir), "/MIR", "/R:3", "/W:2", "/NP", "/NFL", "/NDL"],
                    capture_output=True,
                    check=False,
                )
                if git_dir.exists():
                    shutil.rmtree(git_dir, ignore_errors=True)
            else:
                shutil.rmtree(git_dir, ignore_errors=True)
        except Exception as e:
            print(f"Warning: Could not fully remove .git directory: {e}")

    try:
        run_command(["git", "init"], cwd=target_path, capture_output=True, check=True)
        print("Git repository initialized.")
        
        # Ask for new remote
        print("\nGit Remote Setup:")
        print("-" * 40)
        default_remote = input("Git remote URL (leave empty to skip): ").strip()
        
        if default_remote:
            try:
                existing_remote = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=target_path,
                    capture_output=True,
                    text=True,
                )

                if existing_remote.returncode == 0:
                    print("Remote 'origin' already exists, updating URL...")
                    run_command(
                        ["git", "remote", "set-url", "origin", default_remote],
                        cwd=target_path,
                        capture_output=True,
                        check=True,
                    )
                else:
                    run_command(
                        ["git", "remote", "add", "origin", default_remote],
                        cwd=target_path,
                        capture_output=True,
                        check=True,
                    )
                print(f"Remote 'origin' set to: {default_remote}")

                # Reset branch to main
                print("\nResetting branch to 'main'...")
                run_command(
                    ["git", "checkout", "-B", "main"],
                    cwd=target_path,
                    capture_output=True,
                    check=True,
                )
                print("Branch reset to 'main'.")
                
                # Create initial commit
                print("Creating initial commit...")
                run_command(
                    ["git", "add", "-A"],
                    cwd=target_path,
                    capture_output=True,
                    check=True,
                )
                try:
                    run_command(
                        ["git", "commit", "-m", "Initial commit from ops-cli"],
                        cwd=target_path,
                        capture_output=True,
                        check=True,
                    )
                    print("Initial commit created.")
                except Exception:
                    print("No files to commit (empty project).")
                
                # Push to remote
                print("\nPushing to remote...")
                try:
                    run_command(
                        ["git", "push", "-u", "origin", "main"],
                        cwd=target_path,
                        capture_output=True,
                        check=True,
                    )
                    print("Pushed to origin/main.")
                except Exception as e:
                    print(f"Warning: Failed to push: {e}")
                    
            except Exception as e:
                print(f"Warning: Failed to set remote: {e}")
        else:
            print("Skipped remote setup (no URL provided).")
            
    except Exception as e:
        print(f"Warning: Failed to initialize git: {e}")


def create_venv(target_path: Path) -> Path:
    """Create a Python virtual environment."""
    print("Creating Python virtual environment...")
    venv_path = target_path / ".venv"
    try:
        run_command(
            [sys.executable, "-m", "venv", str(venv_path)],
            capture_output=False,
            check=True,
        )
        print(f"Virtual environment created at: {venv_path}")
        return venv_path
    except Exception as e:
        print(f"Failed to create virtual environment: {e}")
        raise


def install_dependencies(venv_python: Path, target_path: Path) -> None:
    """Install Python dependencies."""
    print("Installing Python dependencies...")
    requirements = target_path / "requirements.txt"
    if requirements.exists():
        try:
            run_command(
                [str(venv_python), "-m", "pip", "install", "-r", str(requirements)],
                cwd=target_path,
                capture_output=False,
                check=True,
                timeout=600,
            )
            print("Python dependencies installed.")
        except Exception as e:
            print(f"Warning: Failed to install Python dependencies: {e}")
    else:
        print("No requirements.txt found, skipping Python dependencies.")


def install_node_dependencies(target_path: Path) -> None:
    """Install Node.js dependencies."""
    frontend_path = target_path / "web" / "admin"
    if not frontend_path.exists():
        print("No frontend directory found, skipping Node dependencies.")
        return

    package_json = frontend_path / "package.json"
    if not package_json.exists():
        print("No package.json found, skipping Node dependencies.")
        return

    print("Installing Node.js dependencies...")

    # Try pnpm first, then npm
    for pm in ["pnpm", "npm"]:
        try:
            print(f"Installing with {pm}...")
            run_command(
                [pm, "install"],
                cwd=frontend_path,
                capture_output=False,
                check=True,
                timeout=600,
            )
            print(f"Node.js dependencies installed with {pm}.")
            return
        except Exception:
            continue

    print("Warning: Failed to install Node.js dependencies.")


def copy_scaffold_docs(target_path: Path) -> None:
    """Save scaffold AGENTS.md for reference."""
    scaffold_agents = target_path / ".ops-scaffold" / "AGENTS.md"
    current_agents = target_path / "AGENTS.md"
    
    # Save current AGENTS.md as scaffold reference
    if current_agents.exists():
        scaffold_agents.parent.mkdir(exist_ok=True)
        import shutil
        shutil.copy2(current_agents, scaffold_agents)
        print("Scaffold rules saved to .ops-scaffold/AGENTS.md")


def copy_agents_guide(target_path: Path) -> None:
    """Copy project-level AGENTS.md to project root."""
    template_path = Path(__file__).parent.parent / "templates" / "AGENTS.md"
    if template_path.exists():
        import shutil
        shutil.copy2(template_path, target_path / "AGENTS.md")
        print("Project AGENTS.md copied to project root.")


def write_ops_config(target_path: Path, project_name: str, branch: str, modules: list[str]) -> None:
    """Write .ops-config file."""
    config = {
        "name": project_name,
        "branch": branch,
        "modules": modules,
        "created_at": datetime.now().isoformat(),
    }
    config_path = target_path / ".ops-config"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"Project config saved to: {config_path}")


def run_init(args) -> None:
    """Initialize a new project."""
    config = get_config()
    scaffold_url = config.get("scaffold_url")
    projects_dir = Path(config.get("projects_dir"))

    # Ensure projects directory exists
    ensure_dir(projects_dir)

    # Step 1: Fetch and select branch
    print("\n" + "=" * 50)
    print("Step 1: Select Branch")
    print("=" * 50)
    branches = fetch_branches(scaffold_url)
    if not branches:
        print("No branches found, using 'main' as default.")
        branches = ["main"]

    selected_branch = select_from_list(branches, "Select a branch to create project from:")
    if not selected_branch:
        print("Operation cancelled.")
        return

    print(f"Selected branch: {selected_branch}")

    # Step 2: Select modules
    print("\n" + "=" * 50)
    print("Step 2: Select Modules")
    print("=" * 50)
    print("Select which modules to enable (enter numbers separated by space):")
    selected_modules = select_multiple_from_list(
        AVAILABLE_MODULES,
        "Select modules (e.g., '1 3 5' for system, identity_access, llm_runtime):"
    )
    if not selected_modules:
        print("No modules selected, using all modules.")
        selected_modules = AVAILABLE_MODULES.copy()

    print(f"Selected modules: {', '.join(selected_modules)}")

    # Step 3: Enter project name
    print("\n" + "=" * 50)
    print("Step 3: Project Name")
    print("=" * 50)
    default_name = f"ops-project-{datetime.now().strftime('%Y%m%d')}"
    project_name = ask_project_name(default_name)
    if not project_name:
        print("Operation cancelled.")
        return

    # Check if project already exists
    project_path = projects_dir / project_name
    if project_path.exists():
        print(f"Error: Project '{project_name}' already exists at {project_path}")
        return

    # Step 4: Clone repository
    print("\n" + "=" * 50)
    print("Step 4: Creating Project")
    print("=" * 50)

    if not clone_repo(scaffold_url, selected_branch, project_path):
        print("Failed to create project.")
        return

    # Step 5: Save scaffold docs and copy project AGENTS.md
    copy_scaffold_docs(project_path)
    copy_agents_guide(project_path)

    # Step 6: Initialize git with new remote
    setup_new_git(project_path)

    # Step 7: Create virtual environment
    try:
        venv_path = create_venv(project_path)
    except Exception:
        print("Failed to create virtual environment. Continuing anyway...")
        venv_path = None

    # Step 8: Install dependencies
    if venv_path:
        python_exe = venv_path / "Scripts" / "python.exe" if is_windows() else venv_path / "bin" / "python"
        install_dependencies(python_exe, project_path)

    install_node_dependencies(project_path)

    # Step 8: Write config
    write_ops_config(project_path, project_name, selected_branch, selected_modules)

    # Step 9: Add to config
    config.add_project(project_name, {
        "path": str(project_path),
        "branch": selected_branch,
        "modules": selected_modules,
        "created_at": datetime.now().isoformat(),
    })
    config.set_current_project(project_name)

    print("\n" + "=" * 50)
    print("Project Created Successfully!")
    print("=" * 50)
    print(f"Name:     {project_name}")
    print(f"Path:     {project_path}")
    print(f"Branch:   {selected_branch}")
    print(f"Modules:  {', '.join(selected_modules)}")
    print()
    print("To activate the environment and start working:")
    if is_windows():
        print(f"  .venv\\Scripts\\activate")
    else:
        print(f"  source .venv/bin/activate")
    print()
    print("To start the project:")
    print(f"  ops-cli run")
