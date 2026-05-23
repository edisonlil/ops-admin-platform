from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from file_management.application import services
from file_management.infrastructure.persistence import repositories
from file_management.infrastructure.persistence.bootstrap import ensure_file_management_schema
from file_management.infrastructure.storage.minio_storage import MinioObjectStorage
from file_management.interfaces.http.router import router


services.configure_repository(repositories)
services.configure_storage(MinioObjectStorage())


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"file_management": ensure_file_management_schema}
