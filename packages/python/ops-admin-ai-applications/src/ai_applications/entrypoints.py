from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ai_applications.application.services import configure_repository
from ai_applications.infrastructure.persistence import repositories
from ai_applications.infrastructure.persistence.bootstrap import ensure_ai_applications_schema
from ai_applications.interfaces.http.router import router

configure_repository(repositories)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"ai_applications": ensure_ai_applications_schema}
