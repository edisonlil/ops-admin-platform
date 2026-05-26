from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from fastapi import HTTPException, status


TERMINAL_STATUSES = {"succeeded", "failed"}
ACTIVE_STATUSES = {"pending", "running"}
ProgressUpdater = Callable[[int, str], None]
JobRunner = Callable[[ProgressUpdater], dict[str, Any]]

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="identity-import")
_lock = Lock()
_jobs: dict[str, ImportJob] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ImportJob:
    id: str
    kind: str
    scope_id: int | None = None
    status: str = "pending"
    progress: int = 0
    message: str = "等待执行"
    result_count: int = 0
    error: str = ""
    create_time: str = field(default_factory=now_iso)
    started_at: str = ""
    ended_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "scope_id": self.scope_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "result_count": self.result_count,
            "error": self.error,
            "create_time": self.create_time,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "is_active": self.status in ACTIVE_STATUSES,
        }


def start_import_job(kind: str, runner: JobRunner, *, scope_id: int | None = None) -> dict[str, Any]:
    with _lock:
        active = next(
            (
                job
                for job in _jobs.values()
                if job.kind == kind
                and job.scope_id == scope_id
                and job.status in ACTIVE_STATUSES
            ),
            None,
        )
        if active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已有导入任务正在执行，请等待完成后再导入")
        job = ImportJob(id=uuid4().hex, kind=kind, scope_id=scope_id)
        _jobs[job.id] = job
        _executor.submit(_run_job, job.id, runner)
        return job.to_dict()


def current_import_job(kind: str | None = None, *, scope_id: int | None = None) -> dict[str, Any] | None:
    with _lock:
        jobs = [
            job
            for job in _jobs.values()
            if (kind is None or job.kind == kind)
            and (scope_id is None or job.scope_id == scope_id)
        ]
        if not jobs:
            return None
        active = [job for job in jobs if job.status in ACTIVE_STATUSES]
        latest = max(active or jobs, key=lambda item: item.create_time)
        return latest.to_dict()


def get_import_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        return job.to_dict() if job else None


def _run_job(job_id: str, runner: JobRunner) -> None:
    _update_job(job_id, status="running", progress=5, message="开始导入", started_at=now_iso())
    try:
        result = runner(lambda progress, message: _update_job(job_id, progress=progress, message=message))
        count = int(result.get("count", 0) or 0)
        _update_job(job_id, status="succeeded", progress=100, message=f"导入完成，共导入 {count} 条数据", result_count=count, ended_at=now_iso())
    except Exception as exc:
        _update_job(job_id, status="failed", progress=100, message="导入失败", error=_job_error_message(exc), ended_at=now_iso())


def _job_error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, str):
            return detail
        if detail:
            return str(detail)
    message = str(exc).strip()
    return message or "导入失败，请查看后端日志"


def _update_job(job_id: str, **changes: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for key, value in changes.items():
            if key == "progress":
                value = max(0, min(100, int(value)))
            setattr(job, key, value)


def reset_import_jobs_for_tests() -> None:
    with _lock:
        _jobs.clear()
