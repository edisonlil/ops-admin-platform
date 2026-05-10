from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
import sys
from typing import Any

from fastapi import APIRouter


ROUTER_GROUP = "ops_admin.routers"
INIT_TASK_GROUP = "ops_admin.init_tasks"
MODULE_ORDER = ("system", "identity_access", "messaging", "llm_runtime", "appearance")
REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGE_SRC = {
    "system": REPO_ROOT / "packages" / "python" / "ops-admin-system" / "src",
    "identity_access": REPO_ROOT / "packages" / "python" / "ops-admin-identity-access" / "src",
    "messaging": REPO_ROOT / "packages" / "python" / "ops-admin-messaging" / "src",
    "llm_runtime": REPO_ROOT / "packages" / "python" / "ops-admin-llm-runtime" / "src",
    "appearance": REPO_ROOT / "packages" / "python" / "ops-admin-appearance" / "src",
}
LOCAL_ENTRYPOINTS = {
    ROUTER_GROUP: {
        "system": "system.entrypoints:router",
        "identity_access": "identity_access.entrypoints:router",
        "messaging": "messaging.entrypoints:router",
        "llm_runtime": "llm_runtime.entrypoints:router",
        "appearance": "appearance.entrypoints:router",
    },
    INIT_TASK_GROUP: {
        "system": "system.entrypoints:init_tasks",
        "identity_access": "identity_access.entrypoints:init_tasks",
        "messaging": "messaging.entrypoints:init_tasks",
        "llm_runtime": "llm_runtime.entrypoints:init_tasks",
        "appearance": "appearance.entrypoints:init_tasks",
    },
}


def module_routers() -> list[APIRouter]:
    routers: list[APIRouter] = []
    for entrypoint in ordered_entry_points(ROUTER_GROUP):
        router = entrypoint.load()
        if not isinstance(router, APIRouter):
            raise TypeError(f"{entrypoint.value} must resolve to a FastAPI APIRouter")
        routers.append(router)
    return routers


def module_init_tasks() -> dict[str, Callable[[Any], None]]:
    tasks: dict[str, Callable[[Any], None]] = {}
    for entrypoint in ordered_entry_points(INIT_TASK_GROUP):
        task_map = entrypoint.load()()
        tasks.update(task_map)
    return tasks


def ordered_entry_points(group: str) -> list[EntryPoint]:
    ensure_local_package_sources()
    discovered = list(entry_points(group=group))
    discovered_names = {entrypoint.name for entrypoint in discovered}
    discovered.extend(
        [
            EntryPoint(name=name, value=value, group=group)
            for name, value in LOCAL_ENTRYPOINTS.get(group, {}).items()
            if name not in discovered_names
        ]
    )
    return sorted(discovered, key=lambda item: module_sort_key(item.name))


def module_sort_key(name: str) -> tuple[int, str]:
    try:
        return (MODULE_ORDER.index(name), name)
    except ValueError:
        return (len(MODULE_ORDER), name)


def ensure_local_package_sources() -> None:
    for src_path in LOCAL_PACKAGE_SRC.values():
        if src_path.exists():
            src = str(src_path)
            if src not in sys.path:
                sys.path.insert(0, src)
