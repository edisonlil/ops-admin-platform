from __future__ import annotations

import contextvars
import hashlib
import queue
import re
import threading
import time
from datetime import datetime
from typing import Any

from audit_logging.application.ports import AuditLogRepository
from audit_logging.domain.models import AuditLoggingSettings
from audit_logging.domain.models import (
    LOG_CATEGORY_API,
    LOG_CATEGORY_OPERATION,
    LOG_CATEGORY_SQL,
    LOG_CATEGORY_SYSTEM,
    LOG_CATEGORY_VISITOR,
    LOG_CATEGORIES,
)
from system.application.tenancy import current_tenant_scope_or_none
from system.interfaces.http import current_request_id


_repository: AuditLogRepository | None = None
_queue: queue.Queue[dict[str, Any]] | None = None
_worker: threading.Thread | None = None
_stop_event = threading.Event()
_stats = {"accepted": 0, "dropped": 0, "written": 0, "failed": 0}
_suppress_var: contextvars.ContextVar[bool] = contextvars.ContextVar("audit_logging_suppress", default=False)
_settings_cache: dict[int, AuditLoggingSettings] = {}
_settings_cache_lock = threading.Lock()

DEFAULT_QUEUE_SIZE = 10000
DEFAULT_BATCH_SIZE = 100
DEFAULT_FLUSH_INTERVAL_SECONDS = 1.0
DEFAULT_SLOW_SQL_THRESHOLD_MS = 500
CATEGORY_ENABLED_SETTING = {
    LOG_CATEGORY_API: "api_log_enabled",
    LOG_CATEGORY_OPERATION: "operation_log_enabled",
    LOG_CATEGORY_SQL: "sql_log_enabled",
    LOG_CATEGORY_SYSTEM: "system_log_enabled",
    LOG_CATEGORY_VISITOR: "visitor_log_enabled",
}


def configure_repository(repository: AuditLogRepository) -> None:
    global _repository
    _repository = repository
    clear_settings_cache()


def clear_settings_cache(tenant_id: int | None = None) -> None:
    with _settings_cache_lock:
        if tenant_id is None:
            _settings_cache.clear()
            return
        _settings_cache.pop(int(tenant_id or 0), None)


def cache_settings(settings: AuditLoggingSettings) -> None:
    with _settings_cache_lock:
        _settings_cache[int(settings.tenant_id or 0)] = settings


def suppress_logging() -> contextvars.Token[bool]:
    return _suppress_var.set(True)


def reset_suppress_logging(token: contextvars.Token[bool]) -> None:
    _suppress_var.reset(token)


def is_suppressed() -> bool:
    return bool(_suppress_var.get())


def start_worker() -> None:
    global _queue, _worker
    if _queue is None:
        _queue = queue.Queue(maxsize=DEFAULT_QUEUE_SIZE)
    if _worker and _worker.is_alive():
        return
    _stop_event.clear()
    _worker = threading.Thread(target=_worker_loop, name="audit-log-worker", daemon=True)
    _worker.start()


def stop_worker(timeout: float = 2.0) -> None:
    _stop_event.set()
    worker = _worker
    if worker and worker.is_alive():
        worker.join(timeout=timeout)


def flush_now() -> None:
    records: list[dict[str, Any]] = []
    current_queue = _queue
    if current_queue is None:
        return
    while True:
        try:
            records.append(current_queue.get_nowait())
        except queue.Empty:
            break
    _write_batch(records)


def dispatcher_stats() -> dict[str, int]:
    size = _queue.qsize() if _queue else 0
    return {**_stats, "queued": size}


def reset_for_tests() -> None:
    global _queue, _worker
    stop_worker()
    _queue = None
    _worker = None
    _stop_event.clear()
    clear_settings_cache()
    for key in _stats:
        _stats[key] = 0


def enqueue_log(category: str, payload: dict[str, Any], *, priority: str = "normal") -> bool:
    if category not in LOG_CATEGORIES or is_suppressed():
        return False
    if _repository is None:
        _stats["dropped"] += 1
        return False
    if _queue is None:
        _stats["dropped"] += 1
        return False
    record = normalize_payload(category, payload)
    if not category_log_enabled(category, int(record.get("tenant_id") or 0)):
        return False
    try:
        assert _queue is not None
        _queue.put_nowait(record)
    except queue.Full:
        _stats["dropped"] += 1
        return False
    _stats["accepted"] += 1
    return True


def record_api_log(payload: dict[str, Any]) -> bool:
    return enqueue_log(LOG_CATEGORY_API, payload, priority="high" if int(payload.get("status_code") or 0) >= 500 else "normal")


def record_system_log(payload: dict[str, Any]) -> bool:
    severity = str(payload.get("severity") or "info")
    return enqueue_log(LOG_CATEGORY_SYSTEM, payload, priority="high" if severity in {"error", "critical"} else "normal")


def record_visitor_log(payload: dict[str, Any]) -> bool:
    return enqueue_log(LOG_CATEGORY_VISITOR, payload)


def observe_sql(
    sql: str,
    params: tuple[Any, ...],
    duration_ms: float,
    success: bool,
    error_message: str,
    backend: str,
    readonly: bool,
) -> None:
    if is_suppressed() or not should_record_sql(sql, duration_ms, success):
        return
    template = sql_template(sql)
    scope = current_tenant_scope_or_none()
    tenant_id = scope_tenant_id(scope)
    enqueue_log(
        LOG_CATEGORY_SQL,
        {
            "tenant_id": tenant_id,
            "request_id": current_request_id(),
            "event_action": statement_type(template),
            "event_outcome": "success" if success else "failed",
            "severity": "warning" if success else "error",
            "database_backend": backend,
            "statement_type": statement_type(template),
            "sql_template": template,
            "sql_fingerprint": hashlib.sha256(template.encode("utf-8")).hexdigest(),
            "duration_ms": int(duration_ms),
            "success": success,
            "error_message": error_message,
            "summary": "慢 SQL" if success else "SQL 执行失败",
            "source_module": "database",
            "actor_user_id": scope_principal_id(scope),
            "actor_name": scope_principal_name(scope),
            "actor_type": scope_actor_type(scope),
        },
        priority="high" if not success else "normal",
    )


def should_record_sql(sql: str, duration_ms: float, success: bool) -> bool:
    if not sql.strip():
        return False
    lowered = sql.lower()
    if "audit_" in lowered or is_schema_introspection_sql(lowered):
        return False
    if not effective_settings_value("sql_log_enabled", True, tenant_id=current_scope_tenant_id()):
        return False
    if not success:
        return True
    return duration_ms >= effective_slow_sql_threshold_ms()


def is_schema_introspection_sql(lowered_sql: str) -> bool:
    compact = " ".join(lowered_sql.split())
    return (
        compact.startswith("pragma ")
        or "sqlite_master" in compact
        or "sqlite_schema" in compact
        or "information_schema." in compact
        or "pg_catalog." in compact
        or "pg_indexes" in compact
        or compact.startswith("show index ")
        or compact.startswith("show indexes ")
        or compact.startswith("show columns ")
        or compact.startswith("show full columns ")
    )


def effective_slow_sql_threshold_ms() -> int:
    return int(effective_settings_value("slow_sql_threshold_ms", DEFAULT_SLOW_SQL_THRESHOLD_MS, tenant_id=current_scope_tenant_id()))


def category_log_enabled(category: str, tenant_id: int) -> bool:
    key = CATEGORY_ENABLED_SETTING.get(category)
    if not key:
        return True
    return bool(effective_settings_value(key, True, tenant_id=tenant_id))


def effective_settings_value(key: str, default: Any, *, tenant_id: int = 0) -> Any:
    settings = effective_settings(int(tenant_id or 0))
    if settings is None:
        return default
    return getattr(settings, key, default)


def effective_settings(tenant_id: int) -> AuditLoggingSettings | None:
    if _repository is None:
        return None
    normalized_tenant_id = int(tenant_id or 0)
    with _settings_cache_lock:
        cached = _settings_cache.get(normalized_tenant_id)
    if cached is not None:
        return cached
    token = suppress_logging()
    try:
        settings = _repository.get_effective_settings(normalized_tenant_id)
    except Exception:
        return None
    finally:
        reset_suppress_logging(token)
    cache_settings(settings)
    return settings


def normalize_payload(category: str, payload: dict[str, Any]) -> dict[str, Any]:
    event_time = str(payload.get("event_time") or datetime.now().isoformat(timespec="microseconds"))
    normalized = dict(payload)
    normalized["category"] = category
    normalized["tenant_id"] = resolved_payload_tenant_id(normalized)
    normalized.setdefault("event_time", event_time)
    normalized.setdefault("event_outcome", "success")
    normalized.setdefault("severity", "info")
    normalized.setdefault("source_module", "")
    normalized.setdefault("request_id", "")
    normalized.setdefault("summary", "")
    normalized.setdefault("detail", {})
    normalized.setdefault("creator", "audit-worker")
    normalized.setdefault("editor", "audit-worker")
    return normalized


def resolved_payload_tenant_id(payload: dict[str, Any]) -> int:
    if "tenant_id" in payload and payload.get("tenant_id") is not None:
        return int(payload.get("tenant_id") or 0)
    return current_scope_tenant_id()


def current_scope_tenant_id() -> int:
    return scope_tenant_id(current_tenant_scope_or_none())


def scope_tenant_id(scope: Any) -> int:
    if scope is None:
        return 0
    return int(getattr(scope, "tenant_id", 0) or 0)


def scope_principal_id(scope: Any) -> int | None:
    if scope is None:
        return None
    principal_id = getattr(scope, "principal_id", None)
    return int(principal_id) if principal_id is not None else None


def scope_principal_name(scope: Any) -> str:
    if scope is None:
        return ""
    return str(getattr(scope, "principal_name", "") or "")


def scope_actor_type(scope: Any) -> str:
    if scope is None:
        return ""
    return str(getattr(scope, "source", "") or "")


def _worker_loop() -> None:
    batch: list[dict[str, Any]] = []
    last_flush = time.monotonic()
    while not _stop_event.is_set():
        try:
            assert _queue is not None
            item = _queue.get(timeout=0.2)
            batch.append(item)
        except queue.Empty:
            pass
        elapsed = time.monotonic() - last_flush
        if batch and (len(batch) >= DEFAULT_BATCH_SIZE or elapsed >= DEFAULT_FLUSH_INTERVAL_SECONDS):
            _write_batch(batch)
            batch = []
            last_flush = time.monotonic()
    if batch:
        _write_batch(batch)


def _write_batch(records: list[dict[str, Any]]) -> None:
    if not records or _repository is None:
        return
    token = suppress_logging()
    try:
        _repository.insert_many(records)
        _stats["written"] += len(records)
    except Exception:
        _stats["failed"] += len(records)
    finally:
        reset_suppress_logging(token)


def sql_template(sql: str) -> str:
    text = re.sub(r"\s+", " ", sql.strip())
    text = re.sub(r"'(?:''|[^'])*'", "?", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "?", text)
    return text[:4000]


def statement_type(sql: str) -> str:
    first = (sql.strip().split(" ", 1)[0] or "").lower()
    return first[:40]
