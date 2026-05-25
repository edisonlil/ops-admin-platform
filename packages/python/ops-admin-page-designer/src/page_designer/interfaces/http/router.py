from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, Query

from identity_access.interfaces.http import dependencies as auth
from page_designer.application import services
from page_designer.domain.exceptions import PageDesignerDomainError, PageDesignerNotFoundError, PageDesignerStorageNotReadyError
from page_designer.interfaces.http.dtos import PageDraftRequest, PageMenuMountRequest, PageRequest
from system.interfaces.http import error_response, ok


router = APIRouter(prefix="/page-designer")


@router.get("/pages")
def pages(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(
        lambda: services.list_pages(
            page=page,
            page_size=page_size,
            keyword=keyword,
            page_type=type,
            status=status,
            current_user=current_user,
        )
    )


@router.get("/menu-mount/directories")
def mount_directories(
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.list_mount_directories(current_user))


@router.post("/pages")
def create_page(
    payload: PageRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.create_page(payload.model_dump(), current_user))


@router.get("/pages/{page_id}")
def page_detail(
    page_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.get_page(page_id, current_user))


@router.put("/pages/{page_id}")
def update_page(
    page_id: int,
    payload: PageRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.update_page(page_id, payload.model_dump(), current_user))


@router.delete("/pages/{page_id}")
def delete_page(
    page_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.delete_page(page_id, current_user))


@router.put("/pages/{page_id}/draft")
def save_draft(
    page_id: int,
    payload: PageDraftRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.save_draft(page_id, payload.model_dump(), current_user))


@router.post("/pages/{page_id}/preview")
def preview_page(
    page_id: int,
    payload: PageDraftRequest | None = None,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.preview_page(page_id, payload.model_dump() if payload else None, current_user))


@router.post("/pages/{page_id}/publish")
def publish_page(
    page_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.publish_page(page_id, current_user))


@router.post("/pages/{page_id}/unpublish")
def unpublish_page(
    page_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.unpublish_page(page_id, current_user))


@router.post("/pages/{page_id}/menu-mount")
def mount_menu(
    page_id: int,
    payload: PageMenuMountRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.mount_menu(page_id, payload.model_dump(exclude_none=True), current_user))


@router.delete("/pages/{page_id}/menu-mount")
def unmount_menu(
    page_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_permission("page_designer:page:manage")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.unmount_menu(page_id, current_user))


@router.get("/runtime/{page_key}")
def runtime_page(
    page_key: str,
    current_user: dict[str, Any] = Depends(auth.require_permission("page_designer:page:view")),
) -> dict[str, Any]:
    return ok_or_error(lambda: services.runtime_page(page_key, current_user))


def ok_or_error(action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return ok(action())
    except PageDesignerStorageNotReadyError as exc:
        return error_response(message=str(exc), code="PAGE_DESIGNER_STORAGE_NOT_READY", status_code=503)
    except PageDesignerNotFoundError as exc:
        return error_response(message=str(exc), code="PAGE_DESIGNER_NOT_FOUND", status_code=404)
    except PageDesignerDomainError as exc:
        return error_response(message=str(exc), code="PAGE_DESIGNER_VALIDATION_ERROR", status_code=400)
