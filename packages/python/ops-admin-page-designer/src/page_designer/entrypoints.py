from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from page_designer.application import services
from page_designer.application.menu_ports import IdentityAccessMenuMountPort
from page_designer.infrastructure.persistence import repositories
from page_designer.infrastructure.persistence.bootstrap import ensure_page_designer_schema
from page_designer.interfaces.http.router import router


services.configure_repository(repositories)
services.configure_menu_port(IdentityAccessMenuMountPort())


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"page_designer": ensure_page_designer_schema}
