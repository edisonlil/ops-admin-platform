"""
Deploy command - deploy project to remote servers via SSH or local Docker.
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import tarfile
import tempfile
import shutil
import io
import re
import socket
from datetime import datetime
from pathlib import Path
from typing import Optional

import paramiko
from paramiko import SSHClient, AutoAddPolicy

from ..config import get_config
from ..interactive.prompts import ask_confirmation, ask_with_choices
from ..project_config import (
    application_config_path,
    read_application_config,
    read_database_config,
    write_database_config as write_application_database_config,
)
from .deploy_history import DeployHistory, format_history_list


def _safe_identifier(value: str, fallback: str = "default") -> str:
    """Sanitize a value to a docker-safe identifier segment."""
    safe = re.sub(r"[^a-z0-9_.-]", "-", str(value).lower())
    safe = re.sub(r"-{2,}", "-", safe).strip("-_.")
    if not safe:
        safe = fallback.lower().strip("-_.")
    if not safe:
        safe = "default"
    return safe[:40]


def _make_container_name(target_name: str, fallback: str = "default") -> str:
    return f"ops-admin-backend-{_safe_identifier(target_name or fallback)}"


def _normalize_deploy_host(host: str) -> str:
    host = (host or "").strip().lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host


def _is_local_deploy_host(host: str) -> bool:
    return _normalize_deploy_host(host) in {"127.0.0.1", "localhost", "::1"}


def get_deploy_targets(project_path: Optional[Path] = None) -> dict:
    """Get deploy targets from project-level config."""
    if project_path is None:
        config = get_config()
        project_info = config.get_current_project()
        if project_info:
            project_path = Path(project_info.get("path", ""))
    
    if project_path is None:
        return {}
    
    # Look for deploy config in project
    deploy_config_paths = [
        project_path / ".ops-deploy.json",
        project_path / "config" / "deploy.json",
        project_path / "config" / "deploy_targets.json",
    ]
    
    for config_path in deploy_config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    
    return {}


def save_deploy_targets(targets: dict, project_path: Path) -> None:
    """Save deploy targets to project-level config."""
    config_path = project_path / ".ops-deploy.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(targets, f, indent=2, ensure_ascii=False)


def get_project_path() -> Optional[Path]:
    """Get current project path."""
    config = get_config()
    project_info = config.get_current_project()
    if project_info:
        return Path(project_info.get("path", ""))
    return None


def get_project_info(project_path: Path) -> dict:
    """Get project build info."""
    # Check for .ops-config
    ops_config = project_path / ".ops-config"
    if ops_config.exists():
        try:
            with open(ops_config, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        "name": project_path.name,
        "modules": []
    }


def _guess_db_backend(database_url: str) -> str:
    """Infer database backend from URL prefix."""
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgresql") or database_url.startswith("postgres://"):
        return "postgres"
    if database_url.startswith("mysql://"):
        return "mysql"
    return "mysql"


def _load_db_config_for_target(project_path: Path, target_name: str, target: dict) -> tuple[dict, str]:
    """Load DB config for a deploy target.

    Priority:
    1. config/application.<target>.json (explicit target config)
    2. inline target.database_url (interactive add legacy path)
    3. config/database.<target>.json and config/database.json (legacy fallbacks)
    """
    db_config, config_path = read_database_config(project_path, target_name)
    if db_config and config_path:
        return db_config, str(config_path.relative_to(project_path))

    db_url = target.get("database_url", "")
    if db_url:
        return {
            "backend": _guess_db_backend(db_url),
            "database_url": db_url,
        }, "target.database_url"

    application_config = project_path / "config" / "application.json"
    if application_config.exists():
        with open(application_config, "r", encoding="utf-8") as f:
            payload = json.load(f)
        database = payload.get("database") if isinstance(payload, dict) else None
        if isinstance(database, dict):
            return database, "config/application.json"

    legacy_config = project_path / "config" / "database.json"
    if legacy_config.exists():
        with open(legacy_config, "r", encoding="utf-8") as f:
            return json.load(f), "config/database.json"

    return {}, "missing"


def _load_application_config_for_target(project_path: Path, target_name: str, db_config: dict) -> dict:
    app_config, _ = read_application_config(project_path, target_name)
    if app_config:
        return {**app_config, "database": db_config}

    global_config = project_path / "config" / "application.json"
    if global_config.exists():
        with open(global_config, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            return {**payload, "database": db_config}

    return {"database": db_config}


def _has_database_connection_info(db_config: dict) -> bool:
    """Return whether a database config has enough connection info for deploy."""
    if not isinstance(db_config, dict) or not db_config:
        return False

    database_url = str(db_config.get("database_url", "")).strip()
    if database_url:
        return True

    backend = str(db_config.get("backend", "")).strip().lower()
    sqlite_path = str(db_config.get("sqlite_path", "")).strip()
    if backend == "sqlite":
        return True
    if sqlite_path:
        return True

    return False


def _database_config_summary(db_config: dict) -> str:
    database_url = str(db_config.get("database_url", "")).strip()
    if database_url:
        return _mask_secret_in_url(database_url)

    backend = str(db_config.get("backend", "")).strip().lower()
    sqlite_path = str(db_config.get("sqlite_path", "")).strip()
    if backend == "sqlite" or sqlite_path:
        return f"sqlite:{sqlite_path or 'ops_admin.db'}"

    return "(missing)"


def _mask_secret_in_url(value: str) -> str:
    """Mask the password part of a URL-like secret while preserving host details."""
    if "@" not in value:
        return value

    left, right = value.rsplit("@", 1)
    if ":" not in left:
        return value

    user_part, _password = left.rsplit(":", 1)
    return f"{user_part}:***@{right}"


def _format_deploy_environment_preview(
    target_name: str,
    target: dict,
    db_config: dict,
    db_config_source: str,
) -> str:
    """Build a deployment preview summary."""
    remote_path = target.get("remote_path") or "/opt/ops-admin"
    container_port = target.get("container_port", 8000)
    container_name = _make_container_name(
        target_name,
        fallback=target.get("name", target.get("host", "default")),
    )
    ssh_port = target.get("port", 22)
    ssh_user = target.get("user") or ""
    ssh_host = target.get("host") or ""
    ssh_key = target.get("ssh_key") or ""

    lines = [
        f"Target: {target_name}",
        f"Host: {ssh_host}",
        f"Remote path: {remote_path}",
        f"Container name: {container_name}",
        f"Container port: {container_port}",
        f"Service URL: http://{ssh_host}:{container_port}",
        f"Database config source: {db_config_source}",
        f"Database: {_database_config_summary(db_config)}",
    ]
    if _is_local_deploy_host(ssh_host):
        lines.insert(2, "Mode: local Docker")
    else:
        lines.insert(2, f"SSH: {ssh_user}@{ssh_host}:{ssh_port}")
        lines.insert(3, f"SSH key: {ssh_key or '(password/agent)'}")
    return "\n".join(lines)


def _diagnose_ssh_banner_failure(host: str, port: int, timeout: float = 5.0) -> str:
    """Return a short actionable diagnosis for SSH banner failures."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            sock.settimeout(timeout)
            try:
                banner = sock.recv(256)
            except socket.timeout:
                return (
                    "TCP connection opened, but no SSH banner was received. "
                    f"Verify {host}:{port} is the SSH service port and that sshd is accepting sessions."
                )
    except ConnectionRefusedError:
        return f"Connection refused. No service is accepting TCP connections on {host}:{port}."
    except socket.timeout:
        return f"Connection timed out. Check firewall/security group/VPN routing for {host}:{port}."
    except OSError as exc:
        return f"TCP connectivity check failed for {host}:{port}: {exc}"

    if not banner:
        return (
            "TCP connection opened, but the remote side closed it before sending an SSH banner. "
            "Check sshd status, MaxStartups/rate limits, allowlists, or whether a gateway/proxy is closing the session."
        )

    first_line = banner.splitlines()[0].decode("utf-8", errors="replace").strip()
    first_line = re.sub(r"[^\x20-\x7e]", "?", first_line)[:120]
    if first_line.startswith("SSH-"):
        return (
            f"SSH banner was received during the diagnostic check ({first_line}). "
            "The earlier failure may be transient or caused by SSH server rate limiting."
        )

    return (
        f"Port {host}:{port} is reachable, but it does not look like SSH. "
        f"First response bytes: {first_line!r}. Update the deploy target SSH port or server address."
    )


def _validate_local_deploy_path(remote_path: str) -> Path:
    deploy_dir = Path(os.path.expanduser(remote_path)).resolve(strict=False)
    dangerous_paths = {
        Path("/"),
        Path("/home"),
    }
    if deploy_dir in dangerous_paths:
        raise ValueError(f"Refusing to deploy to unsafe local path: {deploy_dir}")
    return deploy_dir


def _run_local_compose_command(deploy_dir: Path, compose_args: list[str]) -> subprocess.CompletedProcess | None:
    attempts = [
        ["docker", "compose", *compose_args],
        ["docker-compose", *compose_args],
    ]
    last_result: subprocess.CompletedProcess | None = None
    for index, cmd in enumerate(attempts):
        try:
            result = subprocess.run(
                cmd,
                cwd=deploy_dir,
                capture_output=True,
                text=True,
                timeout=300,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            last_result = None
            if index == len(attempts) - 1:
                print(f"  Docker Compose command not found: {exc}")
            continue

        if result.returncode == 0:
            return result

        stderr = (result.stderr or "").lower()
        if index == 0 and ("is not a docker command" in stderr or "unknown command" in stderr):
            last_result = result
            continue

        last_result = result
        break

    return last_result


def _render_deploy_compose_content(container_name: str, container_port: int) -> str:
    return f"""version: '3.8'

services:
  backend:
    image: ops-admin:latest
    container_name: {container_name}
    ports:
      - "{container_port}:8000"
    environment:
      - OPS_ADMIN_APPLICATION_CONFIG=/app/config/application.json
      - FG_AGENT_CORS_ORIGINS=*
      - FG_AGENT_ADMIN_DIST_PATH=/app/dist
    volumes:
      - ./config:/app/config:ro
      - ./dist:/app/dist:ro
      - ./data:/app/data
    restart: unless-stopped
  cron-worker:
    image: ops-admin:latest
    container_name: {container_name}-cron-worker
    command: ["python", "scripts/run_cron_worker.py"]
    environment:
      - OPS_ADMIN_APPLICATION_CONFIG=/app/config/application.json
      - FG_AGENT_CORS_ORIGINS=*
      - FG_AGENT_ADMIN_DIST_PATH=/app/dist
    volumes:
      - ./config:/app/config:ro
      - ./dist:/app/dist:ro
      - ./data:/app/data
    depends_on:
      - backend
    restart: unless-stopped
"""


def _run_local_deploy(package_path: Path, target: dict, db_config: dict, target_name: str = "") -> bool:
    """Deploy package to the local Docker environment."""
    print("\nDeploying to local Docker environment...")

    remote_path = target.get("remote_path", "/tmp/ops-admin")
    container_port = target.get("container_port", 8000)
    container_name = _make_container_name(target_name, fallback=target.get("name", target.get("host", "default")))

    try:
        deploy_dir = _validate_local_deploy_path(remote_path)
    except ValueError as exc:
        print(f"Local deployment failed: {exc}")
        return False

    try:
        if deploy_dir.exists():
            shutil.rmtree(deploy_dir)
        deploy_dir.mkdir(parents=True, exist_ok=True)

        print(f"  Extracting deployment package to {deploy_dir}...")
        with tarfile.open(package_path, "r:gz") as tar:
            tar.extractall(deploy_dir)

        print("  Stopping existing container...")
        _run_local_compose_command(deploy_dir, ["down"])

        print("  Building Docker image...")
        build_result = subprocess.run(
            ["docker", "build", "-t", "ops-admin:latest", "."],
            cwd=deploy_dir,
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
        if build_result.returncode != 0:
            print(f"  docker build failed: {build_result.stderr or build_result.stdout}")
            return False

        print("  Starting container...")
        up_result = _run_local_compose_command(deploy_dir, ["up", "-d"])
        if up_result is None or up_result.returncode != 0:
            message = ""
            if up_result is not None:
                message = up_result.stderr or up_result.stdout or ""
            print(f"  docker compose up failed: {message}")
            return False

        print("  Verifying container status...")
        ps_result = subprocess.run(
            ["docker", "ps", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
            cwd=deploy_dir,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        if container_name not in (ps_result.stdout or ""):
            print(f"  Container '{container_name}' did not start successfully.")
            return False

        print("\n" + "=" * 50)
        print("Deployment Successful!")
        print("=" * 50)
        print(f"Target: {target_name}")
        print(f"Host: {target.get('host')}")
        print(f"URL: http://{target.get('host')}:{container_port}")
        return True
    except subprocess.TimeoutExpired:
        print("Local deployment timed out.")
        return False
    except Exception as exc:
        print(f"Local deployment failed: {exc}")
        return False


def _clone_json_value(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def copy_deploy_environment(
    project_path: Path,
    source_name: str,
    dest_name: str,
    overrides: Optional[dict] = None,
) -> tuple[bool, str]:
    """Copy deploy target and application environment config from one target to another."""
    source_name = (source_name or "").strip()
    dest_name = (dest_name or "").strip()
    if not source_name or not dest_name:
        return False, "Source and destination target names are required."
    if source_name == dest_name:
        return False, "Source and destination target names must be different."

    targets = get_deploy_targets(project_path)
    if source_name not in targets:
        return False, f"Source target '{source_name}' not found."
    if dest_name in targets:
        return False, f"Destination target '{dest_name}' already exists."

    copied_target = _clone_json_value(targets[source_name])
    for key, value in (overrides or {}).items():
        if value is not None and value != "":
            copied_target[key] = value
    targets[dest_name] = copied_target
    save_deploy_targets(targets, project_path)

    source_app_config, source_app_path = read_application_config(project_path, source_name)
    if source_app_path and source_app_config:
        dest_app_path = application_config_path(project_path, dest_name)
        dest_app_path.parent.mkdir(exist_ok=True)
        with open(dest_app_path, "w", encoding="utf-8") as f:
            json.dump(source_app_config, f, indent=2, ensure_ascii=False)
        return True, f"Copied deploy target and {source_app_path.name} to {dest_app_path.name}."

    db_config, db_source = read_database_config(project_path, source_name)
    if db_config:
        dest_path = write_application_database_config(project_path, db_config, env=dest_name)
        return True, f"Copied deploy target and database config from {Path(db_source).name} to {dest_path.name}."

    return True, "Copied deploy target. No source application config was found to copy."


def update_deploy_environment(project_path: Path, target_name: str, updates: dict) -> tuple[bool, str]:
    """Update saved deploy target environment fields."""
    target_name = (target_name or "").strip()
    if not target_name:
        return False, "Target name is required."

    allowed_fields = {"remote_path", "container_port", "host", "port", "user", "ssh_key"}
    clean_updates = {
        key: value
        for key, value in (updates or {}).items()
        if key in allowed_fields and value is not None and value != ""
    }
    if not clean_updates:
        return False, "No environment updates provided."

    targets = get_deploy_targets(project_path)
    if target_name not in targets:
        return False, f"Target '{target_name}' not found."

    targets[target_name].update(clean_updates)
    save_deploy_targets(targets, project_path)

    changed = ", ".join(f"{key}={value}" for key, value in clean_updates.items())
    return True, f"Updated target '{target_name}': {changed}."


def _existing_database_config_for_new_target(project_path: Path, target_name: str) -> tuple[dict, str] | None:
    """Return an existing target database config if it is usable for deployment."""
    db_config, db_config_source = _load_db_config_for_target(project_path, target_name, {})
    if _has_database_connection_info(db_config):
        return db_config, db_config_source
    return None


def _resolve_deploy_config_env(target_name: str, target: dict) -> str:
    """Resolve which application config environment a target should use."""
    return str(target.get("database_env") or target_name or "local").strip() or "local"


def run_build(project_path: Path) -> bool:
    """Build frontend."""
    frontend_path = project_path / "web" / "admin"
    if not frontend_path.exists():
        print("Frontend not found.")
        return False
    
    print("\nBuilding frontend...")
    try:
        pm = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
        
        # Install dependencies if needed
        node_modules = frontend_path / "node_modules"
        if not node_modules.exists():
            print("Installing frontend dependencies...")
            subprocess.run(
                [pm, "install"],
                cwd=frontend_path,
                check=True,
                timeout=600,
                encoding="utf-8",
                errors="replace",
            )
        
        # Build
        result = subprocess.run(
            [pm, "run", "build"],
            cwd=frontend_path,
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
        
        if result.returncode == 0:
            print("Frontend built successfully.")
            return True
        else:
            print(f"Frontend build failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("Frontend build timed out.")
        return False
    except Exception as e:
        print(f"Frontend build error: {e}")
        return False


def create_deploy_package(
    project_path: Path,
    output_path: Path,
    db_config: dict,
    target_name: str = "",
    remote_path: str = "/opt/ops-admin",
    container_port: int = 8000,
) -> bool:
    """Create deployment package (source + config, no Docker image)."""
    print("\nCreating deployment package...")
    container_name = _make_container_name(target_name)
    
    dist_path = project_path / "web" / "admin" / "dist"
    
    # Files to include in package
    include_patterns = [
        "api",
        "packages/python",
        "scripts",
        "requirements.txt",
    ]
    
    # Docker files may not exist in project - check scaffold root
    # scaffold root is the ops-admin-platform repo
    import ops_cli
    scaffold_root = Path(ops_cli.__file__).parent.parent.parent.parent
    # Note: .dockerignore is excluded to avoid excluding dist/ during Docker build
    docker_files = ["Dockerfile", "docker-compose.yml"]
    
    try:
        with tarfile.open(output_path, "w:gz") as tar:
            # Add frontend dist
            if dist_path.exists():
                print(f"  Adding frontend dist from {dist_path}...")
                # List contents
                for f in dist_path.iterdir():
                    print(f"    - {f.name}")
                tar.add(str(dist_path), arcname="dist")
                # Verify it was added
                print(f"  dist/ added successfully")
            else:
                print(f"  Warning: frontend dist not found at {dist_path}")
            
            # Add source code directories
            for pattern in include_patterns:
                src = project_path / pattern
                if src.exists():
                    print(f"  Adding {pattern}...")
                    tar.add(src, arcname=pattern)
            
            # Add Docker files from project or scaffold
            for docker_file in docker_files:
                src_project = project_path / docker_file
                src_scaffold = scaffold_root / docker_file
                
                if src_project.exists():
                    print(f"  Adding {docker_file}...")
                    tar.add(src_project, arcname=docker_file)
                elif src_scaffold.exists():
                    print(f"  Adding {docker_file} (from scaffold)...")
                    tar.add(src_scaffold, arcname=docker_file)
            
            # Add application config
            print("  Adding application config...")
            app_config = _load_application_config_for_target(project_path, target_name, db_config)
            config_json = json.dumps(app_config, indent=2, ensure_ascii=False)
            config_data = config_json.encode("utf-8")
            config_file = io.BytesIO(config_data)
            tarinfo = tarfile.TarInfo(name="config/application.json")
            config_file.seek(0, 2)
            tarinfo.size = config_file.tell()
            config_file.seek(0)
            tar.addfile(tarinfo, config_file)

            # Add deploy-specific docker-compose.yml to keep runtime defaults consistent.
            compose_json = _render_deploy_compose_content(container_name, container_port)
            compose_data = compose_json.encode("utf-8")
            compose_file = io.BytesIO(compose_data)
            compose_info = tarfile.TarInfo(name="docker-compose.yml")
            compose_file.seek(0, 2)
            compose_info.size = compose_file.tell()
            compose_file.seek(0)
            tar.addfile(compose_info, compose_file)
            
            # Add build script with dynamic remote_path
            build_script = f"""#!/bin/bash
set -e

DEPLOY_DIR="{remote_path}"
CONTAINER_NAME="{container_name}"
REQUIRED_DIRS=("api" "packages" "dist")
docker_cmd() {{
  if [ "$(id -u)" -eq 0 ]; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}}

compose_cmd() {{
  if [ "$(id -u)" -eq 0 ]; then
    docker-compose "$@"
  else
    sudo docker-compose "$@"
  fi
}}

echo "Starting deployment..."

# Safety check 1: Verify we're in the correct deployment directory
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Deployment directory $DEPLOY_DIR does not exist"
    exit 1
fi

cd "$DEPLOY_DIR"
echo "Working directory: $(pwd)"

# Safety check 2: Verify required directories exist
echo "Verifying deployment package..."
ls -la

MISSING=()
for d in "${{REQUIRED_DIRS[@]}}"; do
    if [ ! -d "$d" ]; then
        MISSING+=("$d")
        echo "  Missing: $d"
    else
        echo "  Found: $d"
    fi
done

# Debug: list dist contents
if [ -d "dist" ]; then
    echo "  dist/ contents:"
    ls -la dist/ | head -10
fi
if [ ${{#MISSING[@]}} -gt 0 ]; then
    echo "ERROR: Missing required directories: ${{MISSING[*]}}"
    ls -la
    exit 1
fi

# Safety check 3: Verify Dockerfile exists (should be in root)
if [ ! -f "Dockerfile" ]; then
    echo "ERROR: Dockerfile not found"
    ls *.txt *.yml 2>/dev/null || true
    exit 1
fi

# Safety check 4: Verify Dockerfile has multi-stage build
if ! grep -q "^FROM" Dockerfile; then
    echo "ERROR: Dockerfile appears invalid (no FROM instruction)"
    exit 1
fi

# Create .dockerignore to allow dist/ (scaffold's .dockerignore excludes it)
echo "Creating .dockerignore to allow dist/..."
cat > .dockerignore << 'DOCKERIGNORE_EOF'
# Allow dist/ for deployment
!dist/**
!dist/

# Exclude other large directories
node_modules/
__pycache__/
*.pyc
.venv/
.vscode/
.idea/
.git/
DOCKERIGNORE_EOF

# Verify dist exists
echo "Verifying dist/ exists..."
if [ ! -d "dist" ]; then
    echo "ERROR: dist/ directory not found!"
    ls -la | grep dist || echo "dist not in ls"
    exit 1
fi
echo "dist/ found, contents:"
ls -la dist/ | head -5

# Stop existing container
echo "Stopping existing container..."
compose_cmd down 2>/dev/null || true

# Remove existing container with the same name to avoid name conflict
if [ -n "$CONTAINER_NAME" ]; then
    EXISTING_IDS=$(docker_cmd ps -aq --filter "name=^/$CONTAINER_NAME$")
    if [ -n "$EXISTING_IDS" ]; then
        echo "Removing existing container: $CONTAINER_NAME"
        echo "$EXISTING_IDS" | xargs -r docker_cmd rm -f
    fi
fi

# Build image
echo "Building Docker image..."
docker_cmd build -t ops-admin:latest . 2>&1 | tee /tmp/ops-admin-build.log
if [ ${{PIPESTATUS[0]}} -ne 0 ]; then
    echo "ERROR: docker build failed. Showing /tmp/ops-admin-build.log"
    tail -n 200 /tmp/ops-admin-build.log
    exit 1
fi

# Verify image was built successfully
if ! docker_cmd image inspect ops-admin:latest > /dev/null 2>&1; then
    echo "ERROR: Docker image build failed"
    exit 1
fi

# Start container
echo "Starting container..."
compose_cmd up -d

# Verify container is running
sleep 3
if ! docker_cmd ps | grep -q "$CONTAINER_NAME"; then
    echo "ERROR: Container failed to start"
    exit 1
fi

echo "Build completed. Cleaning up source code..."

# Safety check 5: Verify we're not in root or home directory
if [ "$DEPLOY_DIR" = "/" ] || [ "$DEPLOY_DIR" = "/home" ] || [ "$DEPLOY_DIR" = "$HOME" ]; then
    echo "ERROR: Safety check failed - refusing to delete in root/home directory"
    exit 1
fi

# Safety check 6: Verify at least Dockerfile exists (critical for build)
if [ ! -f "Dockerfile" ]; then
    echo "ERROR: Dockerfile missing - cannot build image"
    exit 1
fi

# Safety check 7: Verify expected directories still exist before cleanup
if [ ! -d "api" ] || [ ! -d "packages" ]; then
    echo "ERROR: Directory structure mismatch - aborting cleanup"
    exit 1
fi

# Clean up source code (keep only runtime files and config)
echo "Removing source code directories..."
rm -rf api packages scripts *.txt Dockerfile .dockerignore ops-deploy.tar.gz deploy.sh 2>/dev/null || true

# Verify cleanup was successful (directories should not exist)
if [ -d "api" ] || [ -d "packages" ]; then
    echo "WARNING: Source directories still exist, manual cleanup required"
else
    echo "Source code cleaned up successfully"
fi

echo ""
echo "Deployment completed!"
if [ -n "$CONTAINER_NAME" ]; then
    docker_cmd ps | grep "$CONTAINER_NAME"
fi
"""
            script_data = build_script.encode("utf-8")
            script_file = io.BytesIO(script_data)
            tarinfo = tarfile.TarInfo(name="deploy.sh")
            script_file.seek(0, 2)
            tarinfo.size = script_file.tell()
            script_file.seek(0)
            tar.addfile(tarinfo, script_file)
        
        print(f"Deployment package created: {output_path}")
        return True
    except Exception as e:
        print(f"Failed to create package: {e}")
        return False


def do_deploy(package_path: Path, target: dict, db_config: dict, target_name: str = "") -> bool:
    """Deploy package to target server via SSH and build on server."""
    print("\nDeploying to target server...")
    
    host = target.get("host", "")
    port = target.get("port", 22)
    user = target.get("user", "")
    ssh_key = target.get("ssh_key", "")
    password = target.get("password", "")
    remote_path = target.get("remote_path", "/opt/ops-admin")
    container_port = target.get("container_port", 8000)
    container_name = _make_container_name(target_name, fallback=target.get("name", target.get("host", "default")))
    
    if not all([host, user]):
        print("Missing target configuration.")
        return False
    
    # Initialize history
    config = get_config()
    config_path = Path(config.get("config_path", "")).parent
    history = DeployHistory(config_path)
    
    # Generate version
    version = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # Create SSH client
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    
    connect_kwargs = {
        "hostname": host,
        "port": int(port),
        "username": user,
        "look_for_keys": False,
        "allow_agent": False,
        "timeout": 30,
    }
    
    # Auth method: password or key
    if password:
        connect_kwargs["password"] = password
    elif ssh_key:
        connect_kwargs["key_filename"] = os.path.expanduser(ssh_key)
    else:
        connect_kwargs["look_for_keys"] = True
        connect_kwargs["allow_agent"] = True
    
    try:
        print(f"  Connecting to {host}:{port}...")
        client.connect(**connect_kwargs)
        print("  Connected.")
    except Exception as e:
        print(f"SSH connection failed: {e}")
        if "Error reading SSH protocol banner" in str(e):
            print(f"SSH diagnostic: {_diagnose_ssh_banner_failure(host, int(port))}")
        return False
    
    # SFTP upload - upload tar package first, then extract
    print(f"  Uploading deployment package to {host}...")
    try:
        sftp = client.open_sftp()
        
        # Ensure remote directory exists
        stdin, stdout, stderr = client.exec_command(f"rm -rf {remote_path} && mkdir -p {remote_path}")
        stdout.channel.recv_exit_status()
        
        # Upload tar package
        print(f"  Uploading package...")
        remote_tar = f"{remote_path}/deploy.tar.gz"
        sftp.put(str(package_path), remote_tar)
        
        # Extract on server
        print(f"  Extracting package...")
        stdin, stdout, stderr = client.exec_command(f"cd {remote_path} && tar -xzf deploy.tar.gz && rm -f deploy.tar.gz")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"  Extract failed: {stderr.read().decode()}")
            client.close()
            return False
        
        sftp.close()
        print("  Package uploaded and extracted.")
    except Exception as e:
        import traceback
        print(f"Upload failed: {e}")
        client.close()
        return False
    except Exception as e:
        import traceback
        print(f"Upload failed: {e}")
        client.close()
        return False
    
    # Execute build on server via docker exec
    print(f"  Building on server...")
    
    # Generate docker-compose.yml content with configurable port
    compose_content = _render_deploy_compose_content(container_name, container_port)
    
    # Build script content
    build_script = f'''#!/bin/bash
set -e

PORT={container_port}
DEPLOY_DIR="{remote_path}"
CONTAINER_NAME="{container_name}"

echo "Starting deployment..."

# Health check helper for root/non-root users
docker_cmd() {{
  if [ "$(id -u)" -eq 0 ]; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}}

compose_cmd() {{
  if [ "$(id -u)" -eq 0 ]; then
    docker-compose "$@"
  else
    sudo docker-compose "$@"
  fi
}}

# Stop existing container
echo "Stopping existing container..."
compose_cmd down 2>/dev/null || true

# Remove existing container with the same name to avoid name conflict
if [ -n "$CONTAINER_NAME" ]; then
    EXISTING_IDS=$(docker_cmd ps -aq --filter "name=^/$CONTAINER_NAME$")
    if [ -n "$EXISTING_IDS" ]; then
        echo "Removing existing container: $CONTAINER_NAME"
        echo "$EXISTING_IDS" | xargs -r docker_cmd rm -f
    fi
fi

# Write docker-compose.yml with configured port
cat > "$DEPLOY_DIR/docker-compose.yml" << 'COMPOSE_EOF'
{compose_content}COMPOSE_EOF

# Build image
echo "Building Docker image..."
docker_cmd build -t ops-admin:latest . 2>&1 | tee /tmp/ops-admin-build.log
if [ ${{PIPESTATUS[0]}} -ne 0 ]; then
    echo "ERROR: docker build failed. Showing /tmp/ops-admin-build.log"
    tail -n 200 /tmp/ops-admin-build.log
    exit 1
fi

# Verify image was built successfully
if ! docker_cmd image inspect ops-admin:latest > /dev/null 2>&1; then
    echo "ERROR: Docker image build failed"
    exit 1
fi

# Start container
echo "Starting container..."
compose_cmd up -d

# Verify container is running
sleep 3
if ! docker_cmd ps | grep -q "$CONTAINER_NAME"; then
    echo "ERROR: Container failed to start"
    docker_cmd logs "$CONTAINER_NAME" 2>&1 | tail -20
    exit 1
fi

echo "Build completed. Cleaning up source code..."

# Clean up source code (keep only runtime files and config)
echo "Removing source code directories..."
rm -rf api packages scripts *.txt Dockerfile .dockerignore deploy.sh 2>/dev/null || true

# Verify cleanup was successful
if [ -d "api" ] || [ -d "packages" ]; then
    echo "WARNING: Source directories still exist, manual cleanup required"
else
    echo "Source code cleaned up successfully"
fi

echo ""
echo "Deployment completed!"
if [ -n "$CONTAINER_NAME" ]; then
    docker_cmd ps | grep "$CONTAINER_NAME"
fi
'''
    
    # Write build script to server
    print(f"  Writing deployment script...")
    stdin, stdout, stderr = client.exec_command(f"cat > {remote_path}/deploy.sh << 'SCRIPT_EOF'\n{build_script}SCRIPT_EOF")
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode("utf-8", errors="replace")
        print(f"  Failed to write script: {err}")
        client.close()
        return False
    
    # Run build script
    print(f"  Running deployment script...")
    channel = client.exec_command(f"cd {remote_path} && chmod +x deploy.sh && bash -x ./deploy.sh 2>&1")
    
    stdout = channel[1]
    stderr = channel[2]
    
    while True:
        readable, _, _ = select.select([stdout.channel, stderr.channel], [], [])
        if stdout.channel in readable and stdout.channel.recv_ready():
            data = stdout.read(4096).decode()
            if data:
                print(data, end="")
        if stderr.channel in readable and stderr.channel.recv_ready():
            data = stderr.read(4096).decode()
            if data:
                print(data, end="", file=sys.stderr)
        if stdout.channel.exit_status_ready():
            break
    
    exit_status = stdout.channel.recv_exit_status()
    client.close()
    
    if exit_status == 0:
        print("\n  Deployment completed!")
        
        # Record successful deployment
        if target_name:
            history.record(target_name, version, "ops-admin:latest", True, f"Deployed to {host}")
        
        # Health check
        print("\n  Running health check...")
        health_ok, health_msg = check_deploy_health(host, container_port)
        if health_ok:
            print(f"  ✓ Health check passed: {health_msg}")
        else:
            print(f"  ⚠ Health check failed: {health_msg}")
        
        return True
    else:
        print("\n  Deployment failed.")
        
        # Try to get docker logs
        print("\n  Checking container logs...")
        try:
            stdin, stdout, stderr = client.exec_command(
                f"if [ \"$(id -u)\" -eq 0 ]; then docker logs {container_name}; else sudo docker logs {container_name}; fi 2>&1 | tail -30"
            )
            logs = stdout.read().decode("utf-8", errors="replace")
            if logs:
                print("  Container logs:")
                for line in logs.split("\n"):
                    if line.strip():
                        print(f"    {line}")
        except Exception:
            pass
        
        # Record failed deployment
        if target_name:
            history.record(target_name, version, "ops-admin:latest", False, f"Failed: exit {exit_status}")
        
        return False


def check_deploy_health(host: str, port: int, timeout: int = 30) -> tuple[bool, str]:
    """Check if deployed service is healthy."""
    try:
        import urllib.request
        url = f"http://{host}:{port}/api/health"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "ops-cli-deploy-check")
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = response.read().decode()
                try:
                    import json
                    result = json.loads(data)
                    status = result.get("data", {}).get("status", "unknown")
                    return True, f"status={status}"
                except Exception:
                    return True, f"HTTP {response.status}"
            else:
                return False, f"HTTP {response.status}"
    except Exception as e:
        return False, str(e)[:100]


def run_container_cmd(args) -> None:
    """Handle container subcommands: status, start, stop, restart, logs, health, shell."""
    # Import here to avoid circular dependency
    from .container import run_container_command
    
    # Create a namespace with command attribute
    class CmdArgs:
        def __init__(self, command, target, lines, follow=False):
            self.command = command
            self.target = target
            self.lines = lines
            self.follow = follow
    
    cmd_args = CmdArgs(
        command=args.subcommand,
        target=args.target,
        lines=args.lines,
        follow=getattr(args, 'follow', False),
    )
    
    run_container_command(cmd_args)


def run_deploy(args) -> None:
    """Deploy project to configured target."""
    config = get_config()
    
    # Get current project
    project_info = config.get_current_project()
    if not project_info:
        print("\nNo current project selected.")
        print("Use 'ops-cli switch <name>' to switch to a project first.")
        return
    
    project_path = Path(project_info["path"])
    
    # Get target
    target_name = args.target
    targets = get_deploy_targets(project_path)
    local_mode = False
    
    if not targets:
        print("\nNo deploy targets configured.")
        response = input("Would you like to create one now? [Y/n]: ").strip().lower()
        if response in ("", "y", "yes"):
            # Interactive create
            import getpass
            
            print("\nConfigure deployment target:")
            print("-" * 40)
            
            target_name = args.target if args.target else input("Target name: ").strip()
            if not target_name:
                print("Target name required.")
                return
            
            host = input(f"Host/IP [192.168.1.100]: ").strip() or "192.168.1.100"
            local_mode = _is_local_deploy_host(host)
            port = 22
            user = ""
            ssh_key = ""
            password = ""

            if local_mode:
                print("\nLocal Docker target detected; SSH settings will be skipped.")
            else:
                port = int(input(f"SSH Port [22]: ").strip() or "22")
                user = input(f"SSH User [root]: ").strip() or "root"
                
                print("\nAuthentication method:")
                print("  1. SSH Key")
                print("  2. Password")
                auth_choice = input("Choice [2]: ").strip() or "2"
                
                if auth_choice == "1":
                    ssh_key = input(f"SSH Key path [~/.ssh/id_rsa]: ").strip() or "~/.ssh/id_rsa"
                else:
                    password = args.password if args.password else getpass.getpass("Password: ").strip()
                    if not password:
                        print("Password required.")
                        return

            remote_default = "/tmp/ops-admin" if local_mode else "/opt/ops-admin"
            remote_path = getattr(args, "remote_path", None) or input(f"Remote path [{remote_default}]: ").strip() or remote_default
            container_port = getattr(args, "container_port", None) or input("Container port [8000]: ").strip() or "8000"

            target = {
                "host": host,
                "port": int(port),
                "remote_path": remote_path,
                "container_port": int(container_port),
            }

            if user:
                target["user"] = user

            existing_db = _existing_database_config_for_new_target(project_path, target_name)
            if existing_db:
                db_config, db_config_source = existing_db
                print(f"\nUsing existing database config from: {db_config_source}")
                target["database_url"] = db_config.get("database_url", "")
            elif local_mode:
                print("\nNo local database config found.")
                print(f"Please create 'config/application.{target_name}.json' with a database section first.")
                print("\nExample format:")
                print('  {"backend": "mysql", "database_url": "mysql://user:pass@host:3306/dbname"}')
                print('  {"backend": "sqlite", "sqlite_path": "data/ops_admin.db"}')
                return
            else:
                print("\nDatabase configuration:")
                db_host = input("  DB Host [127.0.0.1]: ").strip() or "127.0.0.1"
                db_port = input("  DB Port [3306]: ").strip() or "3306"
                db_user = input("  DB Username [root]: ").strip() or "root"
                import getpass
                db_pass = getpass.getpass("  DB Password: ").strip()
                db_name = input("  DB Name: ").strip()

                if not db_name:
                    print("Database name required.")
                    return

                target["database_url"] = f"mysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
            
            if ssh_key:
                target["ssh_key"] = os.path.expanduser(ssh_key)
            if password:
                target["password"] = password
            
            targets[target_name] = target
            save_deploy_targets(targets, project_path)
            
            print(f"\nTarget '{target_name}' created.")
            print("Run 'ops-cli deploy' to start deployment.")
            return
        else:
            print("Cancelled.")
            return
    
    if target_name:
        if target_name not in targets:
            print(f"Target '{target_name}' not found.")
            response = input("Would you like to create it now? [y/N]: ").strip().lower()
            if response in ("y", "yes"):
                targets[target_name] = {"placeholder": True}
                # Continue to creation flow
            else:
                print("Available targets:", ", ".join(targets.keys()))
                return
        target = targets[target_name]
    else:
        # Show selection if multiple targets
        if len(targets) == 1:
            target_name = list(targets.keys())[0]
            target = targets[target_name]
        else:
            print("\nSelect target:")
            print("-" * 40)
            for i, name in enumerate(targets.keys(), 1):
                t = targets[name]
                print(f"  {i}. {name} ({t.get('host')})")
            print("-" * 40)
            
            while True:
                choice = input("Enter number: ").strip()
                try:
                    idx = int(choice) - 1
                    names = list(targets.keys())
                    if 0 <= idx < len(names):
                        target_name = names[idx]
                        target = targets[target_name]
                        break
                    print("Invalid selection.")
                except ValueError:
                    print("Please enter a number.")

    local_mode = _is_local_deploy_host(target.get("host", ""))
    config_env = _resolve_deploy_config_env(target_name, target)

    # Get database config based on config environment (also used for dry-run output)
    db_config, db_config_source = _load_db_config_for_target(project_path, config_env, target)
    if not _has_database_connection_info(db_config):
        print(f"\nNo database config found for target '{target_name}'.")
        print(f"Please create 'config/application.{config_env}.json' with a database section.")
        print("\nExample format:")
        print('  {"backend": "mysql", "database_url": "mysql://user:pass@host:3306/dbname"}')
        print('  {"backend": "sqlite", "sqlite_path": "data/ops_admin.db"}')
        return

    environment_preview = _format_deploy_environment_preview(target_name, target, db_config, db_config_source)

    # Dry-run mode
    if getattr(args, 'dry_run', False):
        print("\n" + "=" * 50)
        print("DRY RUN - Deployment Preview")
        print("=" * 50)
        print()
        print(environment_preview)
        print(f"\nWill do:")
        print("  1. Build frontend (pnpm build)")
        print("  2. Create deployment package (tar.gz)")
        print(f"  3. Upload to {target.get('host')}:{target.get('remote_path')}/")
        print("  4. Extract package on server")
        print("  5. Build Docker image")
        print("  6. Start container")
        print("  7. Health check")
        return

    print(f"\nDeploying to: {target_name}")
    print(f"Host: {target.get('host')}")
    print(f"\nUsing DB config from: {db_config_source}")
    
    # Confirm deployment
    if not args.yes and not ask_confirmation("Continue with deployment?", default=True):
        print("Deployment cancelled.")
        return
    
    # Build frontend (still needed locally)
    if not run_build(project_path):
        print("\nBuild failed. Aborting deployment.")
        return
    
    # Create temp directory for package
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create deploy package (source + dist, no Docker image)
        package_path = temp_path / f"ops-deploy-{datetime.now().strftime('%Y%m%d-%H%M%S')}.tar.gz"
        remote_path = target.get("remote_path", "/opt/ops-admin")
        if not create_deploy_package(
            project_path,
            package_path,
            db_config,
            target_name=target_name,
            remote_path=remote_path,
            container_port=target.get("container_port", 8000),
        ):
            print("\nFailed to create deployment package.")
            return

        if local_mode:
            if _run_local_deploy(package_path, target, db_config, target_name):
                print()
                print(f"Use 'ops-cli deploy logs {target_name}' to view logs.")
                print(f"Use 'ops-cli deploy history {target_name}' to see history.")
            else:
                print("\nDeployment failed.")
            return

        # Deploy to target (builds Docker on server)
        if do_deploy(package_path, target, db_config, target_name):
            print("\n" + "=" * 50)
            print("Deployment Successful!")
            print("=" * 50)
            print(f"Target: {target_name}")
            print(f"Host: {target.get('host')}")
            port = target.get("container_port", 8000)
            print(f"URL: http://{target.get('host')}:{port}")
            print()
            print(f"Use 'ops-cli deploy logs {target_name}' to view logs.")
            print(f"Use 'ops-cli deploy history {target_name}' to see history.")
        else:
            print("\nDeployment failed.")


def run_deploy_add(args) -> None:
    """Add a new deploy target."""
    config = get_config()
    project_info = config.get_current_project()
    
    if not project_info:
        print("\nNo current project selected.")
        print("Use 'ops-cli switch <name>' to switch to a project first.")
        return
    
    project_path = Path(project_info["path"])
    targets = get_deploy_targets(project_path)
    
    name = args.name
    if not name:
        name = input("Target name: ").strip()
    if not name:
        print("Target name required.")
        return
    
    if name in targets:
        print(f"Target '{name}' already exists. Use 'ops-cli deploy --remove {name}' to remove it.")
        return
    
    # Collect target info
    print("\nConfigure deployment target:")
    print("-" * 40)
    
    host = input(f"Host/IP [{args.host or '192.168.1.100'}]: ").strip() or args.host or "192.168.1.100"
    local_mode = _is_local_deploy_host(host)
    port = 22
    user = ""
    ssh_key = ""
    password = ""

    if local_mode:
        print("\nLocal Docker target detected; SSH settings will be skipped.")
    else:
        port = int(input(f"SSH Port [{args.port or '22'}]: ").strip() or args.port or "22")
        user = input(f"SSH User [{args.user or 'root'}]: ").strip() or args.user or "root"

        # Auth method selection
        print("\nAuthentication method:")
        print("  1. SSH Key")
        print("  2. Password")
        auth_choice = input("Choice [2]: ").strip() or "2"

        if auth_choice == "1":
            ssh_key = input(f"SSH Key path [~/.ssh/id_rsa]: ").strip() or "~/.ssh/id_rsa"
        else:
            import getpass
            # Use command line password if provided
            if args.password:
                password = args.password
            else:
                password = getpass.getpass("Password: ").strip()
            if not password:
                print("Password required.")
                return

    remote_default = "/tmp/ops-admin" if local_mode else "/opt/ops-admin"
    remote_path = getattr(args, "remote_path", None) or input(f"Remote path [{remote_default}]: ").strip() or remote_default
    container_port = getattr(args, "container_port", None) or input(f"Container port [8000]: ").strip() or "8000"

    existing_db = _existing_database_config_for_new_target(
        project_path,
        _resolve_deploy_config_env(name, {"database_env": name}),
    )
    if existing_db:
        db_config, db_config_source = existing_db
        print(f"\nUsing existing database config from: {db_config_source}")
        db_url = db_config.get("database_url", "")
    else:
        # Database URL
        print("\nDatabase configuration:")
        print("-" * 40)
        db_url = input("Database URL (运维提供): ").strip()
        if not db_url:
            print("Database URL required.")
            return
    
    target = {
        "host": host,
        "port": int(port),
        "remote_path": remote_path,
        "database_url": db_url,
        "container_port": int(container_port),
    }
    if user:
        target["user"] = user
    
    # Add auth method
    if ssh_key:
        target["ssh_key"] = os.path.expanduser(ssh_key)
    if password:
        target["password"] = password
    
    targets[name] = target
    save_deploy_targets(targets, project_path)
    
    print(f"\nTarget '{name}' added successfully.")
    
    # Save database config for deployment
    config = get_config()
    project_info = config.get_current_project()
    if project_info:
        project_path = Path(project_info["path"])
        config_dir = project_path / "config"
        config_dir.mkdir(exist_ok=True)
        
        db_config = {
            "backend": "mysql" if db_url.startswith("mysql") else "postgres",
            "database_url": db_url,
        }
        target_path = write_application_database_config(project_path, db_config, env=name)
        print(f"Database target config saved to {target_path.name}")
        backup_path = config_dir / "application.json"
        backup_payload = {"database": db_config}
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, indent=2, ensure_ascii=False)
        print("Application config backup saved to application.json")


def run_deploy_copy_env(args) -> None:
    """Copy one deploy environment to another target name."""
    config = get_config()
    project_info = config.get_current_project()

    if not project_info:
        print("\nNo current project selected.")
        print("Use 'ops-cli switch <name>' to switch to a project first.")
        return

    source_name = args.target
    dest_name = getattr(args, "target_to", None)
    if not source_name or not dest_name:
        print("\nUsage: ops-cli deploy copy-env <source> <destination>")
        print("Example: ops-cli deploy copy-env dev prod")
        return

    project_path = Path(project_info["path"])
    overrides = {
        "remote_path": getattr(args, "remote_path", None),
        "container_port": getattr(args, "container_port", None),
    }
    ok, message = copy_deploy_environment(project_path, source_name, dest_name, overrides=overrides)
    if not ok:
        print(f"\nCopy failed: {message}")
        return

    print(f"\n{message}")
    print(f"Next: ops-cli deploy {dest_name}")


def run_deploy_set_env(args) -> None:
    """Update saved deploy environment settings for a target."""
    config = get_config()
    project_info = config.get_current_project()

    if not project_info:
        print("\nNo current project selected.")
        print("Use 'ops-cli switch <name>' to switch to a project first.")
        return

    target_name = args.target
    if not target_name:
        print("\nUsage: ops-cli deploy set-env <target> [--container-port PORT] [--remote-path PATH]")
        print("Example: ops-cli deploy set-env prod --container-port 9002")
        return

    updates = {
        "remote_path": getattr(args, "remote_path", None),
        "container_port": getattr(args, "container_port", None),
        "host": getattr(args, "host", None),
        "port": int(args.port) if getattr(args, "port", None) else None,
        "user": getattr(args, "user", None),
        "ssh_key": os.path.expanduser(args.ssh_key) if getattr(args, "ssh_key", None) else None,
    }
    project_path = Path(project_info["path"])
    ok, message = update_deploy_environment(project_path, target_name, updates)
    if not ok:
        print(f"\nUpdate failed: {message}")
        return

    print(f"\n{message}")
    print(f"Next: ops-cli deploy {target_name}")


def run_deploy_list(args) -> None:
    """List configured deploy targets."""
    project_path = get_project_path()
    targets = get_deploy_targets(project_path)
    
    if not targets:
        print("\nNo deploy targets configured.")
        print("Use 'ops-cli deploy --add' to add a target.")
        return
    
    print("\n" + "=" * 50)
    print("Deploy Targets")
    print("=" * 50)
    
    for name, target in targets.items():
        print(f"\n{name}:")
        print(f"  Host: {target.get('host')}")
        print(f"  Port: {target.get('port')}")
        print(f"  User: {target.get('user')}")
        print(f"  Path: {target.get('remote_path')}")
        masked_url = target.get("database_url", "")
        if "@" in masked_url:
            parts = masked_url.split("@")
            user_part = parts[0].split(":")[0] + ":***"
            masked_url = user_part + "@" + parts[1]
        print(f"  DB:   {masked_url}")
    
    print()


def run_deploy_remove(args) -> None:
    """Remove a deploy target."""
    project_path = get_project_path()
    targets = get_deploy_targets(project_path)
    name = args.name
    
    if not name:
        print("Target name required.")
        return
    
    if name not in targets:
        print(f"Target '{name}' not found.")
        return
    
    if not ask_confirmation(f"Remove target '{name}'?", default=False):
        print("Cancelled.")
        return
    
    del targets[name]
    save_deploy_targets(targets, project_path)
    print(f"Target '{name}' removed.")


def run_deploy_history(args) -> None:
    """Show deployment history for a target."""
    config = get_config()
    config_path = Path(config.get("config_path", "")).parent
    history = DeployHistory(config_path)
    
    target_name = args.target
    project_path = get_project_path()
    targets = get_deploy_targets(project_path)
    
    if not target_name:
        # Show selection if multiple targets
        if len(targets) == 1:
            target_name = list(targets.keys())[0]
        else:
            print("\nSelect target:")
            print("-" * 40)
            for i, name in enumerate(targets.keys(), 1):
                t = targets[name]
                print(f"  {i}. {name} ({t.get('host')})")
            print("-" * 40)
            
            while True:
                choice = input("Enter number: ").strip()
                try:
                    idx = int(choice) - 1
                    names = list(targets.keys())
                    if 0 <= idx < len(names):
                        target_name = names[idx]
                        break
                    print("Invalid selection.")
                except ValueError:
                    print("Please enter a number.")
    
    if target_name not in targets:
        print(f"Target '{target_name}' not found.")
        return
    
    print(f"\nDeployment History: {target_name}")
    print("=" * 50)
    
    history_records = history.get_history(target_name, limit=args.limit or 10)
    print(format_history_list(history_records, limit=args.limit or 10))
    
    # Show rollback option
    if history_records:
        last = history.get_last_successful(target_name)
        if last and len(history_records) > 1:
            print("\nLast successful deployment:")
            print(f"  Version: {last.get('version')}")
            print(f"  Time: {last.get('timestamp')}")
            print("\nUse 'ops-cli deploy rollback {target_name}' to rollback.")


def run_deploy_rollback(args) -> None:
    """Rollback to previous successful deployment."""
    config = get_config()
    config_path = Path(config.get("config_path", "")).parent
    history = DeployHistory(config_path)
    
    target_name = args.target
    project_path = get_project_path()
    targets = get_deploy_targets(project_path)
    
    if not target_name:
        print("Target name required.")
        return
    
    if target_name not in targets:
        print(f"Target '{target_name}' not found.")
        return
    
    target = targets[target_name]
    
    # Get last successful deployment
    last = history.get_last_successful(target_name)
    if not last:
        print("No successful deployment found to rollback to.")
        return
    
    print(f"\nRollback: {target_name}")
    print("=" * 50)
    print(f"Will rollback to: {last.get('version')}")
    print(f"Image: {last.get('image')}")
    
    if not args.yes and not ask_confirmation("Continue with rollback?", default=False):
        print("Cancelled.")
        return
    
    # For now, just show message (full rollback would re-pull image and restart)
    print("\n⚠ Rollback not fully implemented yet.")
    print("This would re-pull the previous image and restart the container.")
    print(f"\nLast successful version: {last.get('version')}")
    print(f"Timestamp: {last.get('timestamp')}")
