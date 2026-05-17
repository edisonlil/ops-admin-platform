from __future__ import annotations

from typing import Any
from uuid import uuid4

from cron.application.executor import CronTaskExecutor
from cron.application.ports import CronRepository, NoopTaskDispatcher, TaskDispatcher
from cron.domain.exceptions import CronDomainError, CronNotFoundError, CronStorageNotReadyError
from cron.domain.models import TASK_STATUS_DISABLED, TASK_STATUS_ENABLED, CronSchedule, CronTask
from system.application.data_access import (
    ResourceDescriptor,
    current_user_primary_department_id,
    resolve_data_access_filter,
)


repository: CronRepository | None = None
dispatcher: TaskDispatcher = NoopTaskDispatcher()
CRON_TASK_RESOURCE = ResourceDescriptor(resource_key="cron.task")


def configure_repository(cron_repository: CronRepository) -> None:
    global repository
    repository = cron_repository


def configure_dispatcher(task_dispatcher: TaskDispatcher) -> None:
    global dispatcher
    dispatcher = task_dispatcher


def repo() -> CronRepository:
    if repository is None:
        raise CronStorageNotReadyError("cron repository is not configured")
    return repository


def list_tasks(*, page: int, page_size: int, status: str | None, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        items, total = repo().list_tasks(
            tenant_id=current_tenant_id(current_user),
            page=page,
            page_size=page_size,
            status=status,
            data_scope=resolve_data_access_filter(current_user=current_user, resource=CRON_TASK_RESOURCE, action="read"),
        )
    except RuntimeError as exc:
        raise CronStorageNotReadyError(str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def get_task(*, task_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        detail = repo().get_task_detail(tenant_id=current_tenant_id(current_user), task_id=task_id)
    except RuntimeError as exc:
        raise CronStorageNotReadyError(str(exc)) from exc
    if not detail:
        raise CronNotFoundError("cron task not found")
    return {"item": detail.to_dict()}


def save_task(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    actor = current_actor(current_user)
    actor_id = current_user_id_or_none(current_user)
    payload = {
        **payload,
        "owner_user_id": actor_id,
        "owner_department_id": current_user_primary_department_id(current_user),
    }
    task_id = int(payload.get("id") or 0)
    if task_id:
        try:
            existing = repo().get_task_detail(tenant_id=tenant_id, task_id=task_id)
        except RuntimeError as exc:
            raise CronStorageNotReadyError(str(exc)) from exc
        if not existing:
            raise CronNotFoundError("cron task not found")
        if existing.task.status == TASK_STATUS_ENABLED:
            raise CronDomainError("enabled cron tasks cannot be edited; disable the task first")
    task = build_task_for_validation(tenant_id=tenant_id, payload=payload)
    task.validate()
    schedule_payload = payload.get("schedule") if isinstance(payload.get("schedule"), dict) else None
    if schedule_payload:
        schedule = build_schedule_for_validation(tenant_id=tenant_id, payload=schedule_payload)
        schedule.validate()
    try:
        detail = repo().save_task(tenant_id=tenant_id, payload=payload, actor=actor, actor_id=actor_id)
    except RuntimeError as exc:
        raise CronStorageNotReadyError(str(exc)) from exc
    return {"item": detail.to_dict()}


def set_task_status(*, task_id: int, next_status: str, current_user: dict[str, Any]) -> dict[str, Any]:
    actor = current_actor(current_user)
    actor_id = current_user_id_or_none(current_user)
    try:
        detail = repo().set_task_status(
            tenant_id=current_tenant_id(current_user),
            task_id=task_id,
            status=next_status,
            actor=actor,
            actor_id=actor_id,
        )
    except RuntimeError as exc:
        raise CronStorageNotReadyError(str(exc)) from exc
    if not detail:
        raise CronNotFoundError("cron task not found")
    return {"item": detail.to_dict()}


def delete_task(*, task_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    actor = current_actor(current_user)
    actor_id = current_user_id_or_none(current_user)
    try:
        detail = repo().delete_task(
            tenant_id=current_tenant_id(current_user),
            task_id=task_id,
            actor=actor,
            actor_id=actor_id,
        )
    except RuntimeError as exc:
        raise CronStorageNotReadyError(str(exc)) from exc
    if not detail:
        raise CronNotFoundError("cron task not found")
    return {"item": detail.to_dict()}


def trigger_task(*, task_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    idempotency_key = str(payload.get("idempotency_key") or "").strip() or f"manual:{uuid4().hex}"
    run_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    try:
        task_detail = repo().get_task_detail(tenant_id=tenant_id, task_id=task_id)
        if not task_detail:
            raise CronNotFoundError("cron task not found")
        merged_payload = {**task_detail.task.default_payload, **run_payload}
        run = repo().create_manual_run(
            tenant_id=tenant_id,
            task_id=task_id,
            payload=merged_payload,
            idempotency_key=idempotency_key,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
        result = CronTaskExecutor(
            repository=repo(),
            dispatcher=dispatcher,
            worker_id="api-manual-trigger",
        ).execute_manual_run(task_detail, run)
    except RuntimeError as exc:
        raise CronStorageNotReadyError(str(exc)) from exc
    return {"item": result["run"], "attempt": result.get("attempt"), "ok": bool(result.get("ok", False))}


def list_runs(
    *,
    task_id: int | None,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    try:
        items, total = repo().list_runs(
            tenant_id=current_tenant_id(current_user),
            task_id=task_id,
            page=page,
            page_size=page_size,
        )
    except RuntimeError as exc:
        raise CronStorageNotReadyError(str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def get_run(*, run_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        run = repo().get_run(tenant_id=tenant_id, run_id=run_id)
        if not run:
            raise CronNotFoundError("cron run not found")
        attempts = repo().list_attempts(tenant_id=tenant_id, run_id=run_id)
    except RuntimeError as exc:
        raise CronStorageNotReadyError(str(exc)) from exc
    return {"item": run.to_dict(), "attempts": [item.to_dict() for item in attempts]}


def build_task_for_validation(*, tenant_id: int, payload: dict[str, Any]) -> CronTask:
    return CronTask(
        id=int(payload.get("id") or 0),
        tenant_id=tenant_id,
        task_key=str(payload.get("task_key") or "").strip(),
        name=str(payload.get("name") or "").strip(),
        description=str(payload.get("description") or "").strip(),
        status=str(payload.get("status") or "draft").strip() or "draft",
        execution_target=str(payload.get("execution_target") or "").strip(),
        payload_schema_version=int(payload.get("payload_schema_version") or 1),
        default_payload=payload.get("default_payload") if isinstance(payload.get("default_payload"), dict) else {},
        concurrency_policy=str(payload.get("concurrency_policy") or "forbid").strip() or "forbid",
        timeout_seconds=int(payload.get("timeout_seconds") or 300),
        max_attempts=int(payload.get("max_attempts") or 1),
        retry_delay_seconds=int(payload.get("retry_delay_seconds") or 0),
        retry_backoff_multiplier=float(payload.get("retry_backoff_multiplier") or 1),
        misfire_policy=str(payload.get("misfire_policy") or "skip").strip() or "skip",
        create_time="",
        update_time="",
    )


def build_schedule_for_validation(*, tenant_id: int, payload: dict[str, Any]) -> CronSchedule:
    return CronSchedule(
        id=int(payload.get("id") or 0),
        tenant_id=tenant_id,
        task_id=1,
        trigger_type=str(payload.get("trigger_type") or "cron").strip() or "cron",
        trigger_expression=str(payload.get("trigger_expression") or "").strip(),
        timezone=str(payload.get("timezone") or "UTC").strip() or "UTC",
        start_time=str(payload["start_time"]) if payload.get("start_time") is not None else None,
        end_time=str(payload["end_time"]) if payload.get("end_time") is not None else None,
        next_fire_time=str(payload["next_fire_time"]) if payload.get("next_fire_time") is not None else None,
        create_time="",
        update_time="",
    )


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current_tenant = current_user.get("current_tenant") or {}
    tenant_id = current_tenant.get("id") or current_user.get("tenant_id") or 1
    return int(tenant_id)


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None


def enable_task(task_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    return set_task_status(task_id=task_id, next_status=TASK_STATUS_ENABLED, current_user=current_user)


def disable_task(task_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    return set_task_status(task_id=task_id, next_status=TASK_STATUS_DISABLED, current_user=current_user)
