from __future__ import annotations

import json
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from file_management.application import services
from file_management.interfaces.http.dtos import (
    FileMetadataRequest,
    FileFolderRequest,
    FileLibraryRequest,
    PreviewProfileRequest,
    StorageProfileRequest,
    TenantStorageQuotaRequest,
)
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import ok


router = APIRouter(prefix="/files")


@router.get("/libraries")
def libraries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(services.list_libraries(page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir, current_user=current_user))


@router.post("/libraries")
def create_library(
    payload: FileLibraryRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:library:manage")),
) -> dict[str, Any]:
    return ok(services.save_library(payload.model_dump(), current_user))


@router.put("/libraries/{library_id}")
def update_library(
    library_id: int,
    payload: FileLibraryRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:library:manage")),
) -> dict[str, Any]:
    return ok(services.save_library(payload.model_dump(), current_user, library_id=library_id))


@router.delete("/libraries/{library_id}")
def delete_library(
    library_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:library:manage")),
) -> dict[str, Any]:
    return ok(services.delete_library(library_id, current_user))


@router.get("/workspace")
def workspace(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    library_id: int | None = None,
    folder_id: int | None = None,
    keyword: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(
        services.list_workspace(
            current_user=current_user,
            page=page,
            page_size=page_size,
            library_id=library_id,
            folder_id=folder_id,
            keyword=keyword,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )


@router.get("/libraries/{library_id}/tree")
def library_tree(
    library_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(services.folder_tree(library_id=library_id, current_user=current_user))


@router.post("/folders")
def create_folder(
    payload: FileFolderRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:library:manage")),
) -> dict[str, Any]:
    return ok(services.save_folder(payload.model_dump(exclude_unset=True), current_user))


@router.put("/folders/{folder_id}")
def update_folder(
    folder_id: int,
    payload: FileFolderRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:library:manage")),
) -> dict[str, Any]:
    return ok(services.save_folder(payload.model_dump(exclude_unset=True), current_user, folder_id=folder_id))


@router.put("/folders/{folder_id}/metadata")
def update_folder_metadata(
    folder_id: int,
    payload: FileMetadataRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:library:manage")),
) -> dict[str, Any]:
    return ok(services.update_folder_metadata(folder_id, payload.model_dump(), current_user))


@router.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:library:manage")),
) -> dict[str, Any]:
    return ok(services.delete_folder(folder_id, current_user))


@router.get("")
def files(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    library_id: int | None = None,
    folder_id: int | None = None,
    current_folder_only: bool = False,
    keyword: str = "",
    mime_type: str = "",
    status_filter: str = Query(default="", alias="status"),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(
        services.list_files(
            page=page,
            page_size=page_size,
            current_user=current_user,
            library_id=library_id,
            folder_id=folder_id,
            current_folder_only=current_folder_only,
            keyword=keyword,
            mime_type=mime_type,
            status_filter=status_filter,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )


@router.get("/search")
def search_files(
    keyword: str = "",
    metadata: str | None = Query(default=None),
    tag_codes: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(
        services.search_files(
            page=page,
            page_size=page_size,
            keyword=keyword,
            metadata_filters=parse_metadata_filters(metadata),
            tag_codes=parse_string_list(tag_codes),
            current_user=current_user,
        )
    )


@router.get("/access-logs")
def access_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    file_id: int | None = None,
    action: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(
        services.list_access_logs(
            page=page,
            page_size=page_size,
            current_user=current_user,
            file_id=file_id,
            action=action,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )


@router.get("/index-jobs")
def index_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    file_id: int | None = None,
    status_filter: str = Query(default="", alias="status"),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(
        services.list_index_jobs(
            page=page,
            page_size=page_size,
            current_user=current_user,
            file_id=file_id,
            status_filter=status_filter,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )


@router.post("/upload")
def upload_file(
    upload: UploadFile = File(...),
    library_id: int | None = Form(default=None),
    folder_id: int | None = Form(default=None),
    visibility: str = Form(default="tenant"),
    metadata: str | None = Form(default=None),
    tag_codes: str | None = Form(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:upload")),
) -> dict[str, Any]:
    return ok(
        services.upload_file(
            current_user=current_user,
            filename=upload.filename or "upload.bin",
            content_type=upload.content_type or "application/octet-stream",
            stream=upload.file,
            library_id=library_id,
            folder_id=folder_id,
            visibility=visibility,
            metadata=parse_metadata_object(metadata),
            tag_codes=parse_string_list(tag_codes),
        )
    )


def parse_metadata_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metadata must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metadata must be a JSON object")
    return payload


def parse_metadata_filters(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metadata must be valid JSON") from exc
    if isinstance(payload, dict):
        return [{"field_key": key, "op": "eq", "value": item} for key, item in payload.items()]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metadata must be a JSON object or filter array")


def parse_string_list(value: str | None) -> list[str]:
    if not value:
        return []
    text = value.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tag_codes must be valid JSON") from exc
        if not isinstance(payload, list):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tag_codes must be a JSON array")
        return [str(item).strip() for item in payload if str(item).strip()]
    return [item.strip() for item in text.split(",") if item.strip()]


@router.get("/admin/tenants/{tenant_id}/quota")
def tenant_quota(
    tenant_id: int,
    _: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.quota_for_tenant(tenant_id))


@router.put("/admin/tenants/{tenant_id}/quota")
def update_tenant_quota(
    tenant_id: int,
    payload: TenantStorageQuotaRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.save_quota(tenant_id, payload.model_dump(), current_user))


@router.get("/admin/storage-profiles")
def storage_profiles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    _: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.list_storage_profiles(page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir))


@router.get("/admin/storage-provider-options")
def storage_provider_options(
    _: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.storage_provider_options())


@router.get("/admin/preview-profiles")
def preview_profiles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    _: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.list_preview_profiles(page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir))


@router.get("/admin/preview-provider-options")
def preview_provider_options(
    _: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.preview_provider_options())


@router.post("/admin/preview-profiles")
def create_preview_profile(
    payload: PreviewProfileRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.save_preview_profile(payload.model_dump(), current_user))


@router.put("/admin/preview-profiles/{profile_id}")
def update_preview_profile(
    profile_id: int,
    payload: PreviewProfileRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.save_preview_profile(payload.model_dump(), current_user, profile_id=profile_id))


@router.post("/admin/preview-profiles/{profile_id}/default")
def set_default_preview_profile(
    profile_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.set_default_preview_profile(profile_id, current_user))


@router.post("/admin/storage-profiles")
def create_storage_profile(
    payload: StorageProfileRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.save_storage_profile(payload.model_dump(), current_user))


@router.put("/admin/storage-profiles/{profile_id}")
def update_storage_profile(
    profile_id: int,
    payload: StorageProfileRequest,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.save_storage_profile(payload.model_dump(), current_user, profile_id=profile_id))


@router.post("/admin/storage-profiles/{profile_id}/test")
def test_storage_profile(
    profile_id: int,
    _: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.test_storage_profile(profile_id))


@router.post("/admin/storage-profiles/{profile_id}/default")
def set_default_storage_profile(
    profile_id: int,
    current_user: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.set_default_storage_profile(profile_id, current_user))


@router.get("/{file_id}/preview-metadata")
def file_preview_metadata(
    file_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(services.get_file_preview_metadata(file_id, current_user))


@router.get("/{file_id}/preview")
def preview_file(
    request: Request,
    file_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> StreamingResponse:
    item, download, preview = services.preview_file(
        file_id,
        current_user,
        client_ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    filename = urllib.parse.quote(item.original_name)
    mime_type = str(preview.get("mime_type") or download.content_type or item.mime_type)
    return StreamingResponse(
        download.stream,
        media_type=mime_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{filename}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{file_id}/preview-source")
def preview_source_file(
    file_id: int,
    expires: int = Query(...),
    signature: str = Query(...),
) -> StreamingResponse:
    item, download = services.preview_source_file(file_id, expires=expires, signature=signature)
    filename = urllib.parse.quote(item.original_name)
    return StreamingResponse(
        download.stream,
        media_type=download.content_type or item.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{file_id}/download")
def download_file(
    request: Request,
    file_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> StreamingResponse:
    item, download = services.download_file(
        file_id,
        current_user,
        client_ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    filename = urllib.parse.quote(item.original_name)
    return StreamingResponse(
        download.stream,
        media_type=download.content_type or item.mime_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/{file_id}/reindex")
def reindex_file(
    file_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:upload")),
) -> dict[str, Any]:
    return ok(services.reindex_file(file_id, current_user))


@router.put("/{file_id}/metadata")
def update_file_metadata(
    file_id: int,
    payload: FileMetadataRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:upload")),
) -> dict[str, Any]:
    return ok(services.update_file_metadata(file_id, payload.model_dump(), current_user))


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:delete")),
) -> dict[str, Any]:
    return ok(services.delete_file(file_id, current_user))


@router.get("/{file_id}")
def file_detail(
    file_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(services.get_file(file_id, current_user))
