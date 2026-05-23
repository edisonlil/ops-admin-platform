from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from appearance.application.services import configure_repository
from appearance.infrastructure.persistence.bootstrap import ensure_appearance_schema
from appearance.infrastructure.persistence import repository
from appearance.interfaces.http.router import router


configure_repository(repository)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"appearance": ensure_appearance_schema}
