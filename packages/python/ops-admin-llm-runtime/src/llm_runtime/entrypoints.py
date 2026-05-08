from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from llm_runtime.infrastructure.persistence.bootstrap import ensure_llm_schema
from llm_runtime.interfaces.http.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"llm_runtime": ensure_llm_schema}
