"""
Sync command - sync scaffold updates to project.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import get_config
from ..utils import run_command


def get_scaffold_info(project_path: Path) -> dict | None:
    """Get scaffold info from project config."""
    ops_config = project_path / ".ops-config"
    if not ops_config.exists():
        return None
    
    try:
        with open(ops_config, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Try to get scaffold info from branch or commit
        scaffold_info = {
            "name": config.get("name", ""),
            "branch": config.get("branch", "main"),
            "commit": config.get("commit", ""),  # Initial commit hash
            "scaffold_url": config.get("scaffold_url", ""),
        }
        
        return scaffold_info
    except Exception:
        return None


def save_scaffold_commit(project_path: Path, commit: str) -> None:
    """Save scaffold commit hash to project config."""
    ops_config = project_path / ".ops-config"
    
    if not ops_config.exists():
        return
    
    try:
        with open(ops_config, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        config["last_synced_commit"] = commit
        config["last_synced_at"] = datetime.now().isoformat()
        
        with open(ops_config, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_config_value(key: str, default: str = "") -> str:
    """Get value from ops-cli config."""
    config = get_config()
    data = config.load()
    return data.get(key, default)


def clone_scaffold(scaffold_url: str, branch: str, target_path: Path) -> bool:
    """Clone scaffold repository."""
    try:
        run_command(
            ["git", "clone", "-b", branch, "--depth", "1", scaffold_url, str(target_path)],
            check=True,
            timeout=300,
        )
        return True
    except Exception as e:
        print(f"Failed to clone scaffold: {e}")
        return False


def get_current_commit(repo_path: Path) -> str:
    """Get current commit hash."""
    try:
        result = run_command(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_file_diff(repo_path: Path, from_commit: str, to_commit: str = "HEAD") -> list[dict]:
    """Get list of changed files between commits."""
    try:
        if from_commit:
            result = run_command(
                ["git", "diff", "--name-status", from_commit, to_commit],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
        else:
            # From beginning
            result = run_command(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
            # Return all untracked files
            files = []
            for f in result.stdout.strip().split("\n"):
                if f:
                    files.append({"status": "A", "file": f})
            return files
        
        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                status = parts[0]
                file_path = parts[1]
                files.append({"status": status, "file": file_path})
        
        return files
    except Exception as e:
        print(f"Failed to get diff: {e}")
        return []


def apply_patch(source_repo: Path, target_path: Path, from_commit: str) -> tuple[int, int, list[str]]:
    """
    Apply patch from source to target.
    Returns: (success_count, fail_count, conflict_files)
    """
    success = 0
    failed = 0
    conflicts = []
    
    # Get changed files
    if from_commit:
        diff_files = get_file_diff(source_repo, from_commit)
    else:
        diff_files = get_file_diff(source_repo, "")
    
    # Files to skip (project-specific, should not be overwritten)
    skip_patterns = [
        ".ops-config",
        ".ops-scaffold",  # Scaffold reference, don't overwrite
        "AGENTS.md",  # Project-level AGENTS, don't overwrite
        "business/",  # Business code isolation
        "config/application.local.json",
        "config/application.dev.json",
        "config/application.test.json",
        "config/database.local.json",
        "config/database.dev.json",
        "config/database.test.json",
        "node_modules",
        ".venv",
        "__pycache__",
        "dist",
        ".git",
    ]
    
    for item in diff_files:
        status = item.get("status", "")
        file_path = item.get("file", "")
        
        # Skip certain files
        skip = False
        for pattern in skip_patterns:
            if pattern in file_path or file_path.startswith(pattern):
                skip = True
                break
        
        if skip:
            continue
        
        source_file = source_repo / file_path
        target_file = target_path / file_path
        
        if status in ("D", "deleted"):
            # File was deleted in scaffold, skip (don't delete user files)
            continue
        
        if not source_file.exists():
            continue
        
        # Check if target file exists and is different
        if target_file.exists():
            try:
                with open(target_file, "rb") as f:
                    target_content = f.read()
                with open(source_file, "rb") as f:
                    source_content = f.read()
                
                if target_content == source_content:
                    continue  # No change needed
                
                # Check if file was modified by user
                # Simple heuristic: if file exists and is different, might be user modification
                # For now, we'll ask or skip
            except Exception:
                pass
        
        # Create parent directories
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy file
            import shutil
            shutil.copy2(source_file, target_file)
            success += 1
            print(f"  + {file_path}")
        except Exception as e:
            failed += 1
            print(f"  X {file_path}: {e}")
    
    return success, failed, conflicts


def check_for_breaking_changes(source_repo: Path, from_commit: str) -> list[str]:
    """Check for potentially breaking changes."""
    breaking = []
    
    # Check for deleted files that might be important
    diff_files = get_file_diff(source_repo, from_commit)
    
    critical_files = [
        "requirements.txt",
        "package.json",
        "Dockerfile",
        "docker-compose.yml",
        "api/main.py",
    ]
    
    for item in diff_files:
        if item.get("status") == "D":
            file_path = item.get("file", "")
            for critical in critical_files:
                if file_path.endswith(critical) or file_path == critical:
                    breaking.append(f"Deleted: {file_path}")
    
    return breaking


def run_sync(args) -> None:
    """Sync project with scaffold updates."""
    config = get_config()
    
    # Get current project
    project_info = config.get_current_project()
    if not project_info:
        print("\nNo current project selected.")
        print("Use 'ops-cli switch <name>' to switch to a project first.")
        return
    
    project_path = Path(project_info["path"])
    
    # Get scaffold info
    scaffold_info = get_scaffold_info(project_path)
    if not scaffold_info:
        print("\nProject was not created from scaffold (no .ops-config found).")
        print("Cannot sync without scaffold information.")
        return
    
    # Get scaffold URL
    scaffold_url = scaffold_info.get("scaffold_url") or get_config_value("scaffold_url")
    if not scaffold_url:
        print("\nScaffold URL not found.")
        print("Please run 'ops-cli config set scaffold_url <url>' first.")
        return
    
    branch = scaffold_info.get("branch", "main")
    last_commit = scaffold_info.get("last_synced_commit", "")
    
    print("\n" + "=" * 50)
    print("Scaffold Sync")
    print("=" * 50)
    print(f"\nProject: {project_path.name}")
    print(f"Scaffold: {scaffold_url}")
    print(f"Branch: {branch}")
    print(f"Last synced: {last_commit[:8] if last_commit else 'Never'}")
    
    # Check mode
    if args.check:
        print("\n" + "-" * 40)
        print("Checking for updates...")
        
        # Clone scaffold to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "scaffold"
            
            print(f"\nCloning scaffold...")
            if not clone_scaffold(scaffold_url, branch, temp_path):
                print("Failed to clone scaffold.")
                return
            
            current_commit = get_current_commit(temp_path)
            print(f"Current scaffold commit: {current_commit[:8]}")
            
            if not last_commit:
                # First time sync - just record current commit, no changes to apply
                print("\n[OK] No updates available.")
                print("     Project was just synced to scaffold.")
                return
            
            diff_files = get_file_diff(temp_path, last_commit)
            
            if not diff_files:
                print("\n[OK] No updates available.")
                return
            
            print(f"\nUpdates available: {len(diff_files)} files changed")
            print("-" * 40)
            
            # Show breaking changes
            if breaking:
                print("\n[WARN] Potential breaking changes:")
                for b in breaking:
                    print(f"  - {b}")
            
            print("\nChanged files:")
            for item in diff_files[:20]:
                status = item.get("status", "?")
                file_path = item.get("file", "")
                status_symbol = {"M": "~", "A": "+", "D": "-", "R": "?"}.get(status, "?")
                print(f"  {status_symbol} {file_path}")
            
            if len(diff_files) > 20:
                print(f"  ... and {len(diff_files) - 20} more files")
        
        return
    
    # Confirm sync
    if not args.yes:
        response = input("\nSync changes from scaffold? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print("Cancelled.")
            return
    
    # Perform sync
    print("\nSyncing...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "scaffold"
        
        # Clone scaffold
        print(f"\nCloning scaffold...")
        if not clone_scaffold(scaffold_url, branch, temp_path):
            print("Failed to clone scaffold.")
            return
        
        current_commit = get_current_commit(temp_path)
        
        # Apply patch
        print("\nApplying changes...")
        success, failed, conflicts = apply_patch(temp_path, project_path, last_commit)
        
        # Save new commit
        save_scaffold_commit(project_path, current_commit)
        
        print("\n" + "=" * 50)
        print("Sync Complete")
        print("=" * 50)
        print(f"\n[OK] Updated: {success} files")
        if failed:
            print(f"[FAIL] Failed: {failed} files")
        print(f"\nSynced to: {current_commit[:8]}")
        print(f"\nRun 'ops-cli sync --check' to see future updates.")
