from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class AIServiceError(RuntimeError):
    pass


class AIServiceUnavailable(AIServiceError):
    pass


@dataclass(slots=True)
class AIExecuteOptions:
    model: str | None = None
    temperature: float | None = None
    response_format: dict[str, Any] | None = None
    extra_body: dict[str, Any] | None = None
    enable_think_output: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AIExecuteResult:
    answer: str
    trace_id: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    trace: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class AIService(Protocol):
    def execute(
        self,
        capability_key: str,
        variables: Mapping[str, Any],
        *,
        options: AIExecuteOptions | None = None,
    ) -> AIExecuteResult:
        ...
