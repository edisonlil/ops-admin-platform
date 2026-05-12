from __future__ import annotations

from typing import Any

from cron.application.executor import CronTaskExecutor
from cron.application.ports import TaskDispatcher
from cron.domain.models import CronTaskDetail
from cron.infrastructure.commands.registry import build_default_dispatcher
from cron.infrastructure.persistence import repositories


class CronWorker:
    def __init__(self, *, scheduler: Any, dispatcher: TaskDispatcher | None = None, worker_id: str = "cron-worker") -> None:
        self.scheduler = scheduler
        self.executor = CronTaskExecutor(
            repository=repositories,
            dispatcher=dispatcher or build_default_dispatcher(),
            worker_id=worker_id,
        )
        self.worker_id = worker_id

    def load_enabled_tasks(self) -> list[CronTaskDetail]:
        return [detail for detail in repositories.list_enabled_task_details() if detail.schedule is not None]

    def register_enabled_tasks(self) -> int:
        enabled_details = self.load_enabled_tasks()
        enabled_job_ids = {external_job_id(detail.task.id) for detail in enabled_details}
        for job in self.scheduler.get_jobs():
            if str(job.id).startswith("cron-task-") and job.id not in enabled_job_ids:
                self.scheduler.remove_job(job.id)
        count = 0
        for detail in enabled_details:
            self.scheduler.add_job(
                self.executor.execute_scheduled_task,
                trigger=build_trigger(detail),
                args=[detail],
                id=external_job_id(detail.task.id),
                name=detail.task.task_key,
                replace_existing=True,
                max_instances=1 if detail.task.concurrency_policy == "forbid" else 3,
                misfire_grace_time=max(detail.task.timeout_seconds, 1),
                coalesce=detail.task.misfire_policy != "catch_up_all",
            )
            count += 1
        return count

    def sync_enabled_tasks(self) -> None:
        try:
            self.register_enabled_tasks()
        except Exception as exc:
            print(f"cron worker sync failed: {exc}", flush=True)

    def start(self) -> None:
        registered = self.register_enabled_tasks()
        print(f"cron worker registered {registered} enabled task(s)", flush=True)
        self.scheduler.add_job(
            self.sync_enabled_tasks,
            trigger="interval",
            seconds=10,
            id="cron-worker-sync",
            name="cron worker schedule sync",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown()


def external_job_id(task_id: int) -> str:
    return f"cron-task-{task_id}"


def build_trigger(detail: CronTaskDetail) -> Any:
    if detail.schedule is None:
        raise ValueError("cron task has no schedule")
    from cron.infrastructure.scheduler.apscheduler_adapter import build_trigger as build_apscheduler_trigger

    return build_apscheduler_trigger(detail.schedule)
