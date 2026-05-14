from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from identity_access.interfaces.http import dependencies as auth
from organization.application import services
from organization.domain.exceptions import OrganizationDomainError, OrganizationNotFoundError, OrganizationStorageNotReadyError
from organization.interfaces.http.dtos import DepartmentRequest, UserDepartmentsRequest
from system.interfaces.http import error_response, ok


router = APIRouter(prefix="/organization")


@router.get("/departments")
def departments(
    include_disabled: bool = Query(default=False),
    current_user: dict[str, Any] = Depends(auth.require_permission("organization:departments:read")),
) -> dict[str, Any]:
    tenant_id = services.current_tenant_id(current_user)
    return ok_or_error(lambda: services.list_departments(tenant_id=tenant_id, include_disabled=include_disabled))


@router.post("/departments")
def create_department(
    payload: DepartmentRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("organization:departments:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_department(payload.model_dump(), current_user))


@router.put("/departments/{department_id}")
def update_department(
    department_id: int,
    payload: DepartmentRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("organization:departments:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_department(payload.model_dump(), current_user, department_id=department_id))


@router.delete("/departments/{department_id}")
def delete_department(
    department_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("organization:departments:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.delete_department(department_id=department_id, current_user=current_user))


@router.get("/users/{user_id}/departments")
def user_departments(
    user_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("organization:departments:read")),
) -> dict[str, Any]:
    tenant_id = services.current_tenant_id(current_user)
    return ok_or_error(lambda: {"items": services.user_departments(tenant_id=tenant_id, user_id=user_id)})


@router.put("/users/{user_id}/departments")
def update_user_departments(
    user_id: int,
    payload: UserDepartmentsRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("organization:departments:manage")),
) -> dict[str, Any]:
    tenant_id = services.current_tenant_id(current_user)
    return ok_or_error(
        lambda: {
            "items": services.set_user_departments(
                tenant_id=tenant_id,
                user_id=user_id,
                department_ids=payload.department_ids,
                primary_department_id=payload.primary_department_id,
                current_user=current_user,
            )
        }
    )


def ok_or_error(action: Any) -> dict[str, Any]:
    try:
        return ok(action())
    except OrganizationStorageNotReadyError as exc:
        return error_response(message=str(exc), code="ORGANIZATION_STORAGE_NOT_READY", status_code=503)
    except OrganizationNotFoundError as exc:
        return error_response(message=str(exc), code="ORGANIZATION_NOT_FOUND", status_code=404)
    except OrganizationDomainError as exc:
        return error_response(message=str(exc), code="ORGANIZATION_VALIDATION_ERROR", status_code=400)
