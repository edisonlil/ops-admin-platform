from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from identity_access.application import api_key_service, auth_service, rbac_service
from identity_access.infrastructure.persistence import repositories
from identity_access.infrastructure import security
from identity_access.infrastructure.persistence.common import initialize_auth_storage
from identity_access.interfaces.http.router import router


auth_service.configure_repository(repositories)
auth_service.configure_security(security)
api_key_service.configure_repository(repositories)
rbac_service.configure_repository(repositories)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"identity_access": initialize_auth_storage}
