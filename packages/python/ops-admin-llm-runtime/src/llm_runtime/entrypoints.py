from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from llm_runtime.application.gateway import configure_repository as configure_gateway_repository
from llm_runtime.application.services import configure_repository as configure_services_repository
from llm_runtime.infrastructure.persistence import repositories
from llm_runtime.infrastructure.persistence.bootstrap import ensure_llm_schema
from llm_runtime.interfaces.http.router import router

configure_services_repository(repositories)
configure_gateway_repository(repositories)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"llm_runtime": ensure_llm_schema}
