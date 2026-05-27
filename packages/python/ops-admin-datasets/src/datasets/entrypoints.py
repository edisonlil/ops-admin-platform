from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from datasets.application import services
from datasets.infrastructure.query_executor import SqlDatasetExecutor
from datasets.infrastructure.schema_introspection import DatabaseSourceSchemaInspector
from datasets.infrastructure.persistence import repositories
from datasets.infrastructure.persistence.bootstrap import ensure_datasets_schema
from datasets.interfaces.http.router import router


services.configure_repository(repositories)
services.configure_external_executor(SqlDatasetExecutor())
services.configure_source_schema_inspector(DatabaseSourceSchemaInspector())


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"datasets": ensure_datasets_schema}
