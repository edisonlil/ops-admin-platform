from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from basic_data.application.services import configure_repository
from basic_data.infrastructure.persistence.bootstrap import ensure_basic_data_schema
from basic_data.infrastructure.persistence import repositories
from basic_data.interfaces.http.router import router


configure_repository(repositories)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"basic_data": ensure_basic_data_schema}
