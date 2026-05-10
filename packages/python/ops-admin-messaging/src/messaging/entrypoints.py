from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from messaging.infrastructure.persistence.bootstrap import ensure_messaging_schema
from messaging.interfaces.http.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"messaging": ensure_messaging_schema}
