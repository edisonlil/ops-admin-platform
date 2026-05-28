"""
Container command - manage deployed containers on remote servers.
"""
from __future__ import annotations

import re
import select
import sys
from pathlib import Path

import paramiko
from paramiko import SSHClient, AutoAddPolicy

from ..config import get_config


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


def _get_target_container_name(target_name: str, target: dict) -> str:
    return _make_container_name(target_name, fallback=target.get("name", target.get("host", target.get("user", "default"))))


def _remote_shell_prefix() -> str:
    return (
        "if [ \"$(id -u)\" -eq 0 ]; then SUDO=\"\"; else SUDO=\"sudo\"; fi; "
        "if command -v docker-compose >/dev/null 2>&1; then COMPOSE=\"$SUDO docker-compose\"; "
        "else COMPOSE=\"$SUDO docker compose\"; fi; "
        "DOCKER=\"$SUDO docker\"; "
    )


def _docker_command(command: str) -> str:
    return f"{_remote_shell_prefix()}$DOCKER {command}"


def _compose_command(remote_path: str, action: str) -> str:
    return f"{_remote_shell_prefix()}$COMPOSE -f {remote_path}/docker-compose.yml {action}"


def get_deploy_targets() -> dict:
    """Get deploy targets for the active project."""
    config = get_config()
    project_info = config.get_current_project()
    if project_info:
        from .deploy import get_deploy_targets as get_project_deploy_targets

        return get_project_deploy_targets(Path(project_info.get("path", "")))

    data = config.load()
    return data.get("deploy_targets", {})


def ssh_connect(target: dict) -> SSHClient | None:
    """Create SSH connection to target."""
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    
    connect_kwargs = {
        "hostname": target.get("host", ""),
        "port": int(target.get("port", 22)),
        "username": target.get("user", "root"),
        "look_for_keys": False,
        "allow_agent": False,
        "timeout": 30,
    }
    
    password = target.get("password", "")
    ssh_key = target.get("ssh_key", "")
    
    if password:
        connect_kwargs["password"] = password
    elif ssh_key:
        connect_kwargs["key_filename"] = str(Path(ssh_key).expanduser())
    
    try:
        client.connect(**connect_kwargs)
        return client
    except Exception as e:
        print(f"SSH connection failed: {e}")
        return None


def run_container_command(args) -> None:
    """Manage container on remote server."""
    targets = get_deploy_targets()
    
    if not targets:
        print("No deploy targets configured.")
        print("Use 'ops-cli deploy --add' to add a target first.")
        return
    
    # Get target
    target_name = args.target
    if not target_name:
        # Show selection
        print("\nSelect target:")
        print("-" * 40)
        for i, name in enumerate(targets.keys(), 1):
            t = targets[name]
            print(f"  {i}. {name} ({t.get('host')})")
        print("-" * 40)
        
        while True:
            try:
                choice = input("Enter number: ").strip()
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
        print("Available:", ", ".join(targets.keys()))
        return
    
    target = targets[target_name]
    print(f"\nTarget: {target_name} ({target.get('host')})")
    print("=" * 50)
    
    # Connect to server
    client = ssh_connect(target)
    if not client:
        return
    
    command = args.command
    
    if command == "status":
        # Show container status
        print("\nContainer Status:")
        print("-" * 40)
        container_name = _get_target_container_name(target_name, target)
        stdin, stdout, stderr = client.exec_command(
            _docker_command(f"ps -a --filter name=^{container_name}$ --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'")
        )
        stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        if output.strip():
            print(output)
        else:
            print("No ops-admin container found.")
        
        # Show image
        print("\nImage:")
        print("-" * 40)
        stdin, stdout, stderr = client.exec_command(
            _docker_command("images ops-admin:latest --format '{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}'")
        )
        stdout.channel.recv_exit_status()
        print(stdout.read().decode() or "No image found.")
    
    elif command in ("start", "stop", "restart"):
        # Start/stop/restart container
        action = command
        action_label = {"start": "Starting", "stop": "Stopping", "restart": "Restarting"}[action]
        print(f"\n{action_label} container...")
        remote_path = target.get("remote_path", "/opt/ops-admin")

        stdin, stdout, stderr = client.exec_command(_compose_command(remote_path, action))
        
        # Show output
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
        if exit_status == 0:
            print(f"\nContainer {action} completed successfully.")
        else:
            print(f"\nFailed to {action} container.")
    
    elif command == "logs":
        container_name = _get_target_container_name(target_name, target)
        # Show container logs
        lines = args.lines or 100
        follow = getattr(args, 'follow', False)
        
        if follow:
            print(f"\nFollowing container logs (Ctrl+C to stop):")
            print("-" * 40)
            
            # Use docker logs -f for real-time
            channel = client.exec_command(_docker_command(f"logs -f --tail {lines} {container_name}") + " 2>&1")
            
            stdout = channel[1]
            stderr = channel[2]
            
            try:
                while True:
                    readable, _, _ = select.select([stdout.channel, stderr.channel, sys.stdin], [], [])
                    if stdout.channel in readable and stdout.channel.recv_ready():
                        data = stdout.read(4096).decode()
                        if data:
                            print(data, end="")
                    if stderr.channel in readable and stderr.channel.recv_ready():
                        data = stderr.read(4096).decode()
                        if data:
                            print(data, end="")
                    if stdout.channel.exit_status_ready():
                        break
            except KeyboardInterrupt:
                print("\n\nStopped following logs.")
                client.exec_command("")  # Send empty command to interrupt
        else:
            print(f"\nContainer logs (last {lines} lines):")
            print("-" * 40)
            
            stdin, stdout, stderr = client.exec_command(_docker_command(f"logs --tail {lines} {container_name}") + " 2>&1")
            
            while True:
                readable, _, _ = select.select([stdout.channel, stderr.channel], [], [])
                if stdout.channel in readable and stdout.channel.recv_ready():
                    data = stdout.read(4096).decode()
                    if data:
                        print(data, end="")
                if stderr.channel in readable and stderr.channel.recv_ready():
                    data = stderr.read(4096).decode()
                    if data:
                        print(data, end="")
                if stdout.channel.exit_status_ready():
                    break
            
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print(f"\n✓ Logs retrieved successfully.")
                print("\nUse 'ops-cli deploy logs -f {target}' to follow logs in real-time.")
    
    elif command == "health":
        # Check health endpoint
        print("\nChecking health endpoint...")
        port = target.get("container_port", 8000)
        host = target.get("host")
        
        stdin, stdout, stderr = client.exec_command(f"curl -s http://localhost:{port}/api/health")
        stdout.channel.recv_exit_status()
        print(stdout.read().decode() or stderr.read().decode()[:200])
    
    elif command == "shell":
        # Open shell in container
        print("\nOpening shell in container...")
        channel = client.invoke_shell()
        
        while True:
            readable, _, _ = select.select([channel, sys.stdin], [], [])
            if channel in readable:
                try:
                    data = channel.recv(1024).decode()
                    if data:
                        print(data, end="")
                    else:
                        break
                except Exception:
                    break
            if sys.stdin in readable:
                try:
                    cmd = sys.stdin.readline()
                    if cmd:
                        channel.send(cmd)
                    else:
                        break
                except Exception:
                    break
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: status, start, stop, restart, logs, health, shell")
    
    client.close()
