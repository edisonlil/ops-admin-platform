from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cron.application.ports import TaskDispatcher


CronCommand = Callable[[dict[str, Any]], dict[str, Any]]


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CronCommand] = {}

    def register(self, name: str, command: CronCommand) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("command name is required")
        self._commands[normalized] = command

    def dispatch(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        command = self._commands.get(name)
        if command is None:
            raise KeyError(f"cron command is not registered: {name}")
        return command(payload)

    def command_names(self) -> list[str]:
        return sorted(self._commands)


class RegistryTaskDispatcher(TaskDispatcher):
    def __init__(self, registry: CommandRegistry) -> None:
        self.registry = registry

    def dispatch(self, execution_target: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.registry.dispatch(execution_target, payload)
