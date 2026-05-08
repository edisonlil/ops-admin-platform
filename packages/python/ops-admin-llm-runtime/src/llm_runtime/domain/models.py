from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMProvider:
    provider_key: str
    display_name: str
    base_url: str
    api_key: str
    auth_type: str = "bearer"
    extra_headers: dict[str, Any] = field(default_factory=dict)
    extra_body: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass(frozen=True)
class LLMModel:
    model_key: str
    provider_key: str
    model_name: str
    display_name: str = ""
    capabilities: dict[str, Any] = field(default_factory=dict)
    context_window: int | None = None
    enabled: bool = True


@dataclass(frozen=True)
class LLMTask:
    task_key: str
    context_key: str
    scene_key: str
    task_name: str
    display_name: str = ""
    description: str = ""
    owner_context: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class RoutingEntry:
    id: int
    policy_id: int
    model_key: str
    provider_key: str
    model_name: str
    provider_display_name: str
    base_url: str
    api_key: str
    provider_extra_body: dict[str, Any] = field(default_factory=dict)
    model_capabilities: dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    temperature: float = 0.1
    timeout_seconds: float = 120.0
    max_retries: int = 0
    response_format: str = "text"
    extra_body: dict[str, Any] = field(default_factory=dict)
    enable_think_output: bool = False


@dataclass(frozen=True)
class RoutingPolicy:
    id: int
    route_key: str
    display_name: str
    strategy: str
    entries: list[RoutingEntry]


@dataclass(frozen=True)
class RouteResolution:
    task_key: str
    route_key: str
    policy: RoutingPolicy
