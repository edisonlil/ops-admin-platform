from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from cron.domain.models import CronRun, CronTaskDetail, CronSchedule, CronTask, ExternalScheduleBinding


class Clock(Protocol):
    def now(self) -> datetime:
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class SchedulerAdapter(Protocol):
    def upsert_schedule(self, task: CronTask, schedule: CronSchedule) -> ExternalScheduleBinding:
        ...

    def pause_schedule(self, task_id: int) -> None:
        ...

    def resume_schedule(self, task_id: int) -> None:
        ...

    def delete_schedule(self, task_id: int) -> None:
        ...

    def trigger_now(self, task_id: int, reason: str) -> None:
        ...

    def sync_schedule_state(self, task_id: int) -> dict[str, Any]:
        ...


class TaskDispatcher(Protocol):
    def dispatch(self, execution_target: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class NoopTaskDispatcher:
    def dispatch(self, execution_target: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"dispatched": False, "execution_target": execution_target, "payload": payload}


class CronRepository(Protocol):
    def list_tasks(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[CronTaskDetail], int]:
        ...

    def get_task_detail(self, *, tenant_id: int, task_id: int) -> CronTaskDetail | None:
        ...

    def save_task(self, *, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> CronTaskDetail:
        ...

    def set_task_status(
        self,
        *,
        tenant_id: int,
        task_id: int,
        status: str,
        actor: str,
        actor_id: int | None,
    ) -> CronTaskDetail | None:
        ...

    def delete_task(self, *, tenant_id: int, task_id: int, actor: str, actor_id: int | None) -> CronTaskDetail | None:
        ...

    def create_manual_run(
        self,
        *,
        tenant_id: int,
        task_id: int,
        payload: dict[str, Any],
        idempotency_key: str,
        actor: str,
        actor_id: int | None,
    ) -> CronRun:
        ...

    def list_runs(
        self,
        *,
        tenant_id: int,
        task_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CronRun], int]:
        ...

    def get_run(self, *, tenant_id: int, run_id: int) -> CronRun | None:
        ...

    def list_attempts(self, *, tenant_id: int, run_id: int) -> list[Any]:
        ...
