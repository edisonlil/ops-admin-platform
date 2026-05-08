from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import EntryPoint, entry_points
from typing import Any

from fastapi import APIRouter


ROUTER_GROUP = "ops_admin.routers"
INIT_TASK_GROUP = "ops_admin.init_tasks"
MODULE_ORDER = ("system", "identity_access", "llm_runtime", "appearance")
LOCAL_ENTRYPOINTS = {
    ROUTER_GROUP: {
        "system": "system.entrypoints:router",
        "identity_access": "identity_access.entrypoints:router",
        "llm_runtime": "llm_runtime.entrypoints:router",
        "appearance": "appearance.entrypoints:router",
    },
    INIT_TASK_GROUP: {
        "system": "system.entrypoints:init_tasks",
        "identity_access": "identity_access.entrypoints:init_tasks",
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
    discovered = list(entry_points(group=group))
    if not discovered:
        discovered = [
            EntryPoint(name=name, value=value, group=group)
            for name, value in LOCAL_ENTRYPOINTS.get(group, {}).items()
        ]
    return sorted(discovered, key=lambda item: module_sort_key(item.name))


def module_sort_key(name: str) -> tuple[int, str]:
    try:
        return (MODULE_ORDER.index(name), name)
    except ValueError:
        return (len(MODULE_ORDER), name)
