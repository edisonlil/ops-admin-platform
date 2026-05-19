from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from cron.application import services
from cron.domain.exceptions import CronDomainError, CronNotFoundError, CronStorageNotReadyError
from cron.interfaces.http.dtos import CronTaskRequest, CronTriggerRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import error_response, ok


router = APIRouter(prefix="/cron")


@router.get("/tasks")
def tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:tasks:view")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_tasks(page=page, page_size=page_size, status=status, sort_by=sort_by, sort_dir=sort_dir, current_user=current_user))


@router.post("/tasks")
def create_task(
    payload: CronTaskRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:tasks:create")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_task(payload.model_dump(), current_user))


@router.get("/tasks/{task_id}")
def task_detail(
    task_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:tasks:view")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.get_task(task_id=task_id, current_user=current_user))


@router.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    payload: CronTaskRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:tasks:update")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = task_id
    return ok_or_error(lambda: services.save_task(data, current_user))


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:tasks:delete")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.delete_task(task_id=task_id, current_user=current_user))


@router.post("/tasks/{task_id}/enable")
def enable_task(
    task_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:tasks:enable")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.enable_task(task_id, current_user))


@router.post("/tasks/{task_id}/disable")
def disable_task(
    task_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:tasks:disable")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.disable_task(task_id, current_user))


@router.post("/tasks/{task_id}/trigger")
def trigger_task(
    task_id: int,
    payload: CronTriggerRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:tasks:trigger")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.trigger_task(task_id=task_id, payload=payload.model_dump(), current_user=current_user))


@router.get("/tasks/{task_id}/runs")
def task_runs(
    task_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:runs:view")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_runs(task_id=task_id, page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir, current_user=current_user))


@router.get("/runs")
def runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:runs:view")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_runs(task_id=None, page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir, current_user=current_user))


@router.get("/runs/{run_id}")
def run_detail(
    run_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("cron:runs:view")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.get_run(run_id=run_id, current_user=current_user))


def ok_or_error(action: Any) -> dict[str, Any]:
    try:
        return ok(action())
    except CronStorageNotReadyError as exc:
        return error_response(message=str(exc), code="CRON_STORAGE_NOT_READY", status_code=503)
    except CronNotFoundError as exc:
        return error_response(message=str(exc), code="CRON_NOT_FOUND", status_code=404)
    except CronDomainError as exc:
        return error_response(message=str(exc), code="CRON_VALIDATION_ERROR", status_code=400)
