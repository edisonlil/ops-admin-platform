from __future__ import annotations

from datetime import datetime
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
        trigger = build_trigger(schedule)
        job_id = self.external_job_id(task.id)
        self.scheduler.add_job(
            self.trigger_now,
            trigger=trigger,
            args=[task.id, "schedule"],
            id=job_id,
            name=task.task_key,
            replace_existing=True,
            max_instances=1 if task.concurrency_policy == "forbid" else 3,
            misfire_grace_time=max(task.timeout_seconds, 1),
            coalesce=task.misfire_policy != "catch_up_all",
        )
        return ExternalScheduleBinding(
            id=0,
            tenant_id=task.tenant_id,
            task_id=task.id,
            scheduler_type=self.scheduler_type,
            external_id=job_id,
            status="active",
            metadata={"task_key": task.task_key},
            create_time="",
            update_time="",
        )

    def pause_schedule(self, task_id: int) -> None:
        self.scheduler.pause_job(self.external_job_id(task_id))

    def resume_schedule(self, task_id: int) -> None:
        self.scheduler.resume_job(self.external_job_id(task_id))

    def delete_schedule(self, task_id: int) -> None:
        job_id = self.external_job_id(task_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    def trigger_now(self, task_id: int, reason: str) -> None:
        job = self.scheduler.get_job(self.external_job_id(task_id))
        if job:
            job.modify(next_run_time=datetime.now(job.trigger.timezone if hasattr(job.trigger, "timezone") else None))

    def sync_schedule_state(self, task_id: int) -> dict[str, Any]:
        job = self.scheduler.get_job(self.external_job_id(task_id))
        return {
            "task_id": task_id,
            "scheduler_type": self.scheduler_type,
            "status": "active" if job else "missing",
            "next_run_time": job.next_run_time.isoformat() if job and job.next_run_time else None,
        }

    def external_job_id(self, task_id: int) -> str:
        return f"cron-task-{task_id}"


def build_trigger(schedule: CronSchedule) -> Any:
    if schedule.trigger_type == "cron":
        from apscheduler.triggers.cron import CronTrigger

        return build_cron_trigger(schedule.trigger_expression, schedule.timezone)
    if schedule.trigger_type == "interval":
        from apscheduler.triggers.interval import IntervalTrigger

        seconds = int(schedule.trigger_expression)
        return IntervalTrigger(seconds=seconds, timezone=schedule.timezone)
    if schedule.trigger_type == "date":
        from apscheduler.triggers.date import DateTrigger

        return DateTrigger(run_date=schedule.trigger_expression, timezone=schedule.timezone)
    raise ValueError(f"unsupported trigger_type: {schedule.trigger_type}")


def build_cron_trigger(expression: str, timezone: str) -> Any:
    from apscheduler.triggers.cron import CronTrigger

    parts = expression.split()
    if len(parts) == 5:
        minute, hour, day, month, day_of_week = parts
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=normalize_unspecified(day),
            month=normalize_unspecified(month),
            day_of_week=normalize_unspecified(day_of_week),
            timezone=timezone,
        )
    if len(parts) == 6:
        second, minute, hour, day, month, day_of_week = parts
        return CronTrigger(
            second=second,
            minute=minute,
            hour=hour,
            day=normalize_unspecified(day),
            month=normalize_unspecified(month),
            day_of_week=normalize_unspecified(day_of_week),
            timezone=timezone,
        )
    raise ValueError("cron expression must have 5 fields or 6 fields with seconds")


def normalize_unspecified(value: str) -> str:
    return "*" if value == "?" else value
