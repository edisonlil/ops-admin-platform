"""
Run command - start the current project.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import os
from pathlib import Path

from ..config import get_config
from ..utils import is_windows


def get_project_requirements(project_path: Path) -> dict:
    """Get project version requirements."""
    req_file = project_path / ".ops-requirements.json"
    if req_file.exists():
        try:
            with open(req_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"python": ">=3.11", "node": ">=18"}


def parse_node_version(output: str) -> tuple:
    """Parse node version from output like 'v20.19.0'."""
    match = re.search(r'v?(\d+)\.(\d+)\.(\d+)', output)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return (0, 0, 0)


def check_nvm_available() -> bool:
    """Check if nvm is available."""
    try:
        result = subprocess.run(
            ["nvm", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def switch_node_version(required_version: str) -> bool:
    """Switch Node.js version using nvm."""
    if not is_windows():
        # On Windows, nvm is usually a batch file
        nvm_cmd = "nvm"
    else:
        # Try nvm for Windows (nvm-windows)
        nvm_cmd = "nvm"
    
    try:
        # Parse required version (e.g., "20.19.0" or ">=18")
        match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', required_version)
        if not match:
            print(f"Cannot parse Node version requirement: {required_version}")
            return False
        
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3)) if match.group(3) else 0
        
        # Check if version is already installed
        result = subprocess.run(
            [nvm_cmd, "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # Look for installed version
        version_str = f"{major}.{minor}.{patch}"
        if version_str in result.stdout:
            print(f"Node.js {version_str} is already installed.")
        else:
            print(f"Installing Node.js {version_str}...")
            install_result = subprocess.run(
                [nvm_cmd, "install", version_str],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if install_result.returncode != 0:
                print(f"Failed to install Node.js {version_str}")
                print(install_result.stderr)
                return False
            print(f"Node.js {version_str} installed.")
        
        # Use the version
        print(f"Switching to Node.js {version_str}...")
        use_result = subprocess.run(
            [nvm_cmd, "use", version_str],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if use_result.returncode == 0:
            print(f"Switched to Node.js {version_str}")
            return True
        else:
            print(f"Failed to switch Node.js version")
            print(use_result.stderr)
            return False
            
    except Exception as e:
        print(f"NVM error: {e}")
        return False


def check_python_version() -> tuple[bool, str]:
    """Check if Python version is compatible."""
    project_req = get_project_requirements(Path.cwd())
    required = project_req.get("python", ">=3.11")
    
    try:
        result = subprocess.run(
            ["python", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            current = parse_node_version(result.stdout)  # Reuse parser for python
            # Parse required
            match = re.search(r'(\d+)\.(\d+)', required)
            if match:
                req = (int(match.group(1)), int(match.group(2)))
                return current[:2] >= req, result.stdout.strip()
    except Exception:
        pass
    return False, "Python not found"


def run_run(args) -> None:
    """Start the current project."""
    config = get_config()
    
    # Get port settings
    backend_port = args.backend_port if hasattr(args, 'backend_port') else 8000
    frontend_port = args.frontend_port if hasattr(args, 'frontend_port') else 8001
    only_backend = args.only_backend if hasattr(args, 'only_backend') else False
    only_frontend = args.only_frontend if hasattr(args, 'only_frontend') else False

    # Get current project
    project_info = config.get_current_project()
    if not project_info:
        print("\nNo current project selected.")
        print("Use 'ops-cli switch <name>' to switch to a project first.")
        return

    project_path = Path(project_info["path"])

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        return

    print(f"\nStarting project: {config.load().get('current_project')}")
    print("=" * 50)

    # Check Python version
    python_ok, python_version = check_python_version()
    if python_ok:
        print(f"Python: {python_version}")
    else:
        print("Warning: Python version may be incompatible")

    # Check Node.js version
    project_req = get_project_requirements(project_path)
    required_node = project_req.get("node", ">=18")
    
    try:
        node_result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if node_result.returncode == 0:
            current_node = parse_node_version(node_result.stdout.strip())
            req_match = re.search(r'(\d+)\.(\d+)', required_node)
            if req_match:
                required_tuple = (int(req_match.group(1)), int(req_match.group(2)))
                if current_node[:2] < required_tuple:
                    print(f"Node.js version mismatch!")
                    print(f"  Current:  {node_result.stdout.strip()}")
                    print(f"  Required:  {required_node}")
                    
                    if check_nvm_available():
                        print("Switching Node.js version using nvm...")
                        if switch_node_version(required_node):
                            print("Node.js version switched successfully.")
                        else:
                            print("Failed to switch Node.js version.")
                    else:
                        print("NVM not found. Please install a compatible Node.js version manually.")
    except Exception as e:
        print(f"Node.js check failed: {e}")

    # Check venv
    venv_path = project_path / ".venv"
    if is_windows():
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        print("\nVirtual environment not found.")
        print("\nChecking project status...")
        
        # Check if deps are installed in system Python
        deps_ok = False
        try:
            result = subprocess.run(
                ["python", "-c", "import fastapi, uvicorn"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            deps_ok = result.returncode == 0
        except Exception:
            pass
        
        # Check if node_modules exists
        frontend_path = project_path / "web" / "admin"
        node_modules_ok = frontend_path.exists() and (frontend_path / "node_modules").exists()
        
        if deps_ok and node_modules_ok:
            print(f"  Python deps: OK (system)")
            print(f"  Node modules: {'OK' if node_modules_ok else 'missing'}")
            print("\nNo venv, but environment looks ready. Starting anyway...")
            python_exe = Path(sys.executable)  # Use system python
            venv_exists = False
        else:
            print(f"  Python deps: {'OK' if deps_ok else 'missing'}")
            print(f"  Node modules: {'OK' if node_modules_ok else 'missing'}")
            print("\nEnvironment not ready. Please run 'ops-cli setup' first.")
            return
    else:
        print(f"Using Python: {python_exe}")
        venv_exists = True

    # Check database config
    db_config = project_path / "config" / "database.local.json"
    if not db_config.exists():
        print("\nDatabase not configured.")
        print("Please run 'ops-cli setup' first to configure the database.")
        return

    # Set environment variables
    os.environ["FG_AGENT_DATABASE_CONFIG"] = str(db_config.resolve())
    os.environ["FG_AGENT_CORS_ORIGINS"] = f"http://localhost:{frontend_port},http://127.0.0.1:{frontend_port}"

    # Set PYTHONPATH
    pythonpath_parts = [
        str(project_path),
        str(project_path / "packages" / "python" / "ops-admin-system" / "src"),
        str(project_path / "packages" / "python" / "ops-admin-identity-access" / "src"),
        str(project_path / "packages" / "python" / "ops-admin-messaging" / "src"),
        str(project_path / "packages" / "python" / "ops-admin-appearance" / "src"),
        str(project_path / "packages" / "python" / "ops-admin-llm-runtime" / "src"),
    ]
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    os.environ["PYTHONPATH"] = ";".join(pythonpath_parts)

    # Start backend (skip if --only-frontend)
    if not only_frontend:
        print(f"\nStarting backend on port {backend_port}...")
        backend_proc = subprocess.Popen(
            [str(python_exe), "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", str(backend_port), "--reload"],
            cwd=project_path,
        )

        time.sleep(3)
        if backend_proc.poll() is None:
            print(f"Backend started on http://0.0.0.0:{backend_port}")
            print(f"API docs: http://127.0.0.1:{backend_port}/docs")
        else:
            print("Backend failed to start!")
    else:
        backend_proc = None
        print("\nSkipping backend (--only-frontend)")

    # Start frontend (skip if --only-backend)
    if not only_backend:
        frontend_path = project_path / "web" / "admin"
        if frontend_path.exists() and (frontend_path / "package.json").exists():
            print(f"\nStarting frontend on port {frontend_port}...")
            
            node_modules = frontend_path / "node_modules"
            if not node_modules.exists():
                print("Installing frontend dependencies...")
                try:
                    pm = "pnpm.cmd" if is_windows() else "pnpm"
                    subprocess.run(
                        [pm, "install"],
                        cwd=frontend_path,
                        check=True,
                        timeout=600,
                    )
                    print("Dependencies installed.")
                except subprocess.TimeoutExpired:
                    print("Installation timed out. Run 'pnpm install' manually.")
                except Exception as e:
                    print(f"Failed to install: {e}")
            
            try:
                pm = "pnpm.cmd" if is_windows() else "pnpm"
                # Set environment for frontend
                env = os.environ.copy()
                env["VITE_API_BASE_URL"] = f"http://127.0.0.1:{backend_port}/api"
                env["PORT"] = str(frontend_port)
                subprocess.run(
                    [pm, "run", "dev", "--", "--port", str(frontend_port)],
                    cwd=frontend_path,
                    env=env,
                )
                print(f"Frontend starting on http://127.0.0.1:{frontend_port}")
            except Exception as e:
                print(f"Failed to start frontend: {e}")
        else:
            print("\nFrontend not found.")
    else:
        print("Skipping frontend (--only-backend)")

    print("\n" + "=" * 50)
    print("Project is running!")
    if not only_frontend and backend_proc:
        print(f"  Backend:  http://127.0.0.1:{backend_port}")
    if not only_backend:
        print(f"  Frontend: http://127.0.0.1:{frontend_port}")
    print("\nPress Ctrl+C to stop...")

    try:
        if backend_proc:
            backend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping project...")
        if backend_proc:
            backend_proc.terminate()
            backend_proc.wait()