from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ai_assets.application.services import configure_repository
from ai_assets.infrastructure.persistence.bootstrap import ensure_ai_assets_schema
from ai_assets.infrastructure.persistence import repositories
from ai_assets.interfaces.http.router import router


configure_repository(repositories)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"ai_assets": ensure_ai_assets_schema}
