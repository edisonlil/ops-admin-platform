from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from basic_data.application import services
from basic_data.domain.exceptions import BasicDataDomainError, BasicDataNotFoundError, BasicDataStorageNotReadyError
from basic_data.interfaces.http.dtos import DictionaryItemRequest, DictionaryTypeRequest
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
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:read")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_dictionary_types(
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            category=category,
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
    status: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("basic-data:dictionary:read")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_dictionary_items(
            type_id=type_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
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


def ok_or_error(action: Any) -> dict[str, Any]:
    try:
        return ok(action())
    except BasicDataStorageNotReadyError as exc:
        return error_response(message=str(exc), code="BASIC_DATA_STORAGE_NOT_READY", status_code=503)
    except BasicDataNotFoundError as exc:
        return error_response(message=str(exc), code="BASIC_DATA_NOT_FOUND", status_code=404)
    except BasicDataDomainError as exc:
        return error_response(message=str(exc), code="BASIC_DATA_VALIDATION_ERROR", status_code=400)
