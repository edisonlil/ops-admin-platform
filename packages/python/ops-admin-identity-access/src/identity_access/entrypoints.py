from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from identity_access.infrastructure.persistence.common import initialize_auth_storage
from identity_access.interfaces.http.router import router


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"identity_access": initialize_auth_storage}
