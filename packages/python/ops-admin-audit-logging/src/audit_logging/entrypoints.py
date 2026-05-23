from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from audit_logging.application import dispatcher
from audit_logging.application.services import configure_repository
from audit_logging.infrastructure.persistence import repositories
from audit_logging.infrastructure.persistence.bootstrap import ensure_audit_logging_schema
from audit_logging.interfaces.http.router import router
from system.application.database import configure_sql_observer


configure_repository(repositories)
dispatcher.configure_repository(repositories)
configure_sql_observer(dispatcher.observe_sql)


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"audit_logging": ensure_audit_logging_schema}
