from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from personalization.infrastructure.persistence.bootstrap import ensure_personalization_schema
from personalization.interfaces.http.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"personalization": ensure_personalization_schema}
