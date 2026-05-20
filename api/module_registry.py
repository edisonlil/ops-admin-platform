from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
import sys
from typing import Any

from fastapi import APIRouter


ROUTER_GROUP = "ops_admin.routers"
INIT_TASK_GROUP = "ops_admin.init_tasks"
MODULE_ORDER = (
    "system",
    "cron",
    "identity_access",
    "organization",
    "authorization",
    "basic_data",
    "metadata_support",
    "personalization",
    "file_management",
    "audit_logging",
    "messaging",
    "llm_runtime",
    "ai_assets",
    "ai_applications",
    "ai_capabilities",
    "appearance",
)
REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGE_SRC = {
    "system": REPO_ROOT / "packages" / "python" / "ops-admin-system" / "src",
    "cron": REPO_ROOT / "packages" / "python" / "ops-admin-cron" / "src",
    "identity_access": REPO_ROOT / "packages" / "python" / "ops-admin-identity-access" / "src",
    "organization": REPO_ROOT / "packages" / "python" / "ops-admin-organization" / "src",
    "authorization": REPO_ROOT / "packages" / "python" / "ops-admin-authorization" / "src",
    "basic_data": REPO_ROOT / "packages" / "python" / "ops-admin-basic-data" / "src",
    "metadata_support": REPO_ROOT / "packages" / "python" / "ops-admin-metadata-support" / "src",
    "personalization": REPO_ROOT / "packages" / "python" / "ops-admin-personalization" / "src",
    "file_management": REPO_ROOT / "packages" / "python" / "ops-admin-file-management" / "src",
    "audit_logging": REPO_ROOT / "packages" / "python" / "ops-admin-audit-logging" / "src",
    "messaging": REPO_ROOT / "packages" / "python" / "ops-admin-messaging" / "src",
    "llm_runtime": REPO_ROOT / "packages" / "python" / "ops-admin-llm-runtime" / "src",
    "ai_assets": REPO_ROOT / "packages" / "python" / "ops-admin-ai-assets" / "src",
    "ai_service_api": REPO_ROOT / "packages" / "python" / "framework" / "ops-admin-ai-service-api" / "src",
    "ai_applications": REPO_ROOT / "packages" / "python" / "ops-admin-ai-applications" / "src",
    "ai_capabilities": REPO_ROOT / "packages" / "python" / "ops-admin-ai-capabilities" / "src",
    "ai_runtime_core": REPO_ROOT / "packages" / "python" / "framework" / "ops-admin-ai-runtime-core" / "src",
    "appearance": REPO_ROOT / "packages" / "python" / "ops-admin-appearance" / "src",
}
LOCAL_ENTRYPOINTS = {
    ROUTER_GROUP: {
        "system": "system.entrypoints:router",
        "cron": "cron.entrypoints:router",
        "identity_access": "identity_access.entrypoints:router",
        "organization": "organization.entrypoints:router",
        "authorization": "authorization.entrypoints:router",
        "basic_data": "basic_data.entrypoints:router",
        "metadata_support": "metadata_support.entrypoints:router",
        "personalization": "personalization.entrypoints:router",
        "file_management": "file_management.entrypoints:router",
        "audit_logging": "audit_logging.entrypoints:router",
        "messaging": "messaging.entrypoints:router",
        "llm_runtime": "llm_runtime.entrypoints:router",
        "ai_assets": "ai_assets.entrypoints:router",
        "ai_applications": "ai_applications.entrypoints:router",
        "ai_capabilities": "ai_capabilities.entrypoints:router",
        "appearance": "appearance.entrypoints:router",
    },
    INIT_TASK_GROUP: {
        "system": "system.entrypoints:init_tasks",
        "cron": "cron.entrypoints:init_tasks",
        "identity_access": "identity_access.entrypoints:init_tasks",
        "organization": "organization.entrypoints:init_tasks",
        "authorization": "authorization.entrypoints:init_tasks",
        "basic_data": "basic_data.entrypoints:init_tasks",
        "metadata_support": "metadata_support.entrypoints:init_tasks",
        "personalization": "personalization.entrypoints:init_tasks",
        "file_management": "file_management.entrypoints:init_tasks",
        "audit_logging": "audit_logging.entrypoints:init_tasks",
        "messaging": "messaging.entrypoints:init_tasks",
        "llm_runtime": "llm_runtime.entrypoints:init_tasks",
        "ai_assets": "ai_assets.entrypoints:init_tasks",
        "ai_applications": "ai_applications.entrypoints:init_tasks",
        "ai_capabilities": "ai_capabilities.entrypoints:init_tasks",
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


ensure_local_package_sources()
