from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ai_capabilities.infrastructure.persistence.bootstrap import ensure_ai_capabilities_schema
from ai_capabilities.interfaces.http.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"ai_capabilities": ensure_ai_capabilities_schema}

