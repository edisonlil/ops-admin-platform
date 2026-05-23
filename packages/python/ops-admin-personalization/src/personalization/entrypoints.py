from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from personalization.application.services import configure_repository
from personalization.infrastructure.persistence.bootstrap import ensure_personalization_schema
from personalization.infrastructure.persistence import repositories
from personalization.interfaces.http.router import router


configure_repository(repositories)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"personalization": ensure_personalization_schema}
