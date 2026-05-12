from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from cron.application.services import configure_dispatcher, configure_repository
from cron.infrastructure.commands.registry import build_default_dispatcher
from cron.infrastructure.persistence.bootstrap import ensure_cron_schema
from cron.infrastructure.persistence import repositories
from cron.interfaces.http.router import router

configure_repository(repositories)
configure_dispatcher(build_default_dispatcher())


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"cron": ensure_cron_schema}
