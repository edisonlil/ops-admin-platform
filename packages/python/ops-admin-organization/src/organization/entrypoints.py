from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from organization.application.services import configure_repository
from organization.infrastructure.persistence import repositories
from organization.infrastructure.persistence.bootstrap import ensure_organization_schema
from organization.interfaces.http.router import router


configure_repository(repositories)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"organization": ensure_organization_schema}
