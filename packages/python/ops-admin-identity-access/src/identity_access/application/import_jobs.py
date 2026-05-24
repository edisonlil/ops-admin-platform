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
_active_job_id: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ImportJob:
    id: str
    kind: str
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


def start_import_job(kind: str, runner: JobRunner) -> dict[str, Any]:
    global _active_job_id
    with _lock:
        active = _jobs.get(_active_job_id or "")
        if active and active.status in ACTIVE_STATUSES:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已有导入任务正在执行，请等待完成后再导入")
        job = ImportJob(id=uuid4().hex, kind=kind)
        _jobs[job.id] = job
        _active_job_id = job.id
        _executor.submit(_run_job, job.id, runner)
        return job.to_dict()


def current_import_job() -> dict[str, Any] | None:
    with _lock:
        if _active_job_id and _active_job_id in _jobs:
            return _jobs[_active_job_id].to_dict()
        if not _jobs:
            return None
        latest = max(_jobs.values(), key=lambda item: item.create_time)
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
        _update_job(job_id, status="failed", progress=100, message="导入失败", error=str(exc), ended_at=now_iso())


def _update_job(job_id: str, **changes: Any) -> None:
    global _active_job_id
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for key, value in changes.items():
            if key == "progress":
                value = max(0, min(100, int(value)))
            setattr(job, key, value)
        if job.status in TERMINAL_STATUSES and _active_job_id == job_id:
            _active_job_id = job_id
