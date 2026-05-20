from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from metadata_support.application.services import configure_repository
from metadata_support.infrastructure.persistence import repositories
from metadata_support.infrastructure.persistence.bootstrap import ensure_metadata_support_schema
from metadata_support.interfaces.http.router import router


configure_repository(repositories)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"metadata_support": ensure_metadata_support_schema}
