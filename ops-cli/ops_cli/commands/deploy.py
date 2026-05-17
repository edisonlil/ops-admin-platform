"""
Deploy command - deploy project to remote servers via SSH.
Builds on remote server (no local Docker required).
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import tarfile
import tempfile
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import paramiko
from paramiko import SSHClient, AutoAddPolicy

from ..config import get_config
from ..interactive.prompts import ask_confirmation, ask_with_choices


def get_deploy_targets() -> dict:
    """Get all configured deploy targets."""
    config = get_config()
    data = config.load()
    return data.get("deploy_targets", {})


def save_deploy_targets(targets: dict) -> None:
    """Save deploy targets to config."""
    config = get_config()
    data = config.load()
    data["deploy_targets"] = targets
    config.save(data)


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
    db_config: dict
) -> bool:
    """Create deployment package (source + config, no Docker image)."""
    print("\nCreating deployment package...")
    
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
    docker_files = ["Dockerfile", "docker-compose.yml", ".dockerignore"]
    
    try:
        with tarfile.open(output_path, "w:gz") as tar:
            # Add frontend dist
            if dist_path.exists():
                print("  Adding frontend dist...")
                tar.add(dist_path, arcname="dist")
            else:
                print("  Warning: frontend dist not found")
            
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
            
            # Add database config
            print("  Adding database config...")
            config_json = json.dumps(db_config, indent=2, ensure_ascii=False)
            config_data = config_json.encode("utf-8")
            config_file = io.BytesIO(config_data)
            tarinfo = tarfile.TarInfo(name="config/database.json")
            config_file.seek(0, 2)
            tarinfo.size = config_file.tell()
            config_file.seek(0)
            tar.addfile(tarinfo, config_file)
            
            # Add build script with strict validation
            build_script = """#!/bin/bash
set -e

DEPLOY_DIR="/opt/ops-admin"
REQUIRED_DIRS=("api" "packages" "dist")

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
MISSING=()
for d in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$d" ]; then
        MISSING+=("$d")
        echo "  Missing: $d"
    else
        echo "  Found: $d"
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "ERROR: Missing required directories: ${MISSING[*]}"
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

# Stop existing container
echo "Stopping existing container..."
docker-compose down 2>/dev/null || true

# Build image
echo "Building Docker image..."
docker build -t ops-admin:latest .

# Verify image was built successfully
if ! docker image inspect ops-admin:latest > /dev/null 2>&1; then
    echo "ERROR: Docker image build failed"
    exit 1
fi

# Start container
echo "Starting container..."
docker-compose up -d

# Verify container is running
sleep 3
if ! docker ps | grep -q "ops-admin"; then
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
echo "URL: http://localhost:8000"
docker ps | grep ops-admin
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


def do_deploy(package_path: Path, target: dict, db_config: dict) -> bool:
    """Deploy package to target server via SSH and build on server."""
    print("\nDeploying to target server...")
    
    host = target.get("host", "")
    port = target.get("port", 22)
    user = target.get("user", "")
    ssh_key = target.get("ssh_key", "")
    password = target.get("password", "")
    remote_path = target.get("remote_path", "/opt/ops-admin")
    
    if not all([host, user]):
        print("Missing target configuration.")
        return False
    
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
    
    # Build script content
    build_script = """#!/bin/bash
set -e

echo "Starting deployment..."

# Stop existing container
echo "Stopping existing container..."
docker-compose down 2>/dev/null || true

# Build image
echo "Building Docker image..."
docker build -t ops-admin:latest .

# Verify image was built successfully
if ! docker image inspect ops-admin:latest > /dev/null 2>&1; then
    echo "ERROR: Docker image build failed"
    exit 1
fi

# Start container
echo "Starting container..."
docker-compose up -d

# Verify container is running
sleep 3
if ! docker ps | grep -q "ops-admin"; then
    echo "ERROR: Container failed to start"
    docker logs ops-admin-backend 2>&1 | tail -20
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
echo "URL: http://localhost:8000"
docker ps | grep ops-admin
"""
    
    # Write build script to server
    stdin, stdout, stderr = client.exec_command(f"cat > {remote_path}/deploy.sh << 'SCRIPT_EOF'\n{build_script}SCRIPT_EOF")
    stdout.channel.recv_exit_status()
    
    # Run build script
    channel = client.exec_command(f"cd {remote_path} && chmod +x deploy.sh && ./deploy.sh")
    
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
        return True
    else:
        print("\n  Deployment failed.")
        return False


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
    targets = get_deploy_targets()
    
    if not targets:
        print("\nNo deploy targets configured.")
        print("Use 'ops-cli deploy --add' to add a target.")
        return
    
    if target_name:
        if target_name not in targets:
            print(f"Target '{target_name}' not found.")
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
    
    print(f"\nDeploying to: {target_name}")
    print(f"Host: {target.get('host')}")
    
    # Get database config
    db_config_path = project_path / "config" / "database.local.json"
    if db_config_path.exists():
        with open(db_config_path, "r", encoding="utf-8") as f:
            db_config = json.load(f)
    else:
        print("\nNo database config found. Please run 'ops-cli setup' first.")
        return
    
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
        if not create_deploy_package(project_path, package_path, db_config):
            print("\nFailed to create deployment package.")
            return
        
        # Deploy to target (builds Docker on server)
        if do_deploy(package_path, target, db_config):
            print("\n" + "=" * 50)
            print("Deployment Successful!")
            print("=" * 50)
            print(f"Target: {target_name}")
            print(f"Host: {target.get('host')}")
            print(f"URL: http://{target.get('host')}:8000")
        else:
            print("\nDeployment failed.")


def run_deploy_add(args) -> None:
    """Add a new deploy target."""
    targets = get_deploy_targets()
    
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
    port = input(f"SSH Port [{args.port or '22'}]: ").strip() or args.port or "22"
    user = input(f"SSH User [{args.user or 'root'}]: ").strip() or args.user or "root"
    
    # Auth method selection
    print("\nAuthentication method:")
    print("  1. SSH Key")
    print("  2. Password")
    auth_choice = input("Choice [2]: ").strip() or "2"
    
    ssh_key = ""
    password = ""
    
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
    
    remote_path = input(f"Remote path [/opt/ops-admin]: ").strip() or "/opt/ops-admin"
    
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
        "user": user,
        "remote_path": remote_path,
        "database_url": db_url,
    }
    
    # Add auth method
    if ssh_key:
        target["ssh_key"] = os.path.expanduser(ssh_key)
    if password:
        target["password"] = password
    
    targets[name] = target
    save_deploy_targets(targets)
    
    print(f"\nTarget '{name}' added successfully.")
    
    # Save database.json for deployment
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
        with open(config_dir / "database.json", "w", encoding="utf-8") as f:
            json.dump(db_config, f, indent=2)
        print(f"Database config saved.")


def run_deploy_list(args) -> None:
    """List configured deploy targets."""
    targets = get_deploy_targets()
    
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
    targets = get_deploy_targets()
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
    save_deploy_targets(targets)
    print(f"Target '{name}' removed.")