from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ai_capabilities.application.ai_service import AICapabilityService
from ai_capabilities.application.services import configure_repository
from ai_capabilities.infrastructure.persistence import repositories
from ai_capabilities.infrastructure.persistence.bootstrap import ensure_ai_capabilities_schema
from ai_capabilities.interfaces.http.router import router
from ai_service_api import register_ai_service

configure_repository(repositories)

register_ai_service(AICapabilityService())


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"ai_capabilities": ensure_ai_capabilities_schema}
