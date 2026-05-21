from __future__ import annotations

import contextlib
import io
import logging
from datetime import datetime, timezone
from typing import Any

from cron.application.ports import CronRepository, NoopTaskDispatcher, TaskDispatcher
from cron.domain.models import (
    ATTEMPT_STATUS_FAILED,
    ATTEMPT_STATUS_SUCCEEDED,
    RUN_STATUS_FAILED,
    RUN_STATUS_PENDING,
    RUN_STATUS_RUNNING,
    RUN_STATUS_STOPPED,
    RUN_STATUS_SUCCEEDED,
    CronTaskDetail,
    CronRun,
)


class CapturedDispatchError(Exception):
    def __init__(self, original: Exception, logs: dict[str, str]) -> None:
        super().__init__(str(original))
        self.original = original
        self.logs = logs


class CronTaskExecutor:
    def __init__(
        self,
        *,
        repository: CronRepository,
        dispatcher: TaskDispatcher | None = None,
        worker_id: str = "cron-worker",
    ) -> None:
        self.repository = repository
        self.dispatcher = dispatcher or NoopTaskDispatcher()
        self.worker_id = worker_id

    def execute_scheduled_task(
        self,
        detail: CronTaskDetail,
        *,
        scheduled_fire_time: datetime | None = None,
    ) -> dict[str, Any]:
        if detail.schedule is None:
            raise ValueError("cron task has no schedule")
        fire_time = scheduled_fire_time or datetime.now(timezone.utc)
        fire_time_text = fire_time.astimezone(timezone.utc).isoformat(timespec="microseconds")
        idempotency_key = f"schedule:{detail.schedule.id}:{fire_time_text}"
        run = self.repository.create_scheduled_run(
            tenant_id=detail.task.tenant_id,
            task_id=detail.task.id,
            schedule_id=detail.schedule.id,
            fire_time=fire_time_text,
            payload=detail.task.default_payload,
            idempotency_key=idempotency_key,
            actor=self.worker_id,
        )
        if run.status != RUN_STATUS_PENDING:
            return {"run": run.to_dict(), "attempt": None, "ok": True, "skipped": True}
        running_run = self.repository.mark_run_running(tenant_id=run.tenant_id, run_id=run.id, actor=self.worker_id)
        if not running_run or running_run.status != RUN_STATUS_RUNNING:
            current_run = self.repository.get_run(tenant_id=run.tenant_id, run_id=run.id)
            is_stopped = bool(current_run and current_run.status == RUN_STATUS_STOPPED)
            return {"run": (current_run or run).to_dict(), "attempt": None, "ok": not is_stopped, "stopped": is_stopped, "skipped": not is_stopped}
        attempt = self.repository.start_attempt(tenant_id=run.tenant_id, run_id=run.id, worker_id=self.worker_id, actor=self.worker_id)
        try:
            result, logs = self._dispatch_with_logs(detail.task.execution_target, run.payload)
        except CapturedDispatchError as captured:
            exc = captured.original
            current_run = self.repository.get_run(tenant_id=run.tenant_id, run_id=run.id)
            if current_run and current_run.status == RUN_STATUS_STOPPED:
                return {"run": current_run.to_dict(), "attempt": attempt.to_dict(), "ok": False, "stopped": True}
            error_message = str(exc)
            self.repository.complete_attempt(
                tenant_id=run.tenant_id,
                attempt_id=attempt.id,
                status=ATTEMPT_STATUS_FAILED,
                error_code=exc.__class__.__name__,
                error_message=error_message,
                actor=self.worker_id,
            )
            failed_run = self.repository.complete_run(
                tenant_id=run.tenant_id,
                run_id=run.id,
                status=RUN_STATUS_FAILED,
                result=attach_run_logs({}, captured.logs),
                failure_code=exc.__class__.__name__,
                failure_message=error_message,
                actor=self.worker_id,
            )
            return {"run": failed_run.to_dict() if failed_run else run.to_dict(), "attempt": attempt.to_dict(), "ok": False}
        current_run = self.repository.get_run(tenant_id=run.tenant_id, run_id=run.id)
        if current_run and current_run.status == RUN_STATUS_STOPPED:
            return {"run": current_run.to_dict(), "attempt": attempt.to_dict(), "result": result, "ok": False, "stopped": True}
        self.repository.complete_attempt(
            tenant_id=run.tenant_id,
            attempt_id=attempt.id,
            status=ATTEMPT_STATUS_SUCCEEDED,
            error_code="",
            error_message="",
            actor=self.worker_id,
        )
        succeeded_run = self.repository.complete_run(
            tenant_id=run.tenant_id,
            run_id=run.id,
            status=RUN_STATUS_SUCCEEDED,
            result=attach_run_logs(result if isinstance(result, dict) else {"value": result}, logs),
            failure_code="",
            failure_message="",
            actor=self.worker_id,
        )
        return {
            "run": succeeded_run.to_dict() if succeeded_run else run.to_dict(),
            "attempt": attempt.to_dict(),
            "result": result,
            "ok": True,
        }

    def _dispatch_with_logs(self, execution_target: str, payload: dict[str, Any]) -> tuple[Any, dict[str, str]]:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        log_handler = logging.StreamHandler(stderr_buffer)
        log_handler.setLevel(logging.INFO)
        logger = logging.getLogger()
        logger.addHandler(log_handler)
        try:
            try:
                with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                    result = self.dispatcher.dispatch(execution_target, payload)
            except Exception as exc:
                raise CapturedDispatchError(exc, build_run_logs(stdout_buffer.getvalue(), stderr_buffer.getvalue())) from exc
            return result, build_run_logs(stdout_buffer.getvalue(), stderr_buffer.getvalue())
        finally:
            logger.removeHandler(log_handler)

    def execute_manual_run(self, detail: CronTaskDetail, run: CronRun) -> dict[str, Any]:
        if run.status != RUN_STATUS_PENDING:
            return {"run": run.to_dict(), "attempt": None, "ok": True, "skipped": True}
        running_run = self.repository.mark_run_running(tenant_id=run.tenant_id, run_id=run.id, actor=self.worker_id)
        if not running_run or running_run.status != RUN_STATUS_RUNNING:
            current_run = self.repository.get_run(tenant_id=run.tenant_id, run_id=run.id)
            return {"run": (current_run or run).to_dict(), "attempt": None, "ok": False, "stopped": True}
        attempt = self.repository.start_attempt(tenant_id=run.tenant_id, run_id=run.id, worker_id=self.worker_id, actor=self.worker_id)
        try:
            result, logs = self._dispatch_with_logs(detail.task.execution_target, run.payload)
        except CapturedDispatchError as captured:
            exc = captured.original
            current_run = self.repository.get_run(tenant_id=run.tenant_id, run_id=run.id)
            if current_run and current_run.status == RUN_STATUS_STOPPED:
                return {"run": current_run.to_dict(), "attempt": attempt.to_dict(), "ok": False, "stopped": True}
            error_message = str(exc)
            self.repository.complete_attempt(
                tenant_id=run.tenant_id,
                attempt_id=attempt.id,
                status=ATTEMPT_STATUS_FAILED,
                error_code=exc.__class__.__name__,
                error_message=error_message,
                actor=self.worker_id,
            )
            failed_run = self.repository.complete_run(
                tenant_id=run.tenant_id,
                run_id=run.id,
                status=RUN_STATUS_FAILED,
                result=attach_run_logs({}, captured.logs),
                failure_code=exc.__class__.__name__,
                failure_message=error_message,
                actor=self.worker_id,
            )
            return {"run": failed_run.to_dict() if failed_run else run.to_dict(), "attempt": attempt.to_dict(), "ok": False}
        current_run = self.repository.get_run(tenant_id=run.tenant_id, run_id=run.id)
        if current_run and current_run.status == RUN_STATUS_STOPPED:
            return {"run": current_run.to_dict(), "attempt": attempt.to_dict(), "result": result, "ok": False, "stopped": True}
        self.repository.complete_attempt(
            tenant_id=run.tenant_id,
            attempt_id=attempt.id,
            status=ATTEMPT_STATUS_SUCCEEDED,
            error_code="",
            error_message="",
            actor=self.worker_id,
        )
        succeeded_run = self.repository.complete_run(
            tenant_id=run.tenant_id,
            run_id=run.id,
            status=RUN_STATUS_SUCCEEDED,
            result=attach_run_logs(result if isinstance(result, dict) else {"value": result}, logs),
            failure_code="",
            failure_message="",
            actor=self.worker_id,
        )
        return {
            "run": succeeded_run.to_dict() if succeeded_run else run.to_dict(),
            "attempt": attempt.to_dict(),
            "result": result,
            "ok": True,
        }


def build_run_logs(stdout: str, stderr: str) -> dict[str, str]:
    logs: dict[str, str] = {}
    if stdout:
        logs["stdout"] = stdout
    if stderr:
        logs["stderr"] = stderr
    return logs


def attach_run_logs(result: dict[str, Any], logs: dict[str, str]) -> dict[str, Any]:
    if not logs:
        return result
    return {**result, "_logs": logs}
