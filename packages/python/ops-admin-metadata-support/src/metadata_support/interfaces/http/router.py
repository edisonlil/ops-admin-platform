from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from identity_access.interfaces.http import dependencies as auth
from metadata_support.application import services
from metadata_support.domain.exceptions import (
    MetadataSupportNotFoundError,
    MetadataSupportStorageNotReadyError,
    MetadataSupportValidationError,
)
from metadata_support.interfaces.http.dtos import (
    FieldDefinitionRequest,
    ResourceMetadataRequest,
    ResourceSearchRequest,
    ResourceTypeRequest,
    TagGroupRequest,
    TagRequest,
)
from system.interfaces.http import error_response, ok


router = APIRouter(prefix="/metadata")


@router.get("/resource-types")
def resource_types(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    status: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:resource-type:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_resource_types(page=page, page_size=page_size, keyword=keyword, status=status, current_user=current_user))


@router.post("/resource-types")
def create_resource_type(
    payload: ResourceTypeRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:resource-type:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_resource_type(payload.model_dump(), current_user))


@router.put("/resource-types/{resource_type_id}")
def update_resource_type(
    resource_type_id: int,
    payload: ResourceTypeRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:resource-type:manage")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = resource_type_id
    return ok_or_error(lambda: services.save_resource_type(data, current_user))


@router.get("/fields")
def field_definitions(
    resource_type_code: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    keyword: str = "",
    status: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:field:read")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_field_definitions(
            resource_type_code=resource_type_code,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            current_user=current_user,
        )
    )


@router.post("/fields")
def create_field_definition(
    payload: FieldDefinitionRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:field:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_field_definition(payload.model_dump(), current_user))


@router.put("/fields/{field_id}")
def update_field_definition(
    field_id: int,
    payload: FieldDefinitionRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:field:manage")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = field_id
    return ok_or_error(lambda: services.save_field_definition(data, current_user))


@router.get("/tag-groups")
def tag_groups(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    status: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:tag:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_tag_groups(page=page, page_size=page_size, keyword=keyword, status=status, current_user=current_user))


@router.post("/tag-groups")
def create_tag_group(
    payload: TagGroupRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:tag:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_tag_group(payload.model_dump(), current_user))


@router.put("/tag-groups/{group_id}")
def update_tag_group(
    group_id: int,
    payload: TagGroupRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:tag:manage")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = group_id
    return ok_or_error(lambda: services.save_tag_group(data, current_user))


@router.get("/tags")
def tags(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    keyword: str = "",
    group_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:tag:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_tags(page=page, page_size=page_size, keyword=keyword, group_id=group_id, status=status, current_user=current_user))


@router.post("/tags")
def create_tag(
    payload: TagRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:tag:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_tag(payload.model_dump(), current_user))


@router.put("/tags/{tag_id}")
def update_tag(
    tag_id: int,
    payload: TagRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:tag:manage")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = tag_id
    return ok_or_error(lambda: services.save_tag(data, current_user))


@router.get("/resources/{resource_type_code}/{resource_id}")
def resource_metadata(
    resource_type_code: str,
    resource_id: str,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:resource:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.get_resource_metadata(resource_type_code=resource_type_code, resource_id=resource_id, current_user=current_user))


@router.put("/resources/{resource_type_code}/{resource_id}")
def update_resource_metadata(
    resource_type_code: str,
    resource_id: str,
    payload: ResourceMetadataRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:resource:manage")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.bind_resource_metadata(
            tenant_id=services.current_tenant_id(current_user),
            resource_type_code=resource_type_code,
            resource_id=resource_id,
            metadata=payload.metadata,
            tag_codes=payload.tag_codes,
            actor=services.current_actor(current_user),
            actor_id=services.current_user_id_or_none(current_user),
        )
    )


@router.post("/resources/search")
def search_resources(
    payload: ResourceSearchRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("metadata:resource:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.search_resources(payload.model_dump(), current_user))


def ok_or_error(action: Any) -> dict[str, Any]:
    try:
        return ok(action())
    except MetadataSupportStorageNotReadyError as exc:
        return error_response(message=str(exc), code="METADATA_STORAGE_NOT_READY", status_code=503)
    except MetadataSupportNotFoundError as exc:
        return error_response(message=str(exc), code="METADATA_NOT_FOUND", status_code=404)
    except MetadataSupportValidationError as exc:
        return error_response(message=str(exc), code="METADATA_VALIDATION_ERROR", status_code=400)
