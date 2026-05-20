from __future__ import annotations

import threading
from typing import Any


_ready_targets: set[str] = set()
_ready_targets_lock = threading.Lock()


def readiness_key(conn: Any, schema_name: str) -> str:
    backend = str(getattr(conn, "backend", "sqlite"))
    database = str(getattr(conn, "database_identity", "") or "")
    return f"{schema_name}:{backend}:{database}"


def is_ready(conn: Any, schema_name: str) -> bool:
    with _ready_targets_lock:
        return readiness_key(conn, schema_name) in _ready_targets


def mark_ready(conn: Any, schema_name: str) -> None:
    with _ready_targets_lock:
        _ready_targets.add(readiness_key(conn, schema_name))


def clear_readiness() -> None:
    with _ready_targets_lock:
        _ready_targets.clear()
