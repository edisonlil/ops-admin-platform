"""
Setup command - configure project database and run init scripts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ..config import get_config
from ..interactive.prompts import ask_with_choices, ask_confirmation
from ..project_config import read_database_config, write_database_config as write_application_database_config
from ..services.discovery import discover_modules


def detect_project_from_dir(projects_dir: Path) -> tuple[str, dict] | None:
    """Detect project from current directory by checking .ops-config or config."""
    cwd = Path.cwd()
    
    # First check if this is a managed project in config
    config = get_config()
    projects = config.get_projects()
    
    for name, project_info in projects.items():
        project_path = Path(project_info.get("path", "")).resolve()
        if project_path == cwd.resolve():
            return name, project_info
    
    # Also check if current directory is under projects_dir
    try:
        relative = cwd.relative_to(projects_dir)
        project_name = relative.parts[0]
        project_info = config.get_project(project_name)
        if project_info:
            return project_name, project_info
    except Exception:
        pass
    
    return None


def create_database_if_not_exists(backend: str, database_url: str) -> bool:
    """
    Create database if it doesn't exist (for MySQL/PostgreSQL).
    Returns True if database exists or was created, False on error.
    """
    if backend == "sqlite":
        return True  # SQLite creates file automatically
    
    try:
        from urllib.parse import urlparse
        
        parsed = urlparse(database_url)
        
        if backend == "mysql":
            import pymysql
            # Connect without database to create it
            conn = pymysql.connect(
                host=parsed.hostname,
                port=parsed.port or 3306,
                user=parsed.username,
                password=parsed.password,
            )
            cursor = conn.cursor()
            db_name = parsed.path.lstrip('/')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            cursor.close()
            conn.close()
            print(f"  Database '{db_name}' created/verified.")
            return True
            
        elif backend == "postgres":
            import psycopg2
            from urllib.parse import quote
            # Connect to default postgres database to create new database
            admin_url = f"postgresql://{parsed.username}:{quote(parsed.password)}@{parsed.hostname}:{parsed.port or 5432}/postgres"
            conn = psycopg2.connect(admin_url)
            conn.autocommit = True
            cursor = conn.cursor()
            db_name = parsed.path.lstrip('/')
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(f"CREATE DATABASE {db_name}")
                print(f"  Database '{db_name}' created.")
            else:
                print(f"  Database '{db_name}' already exists.")
            cursor.close()
            conn.close()
            return True
            
    except ImportError:
        print("  Warning: Database driver not installed. Cannot auto-create database.")
        print("  Please create the database manually before running init scripts.")
        return True  # Continue anyway, init scripts might handle it
    except Exception as e:
        print(f"  Warning: Could not auto-create database: {e}")
        print("  Please create the database manually.")
        return True  # Continue anyway
    
    return True


def write_database_config(project_path: Path, backend: str, **kwargs) -> None:
    """Write database settings into the project application config."""
    if backend == "sqlite":
        db_path = kwargs.get("sqlite_path", "ops_admin.db")
        config = {
            "backend": "sqlite",
            "sqlite_path": db_path
        }
    elif backend == "postgres":
        config = {
            "backend": "postgres",
            "database_url": kwargs.get("database_url", "")
        }
    elif backend == "mysql":
        config = {
            "backend": "mysql",
            "database_url": kwargs.get("database_url", "")
        }
    
    config_file = write_application_database_config(project_path, config)
    print(f"Application config saved to: {config_file}")


def get_venv_python(project_path: Path) -> Path:
    """Get the Python executable in the project's venv."""
    venv_path = project_path / ".venv"
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def get_project_requirements(project_path: Path) -> dict:
    """Get project version requirements from .ops-requirements.json."""
    req_file = project_path / ".ops-requirements.json"
    if req_file.exists():
        try:
            with open(req_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Fallback defaults
    return {
        "python": ">=3.10",
        "node": ">=18",
    }


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse version string like '3.10' or '18.19' into tuple."""
    import re
    match = re.search(r'(\d+)\.(\d+)', version_str)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (0, 0)


def check_python_version() -> tuple[bool, str, str]:
    """
    Check if Python version is compatible with project requirements.
    Returns (compatible, current_version, required_version).
    """
    python_ok, python_version = check_python_available()
    if not python_ok:
        return False, "not found", ""
    
    # Parse current version
    import re
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', python_version)
    if not match:
        return True, python_version, ""  # Can't parse, assume ok
    
    current = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    
    # Get required version from .ops-requirements.json or use default
    project_req = get_project_requirements(Path.cwd())
    required_str = project_req.get("python", ">=3.11")
    
    # Parse required version
    req_match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', required_str)
    if req_match:
        required = (int(req_match.group(1)), int(req_match.group(2)), int(req_match.group(3) or 0))
        
        # Check if version matches
        if required[0] == current[0] and required[1] == current[1] and required[2] == current[2]:
            return True, python_version, required_str
        
        # Also allow if current is higher patch version
        if current[0] == required[0] and current[1] == required[1] and current[2] >= required[2]:
            return True, python_version, required_str
        
        return False, python_version, required_str
    
    return True, python_version, required_str


def check_node_version() -> tuple[bool, str, str]:
    """
    Check if Node.js version is compatible with project requirements.
    Returns (compatible, current_version, required_version).
    """
    node_ok, node_info = check_node_available()
    if not node_ok:
        return False, "not found", ""
    
    # Extract node version from info
    import re
    match = re.search(r'node\s+v?(\d+)\.(\d+)\.(\d+)', node_info)
    if not match:
        return True, node_info, ""  # Can't parse, assume ok
    
    current = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    
    # Get required version from .ops-requirements.json or use default
    project_req = get_project_requirements(Path.cwd())
    required_str = project_req.get("node", ">=18")
    
    # Parse required version
    req_match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', required_str)
    if req_match:
        required = (int(req_match.group(1)), int(req_match.group(2)), int(req_match.group(3) or 0))
        
        # Check exact match or higher version
        if current >= required:
            return True, node_info, required_str
        
        return False, node_info, required_str
    
    return True, node_info, required_str


def check_python_available() -> tuple[bool, str]:
    """Check if Python is available on the system. Returns (available, version)."""
    import shutil
    # Try python first, then python3
    for cmd in ["python", "python3"]:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                return True, version
        except Exception:
            pass
    return False, ""


def check_node_available() -> tuple[bool, str]:
    """Check if Node.js/npm is available. Returns (available, version)."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            node_version = result.stdout.strip()
            # Also check npm
            npm_result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            npm_version = npm_result.stdout.strip() if npm_result.returncode == 0 else "unknown"
            return True, f"node {node_version}, npm {npm_version}"
    except Exception:
        pass
    return False, ""


def check_venv_ready(venv_path: Path) -> bool:
    """Check if virtual environment is set up and ready."""
    if not venv_path.exists():
        return False
    
    # Check Python executable exists
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    if not python_exe.exists():
        return False
    
    # Check if key packages are installed
    try:
        result = subprocess.run(
            [str(python_exe), "-c", "import fastapi; import uvicorn; import sqlalchemy"],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_venv(project_path: Path, interactive: bool = True) -> Path | None:
    """Ensure virtual environment exists and is ready."""
    venv_path = project_path / ".venv"
    
    if venv_path.exists() and check_venv_ready(venv_path):
        print("Virtual environment: OK (dependencies already installed)")
        return venv_path


def ensure_node_ready(project_path: Path) -> bool:
    """Check if Node.js is available and compatible."""
    compatible, current_info, required = check_node_version()
    
    if not compatible:
        print("\n" + "=" * 50)
        print(f"WARNING: Node.js version may be incompatible")
        print("=" * 50)
        print(f"  Current:  {current_info}")
        print(f"  Required: {required}")
        print()
        print("Please upgrade Node.js first:")
        print("  Windows: https://nodejs.org/")
        print("  Or: choco install nodejs (if using Chocolatey)")
        print("  Or: winget install OpenJS.NodeJS.LTS")
        print()
        return False
    
    print(f"Node.js: {current_info}")
    return True
    
    # Check Python version compatibility
    compatible, current_version, required = check_python_version()
    if not compatible:
        print("\n" + "=" * 50)
        print(f"ERROR: Python version incompatible")
        print("=" * 50)
        print(f"  Current:  {current_version}")
        print(f"  Required: {required}")
        print()
        print("Please upgrade Python first:")
        print("  Windows: https://www.python.org/downloads/")
        print("  Or: choco install python (if using Chocolatey)")
        print("  Or: winget install Python.Python.3.12")
        print()
        return None
    
    print(f"Python: {current_version} (compatible)")
    
    if not venv_path.exists():
        if interactive:
            print("Creating virtual environment...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                cwd=project_path,
                check=True,
            )
            print("Virtual environment created.")
        except Exception as e:
            print(f"Failed to create venv: {e}")
            return None
    
    python_exe = get_venv_python(project_path)
    
    # Check if dependencies need installation
    print("Checking dependencies...")
    deps_needed = False
    try:
        result = subprocess.run(
            [str(python_exe), "-c", "import fastapi"],
            capture_output=True,
            timeout=30,
        )
        deps_needed = result.returncode != 0
    except Exception:
        deps_needed = True
    
    if deps_needed:
        print("Installing Python dependencies...")
        requirements = project_path / "requirements.txt"
        if requirements.exists():
            try:
                subprocess.run(
                    [str(python_exe), "-m", "pip", "install", "-r", str(requirements)],
                    check=True,
                    timeout=300,
                )
                print("Dependencies installed.")
            except Exception as e:
                print(f"Warning: Could not install dependencies: {e}")
    
    return venv_path


# Module to init script mapping - use discovery service
def get_module_init_scripts(project_path: Path) -> dict[str, str]:
    """Get all discovered modules that have init scripts."""
    discovery_result = discover_modules(project_path)
    return discovery_result.get_modules_with_init()


def get_modules_from_ops_config(project_path: Path) -> list[str]:
    """Get enabled modules from .ops-config. Returns all discovered modules if not found."""
    ops_config = project_path / ".ops-config"
    if ops_config.exists():
        try:
            with open(ops_config, "r", encoding="utf-8") as f:
                config = json.load(f)
            modules = config.get("modules", [])
            if modules:
                return modules
        except Exception:
            pass

    # If .ops-config doesn't exist or has no modules, default to all discovered modules
    return discover_modules(project_path).get_module_names()


def check_already_initialized(project_path: Path, backend: str, db_path: str = "") -> set[str]:
    """
    Check which init scripts have already been run by looking for
    initialized markers in the database.
    Returns set of module names that have been initialized.
    """
    initialized = set()
    
    # Check if database exists and has tables
    if backend == "sqlite":
        db_file = project_path / db_path if Path(db_path).is_absolute() else project_path / db_path
        if db_file.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                # Check for common indicator tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                # If we have users table, identity_access is initialized
                if "users" in tables:
                    initialized.add("identity_access")
                if "messages" in tables or "conversations" in tables:
                    initialized.add("messaging")
                if "appearance_configs" in tables:
                    initialized.add("appearance")
                if "llm_configs" in tables or "ai_models" in tables:
                    initialized.add("llm_runtime")
                if "ai_applications" in tables:
                    initialized.add("ai_applications")
                if "ai_capabilities" in tables:
                    initialized.add("ai_capabilities")
            except Exception:
                pass
    elif backend in ("mysql", "postgres"):
        # For MySQL/Postgres, we'd need to check connection
        # For now, use a marker file approach
        pass
    
    return initialized


def run_init_scripts(project_path: Path, python_exe: Path) -> None:
    """Run init scripts based on enabled modules, skipping already initialized ones."""
    modules = get_modules_from_ops_config(project_path)
    module_init_scripts = get_module_init_scripts(project_path)
    
    if not modules:
        print("No modules defined in .ops-config. Skipping init scripts.")
        return
    
    # Get database config to check initialization status
    backend = "sqlite"
    db_path = "ops_admin.db"
    
    try:
        db_config, _ = read_database_config(project_path)
        backend = db_config.get("backend", "sqlite")
        db_path = db_config.get("sqlite_path", db_path)
    except Exception:
        pass
    
    initialized = check_already_initialized(project_path, backend, db_path)
    
    # Filter scripts based on enabled modules
    scripts_to_run = []
    for module in modules:
        script_name = module_init_scripts.get(module)
        if script_name:
            scripts_to_run.append((module, script_name))
    
    print(f"\nFound {len(scripts_to_run)} init scripts to process")
    
    for module, script_name in scripts_to_run:
        script_path = project_path / "scripts" / script_name
        
        if module in initialized:
            print(f"  ✓ {script_name} - already initialized, skipping")
            continue
        
        if script_path.exists():
            print(f"  Running {script_name}...")
            try:
                result = subprocess.run(
                    [str(python_exe), str(script_path)],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    print(f"    ✓ {script_name} completed")
                else:
                    error_msg = result.stderr[:200] if result.stderr else "unknown error"
                    print(f"    ✗ {script_name} failed: {error_msg}")
            except subprocess.TimeoutExpired:
                print(f"    ✗ {script_name} timed out")
            except Exception as e:
                print(f"    ✗ {script_name} error: {e}")
        else:
            print(f"    - {script_name} not found, skipping")


def run_setup(args) -> None:
    """Configure project database and run init scripts."""
    config = get_config()
    projects_dir = Path(config.get("projects_dir"))
    
    # Detect project
    project_name = args.name
    project_info = None
    
    if project_name:
        project_info = config.get_project(project_name)
        if not project_info:
            print(f"Error: Project '{project_name}' not found.")
            return
    else:
        # Try to detect from current directory
        detected = detect_project_from_dir(projects_dir)
        if detected:
            project_name, project_info = detected
            print(f"Detected project from current directory: {project_name}")
        else:
            # Show selection
            projects = config.get_projects()
            if not projects:
                print("No projects found. Use 'ops-cli init' to create one first.")
                return
            
            print("\nSelect a project to configure:")
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
    
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        return
    
    print("\n" + "=" * 50)
    print(f"Setting up project: {project_name}")
    print("=" * 50)
    print(f"Path: {project_path}")
    print()
    
    # Check for command line args first, otherwise use existing config or ask
    existing_config, existing_config_path = read_database_config(project_path)
    
    # Check if already configured (for linked projects)
    if existing_config_path and existing_config and not args.database and not args.database_url:
        print("Database config already exists:")
        try:
            existing = existing_config
            print(f"  Backend: {existing.get('backend', 'unknown')}")
            if existing.get('database_url'):
                print(f"  URL: {existing.get('database_url')}")
            elif existing.get('sqlite_path'):
                print(f"  Path: {existing.get('sqlite_path')}")
        except Exception:
            pass
        
        use_existing = input("\nUse existing config? [Y/n]: ").strip().lower()
        if use_existing not in ('n', 'no'):
            # Skip database config, go to init scripts
            print("Using existing database config.")
            # Continue to init scripts section
            _continue_to_init_scripts = True
        else:
            _continue_to_init_scripts = False
            # Fall through to reconfigure
    else:
        _continue_to_init_scripts = False
    
    # Determine backend
    if _continue_to_init_scripts:
        # Use existing config, don't ask
        backend = existing_config.get("backend", "sqlite") if existing_config else "sqlite"
        db_kwargs = {}
    elif args.database:
        backend = args.database
        db_kwargs = {}
    elif existing_config:
        backend = existing_config.get("backend", "sqlite")
    else:
        backend = None
    
    if not backend:
        # Step 1: Choose database type
        print("Step 1: Database Type")
        print("-" * 40)
        backend = ask_with_choices(
            "Database type",
            ["sqlite", "mysql", "postgres"],
            default="sqlite"
        )
        print(f"Selected: {backend}")
        print()
    
    print(f"Database type: {backend}")
    
    db_kwargs = {}
    
    # Skip db config if using existing
    if not _continue_to_init_scripts:
        # Step 2: Get connection details for non-sqlite
        if backend in ("mysql", "postgres"):
            if args.database_url:
                db_kwargs["database_url"] = args.database_url
            elif existing_config:
                db_kwargs["database_url"] = existing_config.get("database_url", "")
            
            if "database_url" not in db_kwargs or not db_kwargs["database_url"]:
                print("\nStep 2: Database Connection")
                print("-" * 40)
                while True:
                    url = input("Database URL (e.g., mysql://user:pass@localhost:3306/db): ").strip()
                    if url:
                        db_kwargs["database_url"] = url
                        break
                    print("Database URL is required.")
        else:
            # SQLite path
            if args.sqlite_path:
                db_kwargs["sqlite_path"] = args.sqlite_path
            elif existing_config:
                db_kwargs["sqlite_path"] = existing_config.get("sqlite_path", "ops_admin.db")
            
            if "sqlite_path" not in db_kwargs:
                print("\nStep 2: SQLite Database Path")
                print("-" * 40)
                db_path = input("SQLite database path [ops_admin.db]: ").strip()
                db_kwargs["sqlite_path"] = db_path or "ops_admin.db"
        
        print()
        
        # Step 3: Write config
        print("\nStep 3: Writing Configuration")
        print("-" * 40)
        write_database_config(project_path, backend, **db_kwargs)
        
        # Step 4: Create database if needed (for MySQL/PostgreSQL)
        if backend in ("mysql", "postgres") and "database_url" in db_kwargs:
            print("\nStep 4: Creating Database")
            print("-" * 40)
            create_database_if_not_exists(backend, db_kwargs["database_url"])
    
    # Step 5: Init script mode selection
    print("\nStep 5: Initialization Scripts")
    print("-" * 40)
    print("Select initialization mode:")
    print("  1. Skip init scripts (use existing database)")
    print("  2. Run init scripts (initialize/reset database)")
    
    init_mode = input("Choice [1]: ").strip() or "1"
    
    # Step 6: Create venv (always, for linked projects too)
    print("\nStep 6: Virtual Environment")
    print("-" * 40)
    python_ok, python_version = check_python_available()
    if not python_ok:
        print("Python not found. Skipping venv creation.")
    else:
        print(f"Python: {python_version}")
        
        venv_path = project_path / ".venv"
        if venv_path.exists():
            print(f"Virtual environment already exists at: {venv_path}")
        else:
            print("Creating virtual environment...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_path)],
                    cwd=project_path,
                    check=True,
                )
                print("Virtual environment created.")
            except Exception as e:
                print(f"Failed to create venv: {e}")
        
        # Install dependencies if needed
        python_exe = get_venv_python(project_path)
        deps_ok = False
        try:
            result = subprocess.run(
                [str(python_exe), "-c", "import fastapi"],
                capture_output=True,
                timeout=30,
            )
            deps_ok = result.returncode == 0
        except Exception:
            pass
        
        if not deps_ok:
            print("Installing Python dependencies...")
            requirements = project_path / "requirements.txt"
            if requirements.exists():
                try:
                    subprocess.run(
                        [str(python_exe), "-m", "pip", "install", "-r", str(requirements)],
                        cwd=project_path,
                        check=True,
                        timeout=600,
                    )
                    print("Dependencies installed.")
                except Exception as e:
                    print(f"Warning: Failed to install dependencies: {e}")
            else:
                # Try editable install from project
                try:
                    subprocess.run(
                        [str(python_exe), "-m", "pip", "install", "-e", "."],
                        cwd=project_path,
                        check=True,
                        timeout=600,
                    )
                    print("Dependencies installed.")
                except Exception as e:
                    print(f"Warning: Failed to install dependencies: {e}")
    
    if init_mode == "1":
        print("\nInit scripts skipped.")
        print("\n" + "=" * 50)
        print("Setup Complete!")
        print("=" * 50)
        if backend:
            print(f"Database: {backend}")
        print()
        print("Run 'ops-cli run' to start the project.")
        print("Or run 'ops-cli deploy' to deploy to server.")
        return
    
    # Continue with init scripts if user chose option 2
    print("\nRunning init scripts...")
    
    # Get venv python (already created in Step 6)
    python_exe = get_venv_python(project_path)
    
    if not python_exe.exists():
        print("Python not found. Init scripts will be skipped.")
        print("Run 'ops-cli setup' again to create the environment.")
    else:
        run_init_scripts(project_path, python_exe)
    
    print("\n" + "=" * 50)
    print("Database Configuration Complete!")
    print("=" * 50)
    
    print("\n" + "=" * 50)
    print("Database Configuration Complete!")
    print("=" * 50)
    print(f"Database: {backend}")
    if backend == "sqlite":
        print(f"Path: {db_kwargs.get('sqlite_path')}")
    else:
        url = db_kwargs.get('database_url', '')
        # Mask password in display
        if '@' in url:
            parts = url.split('@')
            if ':' in parts[0]:
                user_part = parts[0].split(':')[0] + ':***'
                url = user_part + '@' + parts[1]
        print(f"URL: {url}")
    print()
    print("Note: Run 'ops-cli run' to start the project.")
    print("      The project will handle virtual environment setup on first run.")
