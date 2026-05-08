from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from system.interfaces.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {}
