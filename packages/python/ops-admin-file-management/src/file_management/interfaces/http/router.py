from __future__ import annotations

import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from file_management.application import services
from file_management.interfaces.http.dtos import FileFolderRequest, FileLibraryRequest, StorageProfileRequest, TenantStorageQuotaRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import ok


router = APIRouter(prefix="/files")


@router.get("/libraries")
def libraries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(services.list_libraries(page=page, page_size=page_size, current_user=current_user))


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
    library_id: int | None = None,
    folder_id: int | None = None,
    keyword: str = "",
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(services.list_workspace(current_user=current_user, library_id=library_id, folder_id=folder_id, keyword=keyword))


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
    return ok(services.save_folder(payload.model_dump(), current_user))


@router.put("/folders/{folder_id}")
def update_folder(
    folder_id: int,
    payload: FileFolderRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:library:manage")),
) -> dict[str, Any]:
    return ok(services.save_folder(payload.model_dump(), current_user, folder_id=folder_id))


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
        )
    )


@router.get("/search")
def search_files(
    keyword: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(services.search_files(page=page, page_size=page_size, keyword=keyword, current_user=current_user))


@router.get("/access-logs")
def access_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    file_id: int | None = None,
    action: str = "",
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(
        services.list_access_logs(
            page=page,
            page_size=page_size,
            current_user=current_user,
            file_id=file_id,
            action=action,
        )
    )


@router.get("/index-jobs")
def index_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    file_id: int | None = None,
    status_filter: str = Query(default="", alias="status"),
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(
        services.list_index_jobs(
            page=page,
            page_size=page_size,
            current_user=current_user,
            file_id=file_id,
            status_filter=status_filter,
        )
    )


@router.post("/upload")
def upload_file(
    upload: UploadFile = File(...),
    library_id: int | None = Form(default=None),
    folder_id: int | None = Form(default=None),
    visibility: str = Form(default="tenant"),
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
            metadata={},
        )
    )


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
    _: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.list_storage_profiles())


@router.get("/admin/storage-provider-options")
def storage_provider_options(
    _: dict[str, Any] = Depends(auth.require_platform_admin),
) -> dict[str, Any]:
    return ok(services.storage_provider_options())


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


@router.get("/{file_id}")
def file_detail(
    file_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:read")),
) -> dict[str, Any]:
    return ok(services.get_file(file_id, current_user))


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


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("file:object:delete")),
) -> dict[str, Any]:
    return ok(services.delete_file(file_id, current_user))
