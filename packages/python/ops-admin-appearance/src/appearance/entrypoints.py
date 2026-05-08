from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from appearance.infrastructure.persistence.bootstrap import ensure_appearance_schema
from appearance.interfaces.http.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"appearance": ensure_appearance_schema}
