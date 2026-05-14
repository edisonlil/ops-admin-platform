from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from authorization.application.services import BuiltinDataAccessFilterProvider, configure_repository
from authorization.infrastructure.persistence import repositories
from authorization.infrastructure.persistence.bootstrap import ensure_authorization_schema
from authorization.interfaces.http.router import router
from system.application.data_access import configure_data_access_filter_provider


configure_repository(repositories)
configure_data_access_filter_provider(BuiltinDataAccessFilterProvider())


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"authorization": ensure_authorization_schema}
