from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from authorization.application import services
from authorization.domain.exceptions import AuthorizationDomainError, AuthorizationNotFoundError, AuthorizationStorageNotReadyError
from authorization.interfaces.http.dtos import DataAccessPolicyRequest, ResourceDescriptorRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import error_response, ok


router = APIRouter(prefix="/authorization")


@router.get("/resources")
def resources(
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    _: dict[str, Any] = Depends(auth.require_permission("authorization:data-scope:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_resource_descriptors(sort_by=sort_by, sort_dir=sort_dir))


@router.put("/resources/{resource_key}")
def upsert_resource(
    resource_key: str,
    payload: ResourceDescriptorRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("authorization:data-resource:manage")),
) -> dict[str, Any]:
    body = payload.model_dump()
    body["resource_key"] = resource_key
    return ok_or_error(lambda: services.save_resource_descriptor(body, current_user))


@router.get("/data-access-policies")
def data_access_policies(
    subject_type: str | None = Query(default=None),
    subject_id: int | None = Query(default=None, ge=1),
    resource_key: str | None = Query(default=None),
    tenant_id: int | None = Query(default=None, ge=1),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("authorization:data-scope:read")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_data_access_policies(
            current_user,
            subject_type=subject_type,
            subject_id=subject_id,
            resource_key=resource_key,
            tenant_id=tenant_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )


@router.post("/data-access-policies")
def save_data_access_policy(
    payload: DataAccessPolicyRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("authorization:data-scope:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_data_access_policy(payload.model_dump(), current_user))


@router.delete("/data-access-policies/{policy_id}")
def delete_data_access_policy(
    policy_id: int,
    tenant_id: int | None = Query(default=None, ge=1),
    current_user: dict[str, Any] = Depends(auth.require_permission("authorization:data-scope:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.delete_data_access_policy(policy_id, current_user, tenant_id=tenant_id))


def ok_or_error(action: Any) -> dict[str, Any]:
    try:
        return ok(action())
    except AuthorizationStorageNotReadyError as exc:
        return error_response(message=str(exc), code="AUTHORIZATION_STORAGE_NOT_READY", status_code=503)
    except AuthorizationNotFoundError as exc:
        return error_response(message=str(exc), code="AUTHORIZATION_NOT_FOUND", status_code=404)
    except AuthorizationDomainError as exc:
        return error_response(message=str(exc), code="AUTHORIZATION_VALIDATION_ERROR", status_code=400)
