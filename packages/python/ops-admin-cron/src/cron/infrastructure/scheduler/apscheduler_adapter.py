from __future__ import annotations

from typing import Any

from cron.domain.models import CronSchedule, CronTask, ExternalScheduleBinding


class APSchedulerAdapter:
    """Adapter boundary for the built-in scheduler worker.

    The API process does not instantiate this adapter. A dedicated cron worker
    should wire APScheduler, repositories, and a TaskDispatcher together.
    """

    scheduler_type = "apscheduler"

    def __init__(self, scheduler: Any) -> None:
        self.scheduler = scheduler

    def upsert_schedule(self, task: CronTask, schedule: CronSchedule) -> ExternalScheduleBinding:
        raise NotImplementedError("APScheduler worker integration is not enabled yet")

    def pause_schedule(self, task_id: int) -> None:
        raise NotImplementedError("APScheduler worker integration is not enabled yet")

    def resume_schedule(self, task_id: int) -> None:
        raise NotImplementedError("APScheduler worker integration is not enabled yet")

    def delete_schedule(self, task_id: int) -> None:
        raise NotImplementedError("APScheduler worker integration is not enabled yet")

    def trigger_now(self, task_id: int, reason: str) -> None:
        raise NotImplementedError("APScheduler worker integration is not enabled yet")

    def sync_schedule_state(self, task_id: int) -> dict[str, Any]:
        return {"task_id": task_id, "scheduler_type": self.scheduler_type, "status": "not_enabled"}
