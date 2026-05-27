from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from datasets.application import services
from datasets.domain.exceptions import DatasetDomainError, DatasetNotFoundError, DatasetRuntimeUnavailableError, DatasetStorageNotReadyError
from datasets.interfaces.http.dtos import DatasetFieldsRequest, DatasetPreviewRequest, DatasetQueryExecuteRequest, DatasetRequest, DatasetRowsRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import error_response, ok


router = APIRouter(prefix="/datasets")


@router.get("")
def datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    status: str | None = Query(default=None),
    dataset_type: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:read")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_datasets(
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            dataset_type=dataset_type,
            sort_by=sort_by,
            sort_dir=sort_dir,
            current_user=current_user,
        )
    )


@router.post("")
def create_dataset(
    payload: DatasetRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_dataset(payload.model_dump(), current_user))


@router.get("/{dataset_id}")
def dataset_detail(
    dataset_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:read")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.dataset_detail(dataset_id, current_user))


@router.put("/{dataset_id}")
def update_dataset(
    dataset_id: int,
    payload: DatasetRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_dataset(payload.model_dump(), current_user, dataset_id=dataset_id))


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.delete_dataset(dataset_id, current_user))


@router.put("/{dataset_id}/fields")
def save_dataset_fields(
    dataset_id: int,
    payload: DatasetFieldsRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_fields(dataset_id, payload.model_dump(), current_user))


@router.put("/{dataset_id}/manual-rows")
def save_dataset_rows(
    dataset_id: int,
    payload: DatasetRowsRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_manual_rows(dataset_id, payload.model_dump(), current_user))


@router.post("/{dataset_id}/publish")
def publish_dataset(
    dataset_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:publish")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.publish_dataset(dataset_id, current_user))


@router.get("/{dataset_id}/preview")
def preview_dataset(
    dataset_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:preview")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.preview_dataset(
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
            current_user=current_user,
            apply_data_access=False,
        )
    )


@router.post("/{dataset_id}/runtime/preview")
def runtime_preview(
    dataset_id: int,
    payload: DatasetPreviewRequest,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(auth.require_business_api_key_or_permission("datasets:dataset:preview")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.preview_dataset(
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
            variables=payload.variables,
            current_user=current_user,
        )
    )


@router.post("/{dataset_id}/query/execute")
def execute_query(
    dataset_id: int,
    payload: DatasetQueryExecuteRequest,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:manage")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.preview_dataset(
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
            variables=payload.variables,
            query_config=payload.query_config,
            current_user=current_user,
            apply_data_access=False,
        )
    )


@router.get("/{dataset_id}/source-schema")
def source_schema(
    dataset_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("datasets:dataset:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.source_schema(dataset_id, current_user))


def ok_or_error(action: Any) -> dict[str, Any]:
    try:
        return ok(action())
    except DatasetStorageNotReadyError as exc:
        return error_response(message=str(exc), code="DATASET_STORAGE_NOT_READY", status_code=503)
    except DatasetNotFoundError as exc:
        return error_response(message=str(exc), code="DATASET_NOT_FOUND", status_code=404)
    except DatasetRuntimeUnavailableError as exc:
        return error_response(message=str(exc), code="DATASET_RUNTIME_UNAVAILABLE", status_code=503)
    except DatasetDomainError as exc:
        return error_response(message=str(exc), code="DATASET_VALIDATION_ERROR", status_code=400)
