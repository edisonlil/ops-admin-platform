from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cron.domain.exceptions import CronDomainError


TASK_STATUS_DRAFT = "draft"
TASK_STATUS_ENABLED = "enabled"
TASK_STATUS_DISABLED = "disabled"
TASK_STATUSES = {TASK_STATUS_DRAFT, TASK_STATUS_ENABLED, TASK_STATUS_DISABLED}

TRIGGER_TYPE_CRON = "cron"
TRIGGER_TYPE_INTERVAL = "interval"
TRIGGER_TYPE_DATE = "date"
TRIGGER_TYPES = {TRIGGER_TYPE_CRON, TRIGGER_TYPE_INTERVAL, TRIGGER_TYPE_DATE}

MISFIRE_SKIP = "skip"
MISFIRE_CATCH_UP_ONCE = "catch_up_once"
MISFIRE_CATCH_UP_ALL = "catch_up_all"
MISFIRE_POLICIES = {MISFIRE_SKIP, MISFIRE_CATCH_UP_ONCE, MISFIRE_CATCH_UP_ALL}

CONCURRENCY_ALLOW = "allow"
CONCURRENCY_FORBID = "forbid"
CONCURRENCY_REPLACE = "replace"
CONCURRENCY_QUEUE = "queue"
CONCURRENCY_POLICIES = {CONCURRENCY_ALLOW, CONCURRENCY_FORBID, CONCURRENCY_REPLACE, CONCURRENCY_QUEUE}

RUN_STATUS_PENDING = "pending"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_SUCCEEDED = "succeeded"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_SKIPPED = "skipped"

ATTEMPT_STATUS_RUNNING = "running"
ATTEMPT_STATUS_SUCCEEDED = "succeeded"
ATTEMPT_STATUS_FAILED = "failed"

BINDING_STATUS_ACTIVE = "active"
BINDING_STATUS_PAUSED = "paused"
BINDING_STATUS_DELETED = "deleted"


@dataclass(frozen=True)
class TriggerSpec:
    trigger_type: str
    expression: str
    timezone: str = "UTC"
    payload: dict[str, Any] | None = None

    def validate(self) -> None:
        if self.trigger_type not in TRIGGER_TYPES:
            raise CronDomainError(f"unsupported trigger_type: {self.trigger_type}")
        if not self.expression.strip():
            raise CronDomainError("trigger expression is required")
        if not self.timezone.strip():
            raise CronDomainError("timezone is required")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    delay_seconds: int = 0
    backoff_multiplier: float = 1.0

    def validate(self) -> None:
        if self.max_attempts < 1:
            raise CronDomainError("retry max_attempts must be at least 1")
        if self.delay_seconds < 0:
            raise CronDomainError("retry delay_seconds cannot be negative")
        if self.backoff_multiplier < 1:
            raise CronDomainError("retry backoff_multiplier must be at least 1")


@dataclass(frozen=True)
class CronTask:
    id: int
    tenant_id: int
    task_key: str
    name: str
    description: str
    status: str
    execution_target: str
    payload_schema_version: int
    default_payload: dict[str, Any]
    concurrency_policy: str
    timeout_seconds: int
    max_attempts: int
    retry_delay_seconds: int
    retry_backoff_multiplier: float
    misfire_policy: str
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.tenant_id <= 0:
            raise CronDomainError("tenant_id must be positive")
        if not self.task_key.strip():
            raise CronDomainError("task_key is required")
        if not self.name.strip():
            raise CronDomainError("name is required")
        if self.status not in TASK_STATUSES:
            raise CronDomainError(f"unsupported task status: {self.status}")
        if not self.execution_target.strip():
            raise CronDomainError("execution_target is required")
        if self.payload_schema_version < 1:
            raise CronDomainError("payload_schema_version must be positive")
        if self.concurrency_policy not in CONCURRENCY_POLICIES:
            raise CronDomainError(f"unsupported concurrency_policy: {self.concurrency_policy}")
        if self.timeout_seconds < 1:
            raise CronDomainError("timeout_seconds must be positive")
        RetryPolicy(
            max_attempts=self.max_attempts,
            delay_seconds=self.retry_delay_seconds,
            backoff_multiplier=self.retry_backoff_multiplier,
        ).validate()
        if self.misfire_policy not in MISFIRE_POLICIES:
            raise CronDomainError(f"unsupported misfire_policy: {self.misfire_policy}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "task_key": self.task_key,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "execution_target": self.execution_target,
            "payload_schema_version": self.payload_schema_version,
            "default_payload": self.default_payload,
            "concurrency_policy": self.concurrency_policy,
            "timeout_seconds": self.timeout_seconds,
            "max_attempts": self.max_attempts,
            "retry_delay_seconds": self.retry_delay_seconds,
            "retry_backoff_multiplier": self.retry_backoff_multiplier,
            "misfire_policy": self.misfire_policy,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class CronSchedule:
    id: int
    tenant_id: int
    task_id: int
    trigger_type: str
    trigger_expression: str
    timezone: str
    start_time: str | None
    end_time: str | None
    next_fire_time: str | None
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.task_id <= 0:
            raise CronDomainError("task_id must be positive")
        TriggerSpec(self.trigger_type, self.trigger_expression, self.timezone).validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "trigger_type": self.trigger_type,
            "trigger_expression": self.trigger_expression,
            "timezone": self.timezone,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "next_fire_time": self.next_fire_time,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class CronTaskDetail:
    task: CronTask
    schedule: CronSchedule | None

    def to_dict(self) -> dict[str, Any]:
        data = self.task.to_dict()
        data["schedule"] = self.schedule.to_dict() if self.schedule else None
        return data


@dataclass(frozen=True)
class CronRun:
    id: int
    tenant_id: int
    task_id: int
    schedule_id: int | None
    fire_time: str
    status: str
    trigger_source: str
    idempotency_key: str
    payload: dict[str, Any]
    result: dict[str, Any]
    started_time: str | None
    finished_time: str | None
    failure_code: str
    failure_message: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "schedule_id": self.schedule_id,
            "fire_time": self.fire_time,
            "status": self.status,
            "trigger_source": self.trigger_source,
            "idempotency_key": self.idempotency_key,
            "payload": self.payload,
            "result": self.result,
            "started_time": self.started_time,
            "finished_time": self.finished_time,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class CronAttempt:
    id: int
    tenant_id: int
    run_id: int
    attempt_number: int
    status: str
    worker_id: str
    started_time: str
    finished_time: str | None
    error_code: str
    error_message: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "run_id": self.run_id,
            "attempt_number": self.attempt_number,
            "status": self.status,
            "worker_id": self.worker_id,
            "started_time": self.started_time,
            "finished_time": self.finished_time,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class ExternalScheduleBinding:
    id: int
    tenant_id: int
    task_id: int
    scheduler_type: str
    external_id: str
    status: str
    metadata: dict[str, Any]
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "scheduler_type": self.scheduler_type,
            "external_id": self.external_id,
            "status": self.status,
            "metadata": self.metadata,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
