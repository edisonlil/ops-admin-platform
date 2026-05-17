"""
Main CLI entry point for ops-cli.
"""
from __future__ import annotations

import argparse
import sys

from .commands.init import run_init
from .commands.link import run_link
from .commands.list_cmd import run_list
from .commands.switch import run_switch
from .commands.remove import run_remove
from .commands.status import run_status
from .commands.run import run_run
from .commands.set_config import run_set
from .commands.setup import run_setup
from .commands.rerun_module import run_rerun_module
from .commands.deploy import run_deploy, run_deploy_add, run_deploy_list, run_deploy_remove, run_container_cmd, run_deploy_history, run_deploy_rollback
from .commands.sync import run_sync
from .config import get_config


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ops-cli",
        description="OPS Admin Platform Project Manager - Create and manage projects from scaffold",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ops-cli init              Create a new project (interactive)
  ops-cli list              List all projects
  ops-cli switch my-project Switch to a project
  ops-cli status            Show current project status
  ops-cli remove my-project Remove a project
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    init_parser = subparsers.add_parser(
        "init",
        help="Create a new project from scaffold",
    )
    init_parser.add_argument(
        "--name",
        "-n",
        help="Project name (will prompt if not provided)",
    )

    # link command
    link_parser = subparsers.add_parser(
        "link",
        help="Link an existing project to ops-cli management",
    )
    link_parser.add_argument(
        "path",
        nargs="?",
        help="Project path (uses current directory if not provided)",
    )
    link_parser.add_argument(
        "--name",
        "-n",
        help="Project name (uses folder name if not provided)",
    )

    # list command
    list_parser = subparsers.add_parser(
        "list",
        help="List all managed projects",
        aliases=["ls"],
    )

    # switch command
    switch_parser = subparsers.add_parser(
        "switch",
        help="Switch to a different project",
        aliases=["sw"],
    )
    switch_parser.add_argument(
        "name",
        nargs="?",
        help="Project name (will prompt if not provided)",
    )

    # remove command
    remove_parser = subparsers.add_parser(
        "remove",
        help="Remove a project from management",
        aliases=["rm"],
    )
    remove_parser.add_argument(
        "name",
        nargs="?",
        help="Project name (will prompt if not provided)",
    )

    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show current project status",
        aliases=["st"],
    )

    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Start the current project",
        aliases=["start"],
    )
    run_parser.add_argument(
        "--backend-port", "-bp",
        type=int,
        default=8000,
        help="Backend server port (default: 8000)",
    )
    run_parser.add_argument(
        "--frontend-port", "-fp",
        type=int,
        default=8001,
        help="Frontend server port (default: 8001)",
    )
    run_parser.add_argument(
        "--only-backend",
        action="store_true",
        help="Start only the backend server",
    )
    run_parser.add_argument(
        "--only-frontend",
        action="store_true",
        help="Start only the frontend server",
    )

    # config command
    config_parser = subparsers.add_parser(
        "config",
        help="Show configuration",
        aliases=["cfg"],
    )

    # set command
    set_parser = subparsers.add_parser(
        "set",
        help="Set configuration values",
    )
    set_parser.add_argument("key", help="Config key (projects_dir, scaffold_url)")
    set_parser.add_argument("value", help="Config value")

    # setup command
    setup_parser = subparsers.add_parser(
        "setup",
        help="Configure project database and run init scripts",
    )
    setup_parser.add_argument(
        "name",
        nargs="?",
        help="Project name (auto-detected from current directory if not provided)",
    )
    setup_parser.add_argument(
        "--db",
        dest="database",
        help="Database type: sqlite/mysql/postgres",
    )
    setup_parser.add_argument(
        "--url",
        dest="database_url",
        help="Database URL (for mysql/postgres)",
    )
    setup_parser.add_argument(
        "--sqlite-path",
        dest="sqlite_path",
        help="SQLite database path",
    )

    # rerun-module command
    rerun_parser = subparsers.add_parser(
        "rerun-module",
        help="Rerun init script for one module",
    )
    rerun_parser.add_argument("module", help="Module name, e.g. organization")
    rerun_parser.add_argument(
        "--env",
        help="Environment name, e.g. dev/test/prod (uses config/database.<env>.json)",
    )
    rerun_parser.add_argument(
        "--name",
        "-n",
        help="Project name (auto-detected from current directory if not provided)",
    )

    # deploy command
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy project to remote server",
    )
    deploy_parser.add_argument(
        "--target",
        "-t",
        help="Target server name",
    )
    deploy_parser.add_argument(
        "--add",
        action="store_true",
        help="Add a new deploy target",
    )
    deploy_parser.add_argument(
        "--remove",
        dest="remove_target",
        help="Remove a deploy target",
    )
    deploy_parser.add_argument(
        "--list-targets",
        action="store_true",
        help="List all deploy targets",
    )
    deploy_parser.add_argument(
        "subcommand",
        nargs="?",
        choices=["status", "start", "stop", "restart", "logs", "health", "shell"],
        help="Container management command",
    )
    deploy_parser.add_argument(
        "target",
        nargs="?",
        help="Target server name",
    )
    deploy_parser.add_argument(
        "--lines", "-n",
        type=int,
        default=100,
        help="Number of log lines to show [100]",
    )
    deploy_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of history records to show [10]",
    )
    deploy_parser.add_argument(
        "--follow", "-f",
        action="store_true",
        help="Follow log output in real-time",
    )
    deploy_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deployment without executing",
    )
    deploy_parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback to previous deployment",
    )
    deploy_parser.add_argument(
        "--history",
        action="store_true",
        help="Show deployment history",
    )
    # For --add
    deploy_parser.add_argument("--name", help="Target name")
    deploy_parser.add_argument("--host", help="Host/IP")
    deploy_parser.add_argument("--port", help="SSH port")
    deploy_parser.add_argument("--user", help="SSH user")
    deploy_parser.add_argument("--ssh-key", dest="ssh_key", help="SSH key path")
    deploy_parser.add_argument("--password", dest="password", help="SSH password")
    deploy_parser.add_argument("--yes", "-y", dest="yes", action="store_true", help="Skip confirmation")

    # sync command
    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync project with scaffold updates",
    )
    sync_parser.add_argument(
        "--check",
        action="store_true",
        help="Check for updates without applying",
    )
    sync_parser.add_argument(
        "--yes", "-y",
        dest="yes",
        action="store_true",
        help="Skip confirmation",
    )

    return parser


def show_config(args) -> None:
    """Show current configuration."""
    config = get_config()
    data = config.load()

    print("\n" + "=" * 50)
    print("OPS-CLI Configuration")
    print("=" * 50)
    print(f"Scaffold URL:  {data.get('scaffold_url', 'N/A')}")
    print(f"Projects Dir:  {data.get('projects_dir', 'N/A')}")
    print(f"Current:       {data.get('current_project', 'None')}")
    print(f"Total Projects: {len(data.get('projects', {}))}")
    print()


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "init":
            run_init(args)
        elif args.command == "link":
            run_link(args)
        elif args.command in ("list", "ls"):
            run_list(args)
        elif args.command in ("switch", "sw"):
            run_switch(args)
        elif args.command in ("remove", "rm"):
            run_remove(args)
        elif args.command in ("status", "st"):
            run_status(args)
        elif args.command in ("run", "start"):
            run_run(args)
        elif args.command in ("config", "cfg"):
            show_config(args)
        elif args.command == "setup":
            run_setup(args)
        elif args.command == "deploy":
            if args.subcommand:
                # Container management command (logs, status, etc.)
                run_container_cmd(args)
            elif args.rollback:
                run_deploy_rollback(args)
            elif args.history:
                run_deploy_history(args)
            elif args.add:
                run_deploy_add(args)
            elif args.list_targets:
                run_deploy_list(args)
            elif args.remove_target:
                run_deploy_remove(args)
            else:
                run_deploy(args)
        elif args.command in ("container", "ctrl", "ct"):
            run_container_cmd(args)
        elif args.command == "sync":
            run_sync(args)
        elif args.command == "rerun-module":
            run_rerun_module(args)
        else:
            parser.print_help()
            return 1

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
