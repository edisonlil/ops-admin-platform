from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from file_management.infrastructure.persistence.bootstrap import ensure_file_management_schema
from file_management.interfaces.http.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"file_management": ensure_file_management_schema}
