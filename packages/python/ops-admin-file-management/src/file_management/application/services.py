from __future__ import annotations

import hashlib
import hmac
import io
import os
from pathlib import Path
import time
import urllib.parse
from typing import Any, BinaryIO

from fastapi import HTTPException, status

from file_management.application.ports import DownloadObject, FileIndexerPort, PreviewProviderPort, StoragePort
from file_management.application.preview import NativePreviewProvider
from file_management.domain.exceptions import (
    FilePreviewUnsupported,
    FileFolderConflict,
    FileFolderNotEmpty,
    FileFolderNotFound,
    FileLibraryNotEmpty,
    FileLibraryNotFound,
    FileManagementError,
    ManagedFileNotFound,
    QuotaExceeded,
    StorageNotConfigured,
    StorageOperationFailed,
    StorageProviderUnsupported,
    UnsupportedFileType,
    PreviewProviderUnsupported,
)
from file_management.domain.models import (
    ACCESS_ACTION_DELETE,
    ACCESS_ACTION_DOWNLOAD,
    ACCESS_ACTION_PREVIEW,
    ACCESS_ACTION_UPLOAD,
    ACCESS_RESULT_FAILED,
    ACCESS_RESULT_SUCCESS,
    FILE_STATUS_AVAILABLE,
    FileFolder,
    INDEX_JOB_STATUS_FAILED,
    INDEX_JOB_STATUS_SUCCEEDED,
    PREVIEW_PROVIDER_KKFILEVIEW,
    PREVIEW_PROVIDER_OPTIONS,
    PREVIEW_PROVIDER_CUSTOM,
    SUPPORTED_PREVIEW_PROVIDERS,
    STORAGE_PROVIDER_MINIO,
    STORAGE_PROVIDER_OPTIONS,
    SUPPORTED_STORAGE_PROVIDERS,
    ManagedFile,
    PreviewProfile,
    StorageProfile,
)
from file_management.infrastructure.persistence import repositories
from file_management.infrastructure.search.database_search import DatabaseFileSearch
from file_management.infrastructure.search.elasticsearch_placeholder import NoopFileIndexer
from file_management.infrastructure.storage.minio_storage import MinioObjectStorage
from system.application.config import config_string, load_application_config, section_config
from system.application.data_access import (
    ResourceDescriptor,
    current_user_primary_department_id,
    resolve_data_access_filter,
)


_storage: StoragePort = MinioObjectStorage()
_indexer: FileIndexerPort = NoopFileIndexer()
_preview_provider: PreviewProviderPort = NativePreviewProvider()
FILE_OBJECT_RESOURCE = ResourceDescriptor(resource_key="file.object")


def configure_storage(storage: StoragePort) -> None:
    global _storage
    _storage = storage


def configure_indexer(indexer: FileIndexerPort) -> None:
    global _indexer
    _indexer = indexer


def configure_preview_provider(preview_provider: PreviewProviderPort) -> None:
    global _preview_provider
    _preview_provider = preview_provider


def load_file_management_config() -> dict[str, Any]:
    config = load_application_config()
    file_config = section_config(config, "file_management", "fileManagement", "files")
    preview_config = file_config.get("preview")
    if isinstance(preview_config, dict):
        return {**file_config, **preview_config}
    return file_config


def external_base_url() -> str:
    configured = os.environ.get("OPS_ADMIN_PUBLIC_API_BASE_URL", "").strip()
    if configured:
        return configured
    config = load_file_management_config()
    return config_string(config, "public_api_base_url", "api_base_url", "base_url")


def external_url_prefix() -> str:
    configured = os.environ.get("OPS_ADMIN_PUBLIC_API_URL_PREFIX", "").strip()
    if configured:
        return configured
    config = load_file_management_config()
    return config_string(config, "public_api_url_prefix", "api_url_prefix", "url_prefix") or "/api"


def list_libraries(*, page: int, page_size: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repositories.list_libraries(tenant_id=tenant_id, page=page, page_size=page_size)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def save_library(payload: dict[str, Any], current_user: dict[str, Any], library_id: int | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    try:
        item = repositories.save_library(
            tenant_id=tenant_id,
            library_id=library_id,
            payload={
                "name": name,
                "description": str(payload.get("description") or "").strip(),
                "library_type": str(payload.get("library_type") or "general").strip() or "general",
                "visibility": str(payload.get("visibility") or "tenant").strip() or "tenant",
                "status": str(payload.get("status") or "active").strip() or "active",
            },
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(FileLibraryNotFound("file library not found"))
    return {"item": item.to_dict()}


def delete_library(library_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        if repositories.library_file_count(tenant_id=tenant_id, library_id=library_id) > 0:
            raise FileLibraryNotEmpty("file library is not empty")
        if repositories.library_folder_count(tenant_id=tenant_id, library_id=library_id) > 0:
            raise FileLibraryNotEmpty("file library is not empty")
        deleted = repositories.delete_library(
            tenant_id=tenant_id,
            library_id=library_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    if not deleted:
        raise domain_http_error(FileLibraryNotFound("file library not found"))
    return {"id": library_id, "deleted": True}


def list_files(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    library_id: int | None = None,
    folder_id: int | None = None,
    current_folder_only: bool = False,
    keyword: str = "",
    mime_type: str = "",
    status_filter: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repositories.list_files(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            library_id=library_id,
            folder_id=folder_id,
            current_folder_only=current_folder_only,
            keyword=keyword,
            mime_type=mime_type,
            status=status_filter,
            data_scope=resolve_data_access_filter(current_user=current_user, resource=FILE_OBJECT_RESOURCE, action="read"),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def list_workspace(
    *,
    current_user: dict[str, Any],
    library_id: int | None = None,
    folder_id: int | None = None,
    keyword: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        libraries, _ = repositories.list_libraries(tenant_id=tenant_id, page=1, page_size=200)
        selected_library_id = library_id or (libraries[0].id if libraries else None)
        selected_library = (
            repositories.get_library(tenant_id=tenant_id, library_id=selected_library_id)
            if selected_library_id is not None
            else None
        )
        if selected_library_id is not None and not selected_library:
            raise FileLibraryNotFound("file library not found")
        selected_folder = None
        if folder_id is not None:
            selected_folder = repositories.get_folder(tenant_id=tenant_id, folder_id=folder_id)
            if not selected_folder or selected_folder.library_id != selected_library_id:
                raise FileFolderNotFound("file folder not found")
        folders = (
            repositories.list_folders(tenant_id=tenant_id, library_id=int(selected_library_id), parent_id=folder_id)
            if selected_library_id is not None and not keyword.strip()
            else []
        )
        files, _ = repositories.list_files(
            tenant_id=tenant_id,
            page=1,
            page_size=500,
            library_id=selected_library_id,
            folder_id=folder_id,
            current_folder_only=not bool(keyword.strip()),
            keyword=keyword.strip(),
            data_scope=resolve_data_access_filter(current_user=current_user, resource=FILE_OBJECT_RESOURCE, action="read"),
        )
        usage = repositories.storage_usage(tenant_id=tenant_id)
        folder_usages = (
            repositories.folder_storage_usages(
                tenant_id=tenant_id,
                library_id=int(selected_library_id),
                folder_ids=[item.id for item in folders],
            )
            if selected_library_id is not None and folders
            else {}
        )
        current_usage = workspace_usage_from_items(tenant_id=tenant_id, folders=folders, folder_usages=folder_usages, files=files)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    return {
        "libraries": [item.to_dict() for item in libraries],
        "current_library": selected_library.to_dict() if selected_library else None,
        "current_folder": selected_folder.to_dict() if selected_folder else None,
        "breadcrumbs": [item.to_dict() for item in folder_breadcrumbs(selected_folder, tenant_id=tenant_id)],
        "folders": [folder_to_workspace_dict(item, folder_usages) for item in folders],
        "files": [item.to_dict() for item in files],
        "usage": usage.to_dict(),
        "current_usage": current_usage,
    }


def folder_tree(*, library_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        library = repositories.get_library(tenant_id=tenant_id, library_id=library_id)
        if not library:
            raise FileLibraryNotFound("file library not found")
        folders = repositories.list_all_folders(tenant_id=tenant_id, library_id=library_id)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    return {"library": library.to_dict(), "items": [item.to_dict() for item in folders]}


def save_folder(payload: dict[str, Any], current_user: dict[str, Any], folder_id: int | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    actor = current_actor(current_user)
    actor_id = current_user_id_or_none(current_user)
    name = str(payload.get("name") or "").strip()
    library_id = int(payload.get("library_id") or 0)
    parent_id = int(payload["parent_id"]) if payload.get("parent_id") is not None else None
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    if not library_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="library_id is required")
    try:
        if not repositories.get_library(tenant_id=tenant_id, library_id=library_id):
            raise FileLibraryNotFound("file library not found")
        if parent_id is not None:
            parent = repositories.get_folder(tenant_id=tenant_id, folder_id=parent_id)
            if not parent or parent.library_id != library_id:
                raise FileFolderNotFound("parent folder not found")
        if folder_id:
            current = repositories.get_folder(tenant_id=tenant_id, folder_id=folder_id)
            if not current:
                raise FileFolderNotFound("file folder not found")
            if parent_id == folder_id:
                raise FileFolderConflict("folder cannot be its own parent")
        item = repositories.save_folder(
            tenant_id=tenant_id,
            folder_id=folder_id,
            payload={
                "library_id": library_id,
                "parent_id": parent_id,
                "name": name,
                "description": str(payload.get("description") or "").strip(),
                "status": str(payload.get("status") or "active").strip() or "active",
            },
            actor=actor,
            actor_id=actor_id,
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    if not item:
        raise domain_http_error(FileFolderNotFound("file folder not found"))
    return {"item": item.to_dict()}


def delete_folder(folder_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        folder = repositories.get_folder(tenant_id=tenant_id, folder_id=folder_id)
        if not folder:
            raise FileFolderNotFound("file folder not found")
        if repositories.folder_child_count(tenant_id=tenant_id, folder_id=folder_id) > 0:
            raise FileFolderNotEmpty("file folder is not empty")
        deleted = repositories.delete_folder(
            tenant_id=tenant_id,
            folder_id=folder_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    if not deleted:
        raise domain_http_error(FileFolderNotFound("file folder not found"))
    return {"id": folder_id, "deleted": True}


def search_files(*, page: int, page_size: int, keyword: str, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = DatabaseFileSearch().search(tenant_id=tenant_id, keyword=keyword, page=page, page_size=page_size)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def get_file(file_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_tenant_file(file_id=file_id, current_user=current_user)
    return {"item": item.to_dict()}


def get_file_preview_metadata(file_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_tenant_file(file_id=file_id, current_user=current_user)
    preview = _preview_provider.metadata_for(item)
    if not preview.previewable:
        external_preview = external_preview_for_file(item)
        if external_preview:
            preview = external_preview
    return {"item": item.to_dict(), "preview": preview.to_dict()}


def upload_file(
    *,
    current_user: dict[str, Any],
    filename: str,
    content_type: str,
    stream: BinaryIO,
    library_id: int | None,
    visibility: str,
    metadata: dict[str, Any],
    folder_id: int | None = None,
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    actor = current_actor(current_user)
    actor_id = current_user_id_or_none(current_user)
    original_name = Path(filename or "upload.bin").name or "upload.bin"
    display_name = original_name
    extension = normalize_extension(original_name)
    content_type = (content_type or "application/octet-stream").strip() or "application/octet-stream"
    try:
        profile = default_storage_profile()
        if library_id is not None and not repositories.get_library(tenant_id=tenant_id, library_id=library_id):
            raise FileLibraryNotFound("file library not found")
        if folder_id is not None:
            folder = repositories.get_folder(tenant_id=tenant_id, folder_id=folder_id)
            if not folder:
                raise FileFolderNotFound("file folder not found")
            if library_id is None:
                library_id = folder.library_id
            elif folder.library_id != library_id:
                raise FileFolderNotFound("file folder not found")
        quota = repositories.get_quota(tenant_id=tenant_id)
        usage = repositories.storage_usage(tenant_id=tenant_id)
        staged = stage_upload(stream)
        validate_upload(
            quota_enabled=bool(quota.enabled) if quota else True,
            quota_bytes=int(quota.quota_bytes) if quota else 0,
            max_file_size_bytes=int(quota.max_file_size_bytes) if quota else 0,
            allowed_mime_types=quota.allowed_mime_types if quota else [],
            blocked_extensions=quota.blocked_extensions if quota else [],
            used_bytes=usage.used_bytes,
            size_bytes=staged["size_bytes"],
            extension=extension,
            mime_type=content_type,
        )
        file_id = repositories.next_file_id()
        storage_key = storage_key_for(
            tenant_id=tenant_id,
            file_id=file_id,
            sha256=str(staged["sha256"]),
            extension=extension,
        )
        stored = _storage.save(
            profile=profile,
            key=storage_key,
            content=staged["stream"],
            content_type=content_type,
        )
        item = repositories.create_file(
            file_id=file_id,
            tenant_id=tenant_id,
            library_id=library_id,
            folder_id=folder_id,
            original_name=original_name,
            display_name=display_name,
            extension=extension,
            mime_type=content_type,
            size_bytes=int(stored.size_bytes),
            sha256=str(stored.sha256),
            storage_provider=stored.provider,
            storage_bucket=stored.bucket,
            storage_key=stored.key,
            visibility=visibility or "tenant",
            metadata=metadata,
            actor=actor,
            actor_id=actor_id,
            owner_user_id=actor_id,
            owner_department_id=current_user_primary_department_id(current_user),
        )
        create_index_job_for_file(item, "upsert", current_user)
        repositories.record_access_log(
            tenant_id=tenant_id,
            file_id=item.id,
            action=ACCESS_ACTION_UPLOAD,
            result=ACCESS_RESULT_SUCCESS,
            actor=actor,
            actor_id=actor_id,
            detail={"original_name": item.original_name, "size_bytes": item.size_bytes},
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    except Exception as exc:
        raise domain_http_error(StorageOperationFailed(str(exc))) from exc
    return {"item": item.to_dict()}


def download_file(
    file_id: int,
    current_user: dict[str, Any],
    *,
    client_ip: str = "",
    user_agent: str = "",
) -> tuple[ManagedFile, DownloadObject]:
    item = load_tenant_file(file_id=file_id, current_user=current_user)
    try:
        profile = storage_profile_for_file(item)
        download = _storage.open_for_read(profile=profile, key=item.storage_key)
        repositories.record_access_log(
            tenant_id=item.tenant_id,
            file_id=item.id,
            action=ACCESS_ACTION_DOWNLOAD,
            result=ACCESS_RESULT_SUCCESS,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
            client_ip=client_ip,
            user_agent=user_agent,
            detail={"original_name": item.original_name, "size_bytes": item.size_bytes},
        )
        return item, download
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    except Exception as exc:
        raise domain_http_error(StorageOperationFailed(str(exc))) from exc


def preview_file(
    file_id: int,
    current_user: dict[str, Any],
    *,
    client_ip: str = "",
    user_agent: str = "",
) -> tuple[ManagedFile, DownloadObject, dict[str, object]]:
    item = load_tenant_file(file_id=file_id, current_user=current_user)
    preview = _preview_provider.metadata_for(item)
    if not preview.previewable:
        raise domain_http_error(FilePreviewUnsupported(preview.reason or "file preview is not supported"))
    try:
        profile = storage_profile_for_file(item)
        download = _storage.open_for_read(profile=profile, key=item.storage_key)
        repositories.record_access_log(
            tenant_id=item.tenant_id,
            file_id=item.id,
            action=ACCESS_ACTION_PREVIEW,
            result=ACCESS_RESULT_SUCCESS,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
            client_ip=client_ip,
            user_agent=user_agent,
            detail={"original_name": item.original_name, "size_bytes": item.size_bytes, "mode": preview.mode},
        )
        return item, download, preview.to_dict()
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    except Exception as exc:
        raise domain_http_error(StorageOperationFailed(str(exc))) from exc


def preview_source_file(
    file_id: int,
    *,
    expires: int,
    signature: str,
) -> tuple[ManagedFile, DownloadObject]:
    if not verify_preview_source_signature(file_id, expires, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="preview source signature is invalid or expired")
    try:
        item = repositories.get_file(tenant_id=None, file_id=file_id)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(ManagedFileNotFound("file not found"))
    try:
        profile = storage_profile_for_file(item)
        download = _storage.open_for_read(profile=profile, key=item.storage_key)
        return item, download
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    except Exception as exc:
        raise domain_http_error(StorageOperationFailed(str(exc))) from exc


def delete_file(file_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_tenant_file(file_id=file_id, current_user=current_user)
    try:
        profile = storage_profile_for_file(item)
        _storage.delete(profile=profile, key=item.storage_key)
        repositories.delete_file(
            tenant_id=item.tenant_id,
            file_id=item.id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
        create_index_job_for_file(item, "delete", current_user)
        repositories.record_access_log(
            tenant_id=item.tenant_id,
            file_id=item.id,
            action=ACCESS_ACTION_DELETE,
            result=ACCESS_RESULT_SUCCESS,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
            detail={"original_name": item.original_name},
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    except FileManagementError as exc:
        raise domain_http_error(exc) from exc
    except Exception as exc:
        raise domain_http_error(StorageOperationFailed(str(exc))) from exc
    return {"id": file_id, "deleted": True}


def quota_for_tenant(tenant_id: int) -> dict[str, Any]:
    try:
        quota = repositories.get_quota(tenant_id=tenant_id)
        usage = repositories.storage_usage(tenant_id=tenant_id)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {"quota": quota.to_dict() if quota else None, "usage": usage.to_dict()}


def save_quota(tenant_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        quota = repositories.save_quota(
            tenant_id=tenant_id,
            quota_bytes=int(payload.get("quota_bytes") or 0),
            max_file_size_bytes=int(payload.get("max_file_size_bytes") or 0),
            allowed_mime_types=normalize_string_list(payload.get("allowed_mime_types")),
            blocked_extensions=[normalize_extension(value) for value in normalize_string_list(payload.get("blocked_extensions"))],
            enabled=bool(payload.get("enabled", True)),
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {"quota": quota.to_dict(), "usage": repositories.storage_usage(tenant_id=tenant_id).to_dict()}


def list_storage_profiles() -> dict[str, Any]:
    try:
        items = repositories.list_storage_profiles()
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {"items": [item.to_dict() for item in items]}


def list_preview_profiles() -> dict[str, Any]:
    try:
        items = repositories.list_preview_profiles()
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {"items": [item.to_dict() for item in items]}


def save_preview_profile(payload: dict[str, Any], current_user: dict[str, Any], profile_id: int | None = None) -> dict[str, Any]:
    provider = str(payload.get("provider") or "kkfileview")
    if provider not in SUPPORTED_PREVIEW_PROVIDERS:
        raise domain_http_error(PreviewProviderUnsupported(f"preview provider is not supported: {provider}"))
    body = dict(payload)
    body["supported_extensions"] = normalize_string_list(body.get("supported_extensions"))
    body["base_url"] = str(body.get("base_url") or "").rstrip("/")
    if not body["base_url"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="base_url is required")
    try:
        item = repositories.save_preview_profile(
            profile_id=profile_id,
            payload=body,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {"item": item.to_dict()}


def set_default_preview_profile(profile_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        item = repositories.set_default_preview_profile(
            profile_id=profile_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="preview profile not found")
    return {"item": item.to_dict()}


def preview_provider_options() -> dict[str, Any]:
    return {"items": list(PREVIEW_PROVIDER_OPTIONS)}


def save_storage_profile(payload: dict[str, Any], current_user: dict[str, Any], profile_id: int | None = None) -> dict[str, Any]:
    provider = str(payload.get("provider") or STORAGE_PROVIDER_MINIO).strip()
    if provider not in SUPPORTED_STORAGE_PROVIDERS:
        raise domain_http_error(StorageProviderUnsupported(f"storage provider is not supported: {provider}"))
    try:
        item = repositories.save_storage_profile(
            profile_id=profile_id,
            payload={
                "provider": provider,
                "name": str(payload.get("name") or "").strip(),
                "endpoint": str(payload.get("endpoint") or "").strip(),
                "region": str(payload.get("region") or "").strip(),
                "bucket": str(payload.get("bucket") or "").strip(),
                "access_key_id": str(payload.get("access_key_id") or "").strip(),
                "secret_access_key": str(payload.get("secret_access_key") or "").strip(),
                "path_style_enabled": bool(payload.get("path_style_enabled", True)),
                "tls_enabled": bool(payload.get("tls_enabled", True)),
                "enabled": bool(payload.get("enabled", True)),
                "is_default": bool(payload.get("is_default", False)),
                "extra_config": payload.get("extra_config") if isinstance(payload.get("extra_config"), dict) else {},
            },
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {"item": item.to_dict()}


def set_default_storage_profile(profile_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        item = repositories.set_default_storage_profile(
            profile_id=profile_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="storage profile not found")
    return {"item": item.to_dict()}


def test_storage_profile(profile_id: int) -> dict[str, Any]:
    try:
        profile = repositories.get_storage_profile(profile_id=profile_id)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="storage profile not found")
    if profile.provider not in SUPPORTED_STORAGE_PROVIDERS:
        raise domain_http_error(StorageProviderUnsupported(f"storage provider is not supported: {profile.provider}"))
    try:
        return _storage.test_connection(profile=profile)
    except Exception as exc:
        return {"ok": False, "provider": profile.provider, "message": str(exc)}


def storage_provider_options() -> dict[str, Any]:
    return {"items": [dict(item) for item in STORAGE_PROVIDER_OPTIONS]}


def external_preview_for_file(item: ManagedFile):
    try:
        profile = repositories.get_default_preview_profile()
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not profile or not profile.enabled:
        return None
    extension = normalize_extension(item.extension)
    if profile.supported_extensions and extension not in profile.supported_extensions:
        return None
    source_url = signed_preview_source_url(item, profile)
    preview_url = external_preview_url(profile, source_url)
    native_preview = _preview_provider.metadata_for(item)
    return native_preview.__class__(
        previewable=True,
        engine=profile.provider,
        mode="external",
        mime_type=item.mime_type,
        url=preview_url,
    )


def external_preview_url(profile: PreviewProfile, source_url: str) -> str:
    if profile.provider == PREVIEW_PROVIDER_KKFILEVIEW:
        return kkfileview_preview_url(profile, source_url)
    if profile.provider == PREVIEW_PROVIDER_CUSTOM:
        return custom_preview_url(profile, source_url)
    raise domain_http_error(PreviewProviderUnsupported(f"preview provider is not supported: {profile.provider}"))


def kkfileview_preview_url(profile: PreviewProfile, source_url: str) -> str:
    param_name = str(profile.config.get("url_param_name") or "url")
    return f"{profile.base_url.rstrip('/')}/onlinePreview?{urllib.parse.urlencode({param_name: source_url})}"


def custom_preview_url(profile: PreviewProfile, source_url: str) -> str:
    param_name = str(profile.config.get("url_param_name") or "url")
    path = str(profile.config.get("preview_path") or "/onlinePreview")
    path = path if path.startswith("/") else f"/{path}"
    return f"{profile.base_url.rstrip('/')}{path}?{urllib.parse.urlencode({param_name: source_url})}"


def signed_preview_source_url(item: ManagedFile, profile: PreviewProfile) -> str:
    ttl = int(profile.config.get("source_url_ttl_seconds") or 300)
    ttl = max(60, min(ttl, 3600))
    expires = int(time.time()) + ttl
    signature = sign_preview_source(item.id, expires)
    url_prefix = external_url_prefix().strip("/")
    path_prefix = f"/{url_prefix}" if url_prefix else ""
    path = f"{path_prefix}/files/{item.id}/preview-source"
    query = urllib.parse.urlencode({"expires": expires, "signature": signature})
    base_url = external_base_url().rstrip("/")
    return f"{base_url}{path}?{query}" if base_url else f"{path}?{query}"


def sign_preview_source(file_id: int, expires: int) -> str:
    payload = f"{file_id}:{expires}".encode("utf-8")
    return hmac.new(preview_signing_secret().encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_preview_source_signature(file_id: int, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
        return False
    expected = sign_preview_source(file_id, expires)
    return hmac.compare_digest(expected, signature)


def preview_signing_secret() -> str:
    return os.environ.get("OPS_ADMIN_FILE_PREVIEW_SECRET") or os.environ.get("FG_AGENT_AUTH_SECRET", "fg-agent-dev-secret-change-me")


def list_access_logs(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    file_id: int | None = None,
    action: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repositories.list_access_logs(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            file_id=file_id,
            action=action,
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def list_index_jobs(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    file_id: int | None = None,
    status_filter: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repositories.list_index_jobs(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            file_id=file_id,
            status=status_filter,
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def reindex_file(file_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_tenant_file(file_id=file_id, current_user=current_user)
    job = create_index_job_for_file(item, "manual_reindex", current_user)
    return {"item": job.to_dict()}


def load_tenant_file(*, file_id: int, current_user: dict[str, Any]) -> ManagedFile:
    tenant_id = current_tenant_id(current_user)
    try:
        item = repositories.get_file(tenant_id=tenant_id, file_id=file_id)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(ManagedFileNotFound("file not found"))
    return item


def folder_breadcrumbs(folder: FileFolder | None, *, tenant_id: int) -> list[FileFolder]:
    if not folder:
        return []
    folders = [folder]
    visited = {folder.id}
    parent_id = folder.parent_id
    while parent_id is not None:
        parent = repositories.get_folder(tenant_id=tenant_id, folder_id=parent_id)
        if not parent or parent.id in visited:
            break
        folders.append(parent)
        visited.add(parent.id)
        parent_id = parent.parent_id
    return list(reversed(folders))


def folder_to_workspace_dict(item: FileFolder, folder_usages: dict[int, Any]) -> dict[str, Any]:
    payload = item.to_dict()
    usage = folder_usages.get(item.id)
    payload["size_bytes"] = int(usage.used_bytes) if usage else 0
    payload["file_count"] = int(usage.file_count) if usage else 0
    return payload


def workspace_usage_from_items(
    *,
    tenant_id: int,
    folders: list[FileFolder],
    folder_usages: dict[int, Any],
    files: list[ManagedFile],
) -> dict[str, Any]:
    used_bytes = sum(int(file.size_bytes) for file in files)
    file_count = len(files)
    for folder in folders:
        usage = folder_usages.get(folder.id)
        if not usage:
            continue
        used_bytes += int(usage.used_bytes)
        file_count += int(usage.file_count)
    return {"tenant_id": tenant_id, "used_bytes": used_bytes, "file_count": file_count}


def default_storage_profile() -> StorageProfile:
    profile = repositories.get_default_storage_profile()
    if not profile:
        raise StorageNotConfigured("default MinIO storage profile is not configured")
    if profile.provider != STORAGE_PROVIDER_MINIO:
        raise StorageProviderUnsupported(f"storage provider is not supported: {profile.provider}")
    if not profile.enabled:
        raise StorageNotConfigured("default MinIO storage profile is disabled")
    return profile


def storage_profile_for_file(item: ManagedFile) -> StorageProfile:
    profile = repositories.get_default_storage_profile(provider=item.storage_provider)
    if not profile:
        raise StorageNotConfigured(f"storage profile is not configured for provider: {item.storage_provider}")
    return profile


def create_index_job_for_file(item: ManagedFile, job_type: str, current_user: dict[str, Any]):
    actor = current_actor(current_user)
    actor_id = current_user_id_or_none(current_user)
    try:
        if job_type == "delete":
            _indexer.remove_file(item.id)
        else:
            _indexer.index_file(item.id)
            repositories.mark_file_indexed(tenant_id=item.tenant_id, file_id=item.id)
        return repositories.create_index_job(
            tenant_id=item.tenant_id,
            file_id=item.id,
            job_type=job_type,
            status=INDEX_JOB_STATUS_SUCCEEDED,
            payload={"provider": "database", "reserved_for": "elasticsearch"},
            actor=actor,
            actor_id=actor_id,
        )
    except Exception as exc:
        return repositories.create_index_job(
            tenant_id=item.tenant_id,
            file_id=item.id,
            job_type=job_type,
            status=INDEX_JOB_STATUS_FAILED,
            payload={"provider": "database", "reserved_for": "elasticsearch"},
            actor=actor,
            actor_id=actor_id,
            last_error=str(exc),
        )


def stage_upload(stream: BinaryIO) -> dict[str, Any]:
    digest = hashlib.sha256()
    size_bytes = 0
    buffer = io.BytesIO()
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        size_bytes += len(chunk)
        digest.update(chunk)
        buffer.write(chunk)
    buffer.seek(0)
    return {"stream": buffer, "size_bytes": size_bytes, "sha256": digest.hexdigest()}


def validate_upload(
    *,
    quota_enabled: bool,
    quota_bytes: int,
    max_file_size_bytes: int,
    allowed_mime_types: list[str],
    blocked_extensions: list[str],
    used_bytes: int,
    size_bytes: int,
    extension: str,
    mime_type: str,
) -> None:
    if not quota_enabled:
        raise QuotaExceeded("tenant file storage is disabled")
    if max_file_size_bytes > 0 and size_bytes > max_file_size_bytes:
        raise QuotaExceeded("file exceeds max_file_size_bytes")
    if quota_bytes > 0 and used_bytes + size_bytes > quota_bytes:
        raise QuotaExceeded("tenant file storage quota exceeded")
    if allowed_mime_types and mime_type not in allowed_mime_types:
        raise UnsupportedFileType("mime type is not allowed")
    if extension and extension in blocked_extensions:
        raise UnsupportedFileType("file extension is blocked")


def storage_key_for(*, tenant_id: int, file_id: int, sha256: str, extension: str) -> str:
    suffix = f".{extension}" if extension else ""
    return f"tenants/{tenant_id}/files/{file_id}-{sha256[:12]}{suffix}"


def normalize_extension(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.lstrip(".")


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current = current_user.get("current_tenant") or {}
    tenant_id = current.get("id") or current_user.get("tenant_id") or 0
    return int(tenant_id)


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None


def storage_unavailable(exc: RuntimeError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


def domain_http_error(exc: FileManagementError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))
