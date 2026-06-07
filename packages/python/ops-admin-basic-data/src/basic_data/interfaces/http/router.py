from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from basic_data.application import services
from basic_data.domain.exceptions import BasicDataDomainError, BasicDataNotFoundError, BasicDataStorageNotReadyError
from basic_data.interfaces.http.dtos import DictionaryItemRequest, DictionaryTypeRequest, RegionRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import error_response, ok


router = APIRouter(prefix="/basic-data")


@router.get("/dictionary-types")
def dictionary_types(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    status: str | None = Query(default=None),
    category: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:read")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_dictionary_types(
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            category=category,
            sort_by=sort_by,
            sort_dir=sort_dir,
            current_user=current_user,
        )
    )


@router.post("/dictionary-types")
def create_dictionary_type(
    payload: DictionaryTypeRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_dictionary_type(payload.model_dump(), current_user))


@router.put("/dictionary-types/{type_id}")
def update_dictionary_type(
    type_id: int,
    payload: DictionaryTypeRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:manage")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = type_id
    return ok_or_error(lambda: services.save_dictionary_type(data, current_user))


@router.delete("/dictionary-types/{type_id}")
def delete_dictionary_type(
    type_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.delete_dictionary_type(type_id=type_id, current_user=current_user))


@router.get("/dictionary-types/{type_id}/items")
def dictionary_items(
    type_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    code: str = Query(default=""),
    value: str = Query(default=""),
    status: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:read")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_dictionary_items(
            type_id=type_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            code=code,
            value=value,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            current_user=current_user,
        )
    )


@router.post("/dictionary-types/{type_id}/items")
def create_dictionary_item(
    type_id: int,
    payload: DictionaryItemRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_dictionary_item(type_id, payload.model_dump(), current_user))


@router.get("/dictionary-types/{type_id}/items/export")
def export_dictionary_items(
    type_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:export")),
) -> StreamingResponse:
    stream, filename = services.export_dictionary_items(type_id=type_id, current_user=current_user)
    return StreamingResponse(
        stream,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/dictionary-types/{type_id}/items/import-template")
def dictionary_item_import_template(
    type_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:import")),
) -> StreamingResponse:
    stream, filename = services.dictionary_item_import_template(type_id=type_id, current_user=current_user)
    return StreamingResponse(
        stream,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/dictionary-types/{type_id}/items/import")
async def import_dictionary_items(
    type_id: int,
    upload: UploadFile = File(...),
    dry_run: bool = Query(default=True),
    mode: str = Query(default="upsert"),
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:import")),
) -> dict[str, Any]:
    content = await upload.read()
    return ok_or_error(
        lambda: services.import_dictionary_items(
            type_id=type_id,
            content=content,
            filename=upload.filename or "dictionary-items.csv",
            dry_run=dry_run,
            mode=mode,
            current_user=current_user,
        )
    )


@router.put("/dictionary-items/{item_id}")
def update_dictionary_item(
    item_id: int,
    payload: DictionaryItemRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.update_dictionary_item(item_id, payload.model_dump(), current_user))


@router.delete("/dictionary-items/{item_id}")
def delete_dictionary_item(
    item_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.delete_dictionary_item(item_id=item_id, current_user=current_user))


@router.get("/dictionaries/{type_code}/items")
def dictionary_items_by_code(
    type_code: str,
    active_only: bool = True,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_items_by_type_code(type_code=type_code, active_only=active_only, current_user=current_user))


@router.get("/regions")
def regions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    keyword: str = "",
    status: str | None = Query(default=None),
    level: str | None = Query(default=None),
    parent_id: int | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:read")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_regions(
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            level=level,
            parent_id=parent_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
            current_user=current_user,
        )
    )


@router.get("/regions/tree")
def region_tree(
    include_disabled: bool = False,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_region_tree(include_disabled=include_disabled, current_user=current_user))


@router.get("/regions/children")
def root_region_children(
    active_only: bool = True,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_region_children(parent_id=None, active_only=active_only, current_user=current_user))


@router.get("/regions/{region_id}/children")
def region_children(
    region_id: int,
    active_only: bool = True,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_region_children(parent_id=region_id, active_only=active_only, current_user=current_user))


@router.get("/region-options")
def region_options(
    parent_id: int | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_region_options(parent_id=parent_id, current_user=current_user))


@router.post("/regions")
def create_region(
    payload: RegionRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_region(payload.model_dump(), current_user))


@router.put("/regions/{region_id}")
def update_region(
    region_id: int,
    payload: RegionRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:manage")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = region_id
    return ok_or_error(lambda: services.save_region(data, current_user))


@router.delete("/regions/{region_id}")
def delete_region(
    region_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.delete_region(region_id=region_id, current_user=current_user))


@router.post("/regions/import")
async def import_regions(
    upload: UploadFile = File(...),
    dry_run: bool = Query(default=True),
    mode: str = Query(default="upsert"),
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:region:import")),
) -> dict[str, Any]:
    content = await upload.read()
    return ok_or_error(lambda: services.import_regions(content=content, filename=upload.filename or "regions.csv", dry_run=dry_run, mode=mode, current_user=current_user))


def ok_or_error(action: Any) -> dict[str, Any]:
    try:
        return ok(action())
    except BasicDataStorageNotReadyError as exc:
        return error_response(message=str(exc), code="BASIC_DATA_STORAGE_NOT_READY", status_code=503)
    except BasicDataNotFoundError as exc:
        return error_response(message=str(exc), code="BASIC_DATA_NOT_FOUND", status_code=404)
    except BasicDataDomainError as exc:
        return error_response(message=str(exc), code="BASIC_DATA_VALIDATION_ERROR", status_code=400)
