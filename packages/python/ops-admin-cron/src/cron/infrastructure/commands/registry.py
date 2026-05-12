from __future__ import annotations

from cron.application.commands import CommandRegistry, RegistryTaskDispatcher
from cron.application.ports import TaskDispatcher
from cron.infrastructure.commands.system_health import system_health_snapshot


def build_default_command_registry() -> CommandRegistry:
    registry = CommandRegistry()
    registry.register("system.health.snapshot", system_health_snapshot)
    return registry


def build_default_dispatcher() -> TaskDispatcher:
    return RegistryTaskDispatcher(build_default_command_registry())
