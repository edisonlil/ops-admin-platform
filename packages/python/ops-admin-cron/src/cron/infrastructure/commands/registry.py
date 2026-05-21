from __future__ import annotations

from api.module_registry import CRON_COMMAND_GROUP, ordered_entry_points
from cron.application.commands import CommandRegistry, RegistryTaskDispatcher
from cron.application.ports import TaskDispatcher
from cron.infrastructure.commands.system_health import system_health_snapshot


def build_default_command_registry() -> CommandRegistry:
    registry = CommandRegistry()
    registry.register("system.health.snapshot", system_health_snapshot)
    for entrypoint in ordered_entry_points(CRON_COMMAND_GROUP):
        command_map = entrypoint.load()()
        if not isinstance(command_map, dict):
            continue
        for name, command in command_map.items():
            registry.register(str(name), command)
    return registry


def build_default_dispatcher() -> TaskDispatcher:
    return RegistryTaskDispatcher(build_default_command_registry())
