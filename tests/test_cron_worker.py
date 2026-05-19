from __future__ import annotations

import unittest
import sqlite3
import tempfile
from importlib.util import find_spec
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from typing import Any

from cron.application.executor import CronTaskExecutor
from cron.domain.models import (
    ATTEMPT_STATUS_FAILED,
    ATTEMPT_STATUS_SUCCEEDED,
    RUN_STATUS_FAILED,
    RUN_STATUS_PENDING,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCEEDED,
    CronAttempt,
    CronRun,
    CronSchedule,
    CronTask,
    CronTaskDetail,
)
from cron.infrastructure.commands.registry import build_default_command_registry
from cron.infrastructure.persistence import repositories
from cron.infrastructure.persistence.bootstrap import ensure_cron_schema
from cron.infrastructure.scheduler.apscheduler_adapter import build_trigger
from cron.infrastructure.scheduler.worker import external_job_id
from system.application.data_access import DataAccessPredicate, SCOPE_SELF


class FakeRepository:
    def __init__(self) -> None:
        self.runs: dict[int, CronRun] = {}
        self.attempts: dict[int, CronAttempt] = {}
        self.next_run_id = 1
        self.next_attempt_id = 1

    def create_scheduled_run(
        self,
        *,
        tenant_id: int,
        task_id: int,
        schedule_id: int,
        fire_time: str,
        payload: dict[str, Any],
        idempotency_key: str,
        actor: str,
    ) -> CronRun:
        for run in self.runs.values():
            if run.idempotency_key == idempotency_key:
                return run
        run = CronRun(
            id=self.next_run_id,
            tenant_id=tenant_id,
            task_id=task_id,
            schedule_id=schedule_id,
            fire_time=fire_time,
            status=RUN_STATUS_PENDING,
            trigger_source="schedule",
            idempotency_key=idempotency_key,
            payload=payload,
            result={},
            started_time=None,
            finished_time=None,
            failure_code="",
            failure_message="",
            create_time=fire_time,
            update_time=fire_time,
        )
        self.runs[run.id] = run
        self.next_run_id += 1
        return run

    def mark_run_running(self, *, tenant_id: int, run_id: int, actor: str) -> CronRun | None:
        run = self.runs[run_id]
        updated = CronRun(**{**run.__dict__, "status": RUN_STATUS_RUNNING, "started_time": run.fire_time})
        self.runs[run_id] = updated
        return updated

    def start_attempt(self, *, tenant_id: int, run_id: int, worker_id: str, actor: str) -> CronAttempt:
        attempt = CronAttempt(
            id=self.next_attempt_id,
            tenant_id=tenant_id,
            run_id=run_id,
            attempt_number=len([item for item in self.attempts.values() if item.run_id == run_id]) + 1,
            status="running",
            worker_id=worker_id,
            started_time=self.runs[run_id].fire_time,
            finished_time=None,
            error_code="",
            error_message="",
            create_time=self.runs[run_id].fire_time,
            update_time=self.runs[run_id].fire_time,
        )
        self.attempts[attempt.id] = attempt
        self.next_attempt_id += 1
        return attempt

    def complete_attempt(
        self,
        *,
        tenant_id: int,
        attempt_id: int,
        status: str,
        error_code: str,
        error_message: str,
        actor: str,
    ) -> CronAttempt | None:
        attempt = self.attempts[attempt_id]
        updated = CronAttempt(
            **{
                **attempt.__dict__,
                "status": status,
                "finished_time": attempt.started_time,
                "error_code": error_code,
                "error_message": error_message,
            }
        )
        self.attempts[attempt_id] = updated
        return updated

    def complete_run(
        self,
        *,
        tenant_id: int,
        run_id: int,
        status: str,
        result: dict[str, Any] | None = None,
        failure_code: str,
        failure_message: str,
        actor: str,
    ) -> CronRun | None:
        run = self.runs[run_id]
        updated = CronRun(
            **{
                **run.__dict__,
                "status": status,
                "finished_time": run.fire_time,
                "result": result if isinstance(result, dict) else {},
                "failure_code": failure_code,
                "failure_message": failure_message,
            }
        )
        self.runs[run_id] = updated
        return updated


@dataclass
class RecordingDispatcher:
    should_fail: bool = False
    calls: list[tuple[str, dict[str, Any]]] | None = None

    def dispatch(self, execution_target: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.calls is None:
            self.calls = []
        self.calls.append((execution_target, payload))
        if self.should_fail:
            raise RuntimeError("dispatch failed")
        return {"ok": True}


class CronWorkerTests(unittest.TestCase):
    def test_executor_marks_run_and_attempt_succeeded(self) -> None:
        repository = FakeRepository()
        dispatcher = RecordingDispatcher()
        executor = CronTaskExecutor(repository=repository, dispatcher=dispatcher, worker_id="test-worker")
        result = executor.execute_scheduled_task(task_detail(), scheduled_fire_time=fixed_time())

        self.assertTrue(result["ok"])
        self.assertEqual(repository.runs[1].status, RUN_STATUS_SUCCEEDED)
        self.assertEqual(repository.runs[1].result, {"ok": True})
        self.assertEqual(repository.attempts[1].status, ATTEMPT_STATUS_SUCCEEDED)
        self.assertEqual(dispatcher.calls, [("system.health.snapshot", {"scope": "platform"})])

    def test_executor_marks_run_and_attempt_failed(self) -> None:
        repository = FakeRepository()
        dispatcher = RecordingDispatcher(should_fail=True)
        executor = CronTaskExecutor(repository=repository, dispatcher=dispatcher, worker_id="test-worker")
        result = executor.execute_scheduled_task(task_detail(), scheduled_fire_time=fixed_time())

        self.assertFalse(result["ok"])
        self.assertEqual(repository.runs[1].status, RUN_STATUS_FAILED)
        self.assertEqual(repository.runs[1].failure_code, "RuntimeError")
        self.assertEqual(repository.attempts[1].status, ATTEMPT_STATUS_FAILED)
        self.assertEqual(repository.attempts[1].error_message, "dispatch failed")

    def test_default_command_registry_dispatches_system_health_snapshot(self) -> None:
        registry = build_default_command_registry()
        result = registry.dispatch("system.health.snapshot", {"scope": "test"})

        self.assertEqual(result["command"], "system.health.snapshot")
        self.assertEqual(result["input"], {"scope": "test"})
        self.assertIn("health", result)

    @unittest.skipIf(find_spec("apscheduler") is None, "APScheduler is not installed in this test environment")
    def test_cron_trigger_accepts_six_field_expression_with_seconds(self) -> None:
        trigger = build_trigger(
            CronSchedule(
                id=10,
                tenant_id=1,
                task_id=1,
                trigger_type="cron",
                trigger_expression="0 0 0 1 * ?",
                timezone="UTC",
                start_time=None,
                end_time=None,
                next_fire_time=None,
                create_time="",
                update_time="",
            )
        )

        self.assertIn("cron", str(trigger))

    def test_external_job_id_is_stable_for_schedule_sync(self) -> None:
        self.assertEqual(external_job_id(42), "cron-task-42")

    def test_task_detail_honors_data_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cron.db"
            with mock.patch.dict(
                "os.environ",
                {
                    "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                    "FG_AGENT_DATABASE_URL": "",
                    "SUPABASE_DB_URL": "",
                    "DATABASE_URL": "",
                    "FG_AGENT_DB_PATH": str(db_path),
                },
                clear=False,
            ):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                try:
                    ensure_cron_schema(conn)
                    conn.commit()
                finally:
                    conn.close()
                detail = repositories.save_task(
                    tenant_id=7,
                    payload={
                        "task_key": "scoped.task",
                        "name": "Scoped Task",
                        "execution_target": "system.health.snapshot",
                        "owner_user_id": 10,
                    },
                    actor="owner",
                    actor_id=10,
                )

                allowed = repositories.get_task_detail(
                    tenant_id=7,
                    task_id=detail.task.id,
                    data_scope=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
                )
                denied = repositories.get_task_detail(
                    tenant_id=7,
                    task_id=detail.task.id,
                    data_scope=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=11),
                )

                self.assertIsNotNone(allowed)
                self.assertIsNone(denied)

    def test_repository_lists_tasks_with_dynamic_sort(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cron-sort.db"
            with mock.patch.dict(
                "os.environ",
                {
                    "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                    "FG_AGENT_DATABASE_URL": "",
                    "SUPABASE_DB_URL": "",
                    "DATABASE_URL": "",
                    "FG_AGENT_DB_PATH": str(db_path),
                },
                clear=False,
            ):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                try:
                    ensure_cron_schema(conn)
                    conn.commit()
                finally:
                    conn.close()

                repositories.save_task(
                    tenant_id=7,
                    payload={"task_key": "beta.task", "name": "Beta", "execution_target": "system.health.snapshot"},
                    actor="admin",
                    actor_id=1,
                )
                repositories.save_task(
                    tenant_id=7,
                    payload={"task_key": "alpha.task", "name": "Alpha", "execution_target": "system.health.snapshot"},
                    actor="admin",
                    actor_id=1,
                )

                items, total = repositories.list_tasks(
                    tenant_id=7,
                    page=1,
                    page_size=20,
                    sort_by="task_key",
                    sort_dir="asc",
                )

                self.assertEqual(total, 2)
                self.assertEqual([item.task.task_key for item in items], ["alpha.task", "beta.task"])

                with self.assertRaisesRegex(ValueError, "unsupported sort field"):
                    repositories.list_tasks(
                        tenant_id=7,
                        page=1,
                        page_size=20,
                        sort_by="bad_field",
                        sort_dir="asc",
                    )


def fixed_time() -> datetime:
    return datetime(2026, 5, 12, 1, 2, 3, tzinfo=timezone.utc)


def task_detail() -> CronTaskDetail:
    return CronTaskDetail(
        task=CronTask(
            id=1,
            tenant_id=1,
            task_key="system.health_snapshot",
            name="系统健康快照",
            description="",
            status="enabled",
            execution_target="system.health.snapshot",
            payload_schema_version=1,
            default_payload={"scope": "platform"},
            concurrency_policy="forbid",
            timeout_seconds=120,
            max_attempts=1,
            retry_delay_seconds=0,
            retry_backoff_multiplier=1,
            misfire_policy="skip",
            create_time="",
            update_time="",
        ),
        schedule=CronSchedule(
            id=10,
            tenant_id=1,
            task_id=1,
            trigger_type="cron",
            trigger_expression="*/5 * * * *",
            timezone="UTC",
            start_time=None,
            end_time=None,
            next_fire_time=None,
            create_time="",
            update_time="",
        ),
    )


if __name__ == "__main__":
    unittest.main()
