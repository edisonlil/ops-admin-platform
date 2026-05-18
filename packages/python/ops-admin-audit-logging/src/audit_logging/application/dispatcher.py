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
from audit_logging.domain.models import LOG_CATEGORY_API, LOG_CATEGORY_SQL, LOG_CATEGORIES
from system.application.tenancy import current_tenant_scope, current_tenant_scope_or_none


_repository: AuditLogRepository | None = None
_queue: queue.Queue[dict[str, Any]] | None = None
_worker: threading.Thread | None = None
_stop_event = threading.Event()
_stats = {"accepted": 0, "dropped": 0, "written": 0, "failed": 0}
_suppress_var: contextvars.ContextVar[bool] = contextvars.ContextVar("audit_logging_suppress", default=False)

DEFAULT_QUEUE_SIZE = 10000
DEFAULT_BATCH_SIZE = 100
DEFAULT_FLUSH_INTERVAL_SECONDS = 1.0
DEFAULT_SLOW_SQL_THRESHOLD_MS = 500


def configure_repository(repository: AuditLogRepository) -> None:
    global _repository
    _repository = repository


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
    tenant_id = int(getattr(current_tenant_scope(), "tenant_id", 0) or 0)
    enqueue_log(
        LOG_CATEGORY_SQL,
        {
            "tenant_id": tenant_id,
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
            "summary": "慢 SQL" if success else "SQL 执行错误",
            "source_module": "database",
        },
        priority="high" if not success else "normal",
    )


def should_record_sql(sql: str, duration_ms: float, success: bool) -> bool:
    if not sql.strip():
        return False
    lowered = sql.lower()
    if "audit_" in lowered:
        return False
    if not effective_settings_value("sql_log_enabled", True):
        return False
    if not success:
        return True
    return duration_ms >= effective_slow_sql_threshold_ms()


def effective_slow_sql_threshold_ms() -> int:
    return int(effective_settings_value("slow_sql_threshold_ms", DEFAULT_SLOW_SQL_THRESHOLD_MS))


def effective_settings_value(key: str, default: Any) -> Any:
    if _repository is None:
        return default
    token = suppress_logging()
    try:
        return getattr(_repository.get_effective_settings(0), key)
    except Exception:
        return default
    finally:
        reset_suppress_logging(token)


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
    scope = current_tenant_scope_or_none()
    if scope is None:
        return 0
    return int(getattr(scope, "tenant_id", 0) or 0)


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
