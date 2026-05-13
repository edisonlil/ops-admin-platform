from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ai_assets.infrastructure.persistence.bootstrap import ensure_ai_assets_schema
from ai_assets.interfaces.http.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"ai_assets": ensure_ai_assets_schema}
