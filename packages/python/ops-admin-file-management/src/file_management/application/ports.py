from __future__ import annotations

from dataclasses import dataclass
from typing import Any, BinaryIO, Literal, Protocol

from file_management.domain.models import (
    FileFolder,
    FileSearchIndexJob,
    FileLibrary,
    TenantStorageQuota,
    StorageUsage,
    FileAccessLog,
    ManagedFile,
    PreviewProfile,
    StorageProfile,
)


@dataclass(frozen=True)
class StoredObject:
    provider: str
    bucket: str
    key: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class DownloadObject:
    stream: BinaryIO
    size_bytes: int | None = None
    content_type: str | None = None


PreviewMode = Literal["image", "pdf", "text", "audio", "video", "external", "unsupported"]


@dataclass(frozen=True)
class FilePreview:
    previewable: bool
    engine: str
    mode: PreviewMode
    mime_type: str
    reason: str = ""
    url: str = ""
    max_inline_bytes: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "previewable": self.previewable,
            "engine": self.engine,
            "mode": self.mode,
            "mime_type": self.mime_type,
            "reason": self.reason,
            "url": self.url,
        }
        if self.max_inline_bytes is not None:
            payload["max_inline_bytes"] = self.max_inline_bytes
        return payload


class StoragePort(Protocol):
    def save(self, *, profile: StorageProfile, key: str, content: BinaryIO, content_type: str) -> StoredObject:
        ...

    def open_for_read(self, *, profile: StorageProfile, key: str) -> DownloadObject:
        ...

    def delete(self, *, profile: StorageProfile, key: str) -> None:
        ...

    def exists(self, *, profile: StorageProfile, key: str) -> bool:
        ...

    def test_connection(self, *, profile: StorageProfile) -> dict[str, object]:
        ...


class FileIndexerPort(Protocol):
    def index_file(self, file_id: int) -> None:
        ...

    def remove_file(self, file_id: int) -> None:
        ...


class PreviewProviderPort(Protocol):
    engine: str

    def metadata_for(self, file: ManagedFile) -> FilePreview:
        ...


class MetadataBindingPort(Protocol):
    def bind_resource(
        self,
        *,
        tenant_id: int,
        resource_type_code: str,
        resource_id: str | int,
        metadata: dict[str, Any],
        tag_codes: list[str],
        actor: str,
        actor_id: int | None,
    ) -> None:
        ...

    def search_resource_ids(
        self,
        *,
        tenant_id: int,
        resource_type_code: str,
        metadata_filters: list[dict[str, Any]],
        tag_codes: list[str],
        max_results: int,
        offset: int,
    ) -> tuple[list[int], int]:
        ...

    def resource_tag_codes(self, *, tenant_id: int, resource_type_code: str, resource_id: str | int) -> list[str]:
        ...


class FileSearchPort(Protocol):
    def search(
        self,
        *,
        tenant_id: int,
        keyword: str,
        page: int,
        page_size: int,
        file_ids: list[int] | None = None,
    ) -> tuple[list[ManagedFile], int]:
        ...


class FileManagementRepository(Protocol):
    def list_libraries(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[FileLibrary], int]:
        ...

    def save_library(
        self,
        *,
        tenant_id: int,
        library_id: int | None,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> FileLibrary | None:
        ...

    def library_file_count(self, *, tenant_id: int, library_id: int) -> int:
        ...

    def library_folder_count(self, *, tenant_id: int, library_id: int) -> int:
        ...

    def delete_library(self, *, tenant_id: int, library_id: int, actor: str, actor_id: int | None) -> bool:
        ...

    def list_files(
        self,
        *,
        tenant_id: int | None,
        page: int,
        page_size: int,
        library_id: int | None = None,
        folder_id: int | None = None,
        current_folder_only: bool = False,
        keyword: str = "",
        mime_type: str = "",
        status: str = "",
        data_scope: Any = None,
        file_ids: list[int] | None = None,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[ManagedFile], int]:
        ...

    def get_library(self, *, tenant_id: int, library_id: int) -> FileLibrary | None:
        ...

    def get_folder(self, *, tenant_id: int, folder_id: int) -> FileFolder | None:
        ...

    def list_folders(self, *, tenant_id: int, library_id: int, parent_id: int | None = None) -> list[FileFolder]:
        ...

    def storage_usage(self, *, tenant_id: int) -> StorageUsage:
        ...

    def folder_storage_usages(
        self,
        *,
        tenant_id: int,
        library_id: int,
        folder_ids: list[int],
    ) -> dict[int, StorageUsage]:
        ...

    def list_all_folders(self, *, tenant_id: int, library_id: int) -> list[FileFolder]:
        ...

    def save_folder(
        self,
        *,
        tenant_id: int,
        folder_id: int | None,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> FileFolder | None:
        ...

    def folder_child_count(self, *, tenant_id: int, folder_id: int) -> int:
        ...

    def delete_folder(self, *, tenant_id: int, folder_id: int, actor: str, actor_id: int | None) -> bool:
        ...

    def update_file_metadata(
        self,
        *,
        tenant_id: int,
        file_id: int,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> ManagedFile | None:
        ...

    def get_quota(self, *, tenant_id: int) -> TenantStorageQuota:
        ...

    def save_quota(
        self,
        *,
        tenant_id: int,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> TenantStorageQuota:
        ...

    def next_file_id(self) -> int:
        ...

    def create_file(
        self,
        *,
        tenant_id: int,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> ManagedFile:
        ...

    def record_access_log(
        self,
        *,
        tenant_id: int,
        file_id: int,
        action: str,
        result: str,
        actor: str,
        actor_id: int | None,
        owner_user_id: int | None,
        owner_department_id: int | None,
        detail: dict[str, Any] | None = None,
    ) -> FileAccessLog:
        ...

    def get_file(self, *, tenant_id: int | None, file_id: int, data_scope: Any = None) -> ManagedFile | None:
        ...

    def delete_file(
        self,
        *,
        tenant_id: int,
        file_id: int,
        actor: str,
        actor_id: int | None,
    ) -> bool:
        ...

    def list_storage_profiles(self, *, sort_by: str | None = None, sort_dir: str | None = None) -> list[StorageProfile]:
        ...

    def list_preview_profiles(self, *, sort_by: str | None = None, sort_dir: str | None = None) -> list[PreviewProfile]:
        ...

    def save_preview_profile(
        self,
        *,
        profile_id: int | None,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> PreviewProfile:
        ...

    def set_default_preview_profile(
        self,
        *,
        profile_id: int,
        actor: str,
        actor_id: int | None,
    ) -> PreviewProfile | None:
        ...

    def save_storage_profile(
        self,
        *,
        profile_id: int | None,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> StorageProfile:
        ...

    def set_default_storage_profile(
        self,
        *,
        profile_id: int,
        actor: str,
        actor_id: int | None,
    ) -> StorageProfile | None:
        ...

    def get_storage_profile(self, *, profile_id: int) -> StorageProfile | None:
        ...

    def get_default_preview_profile(self) -> PreviewProfile | None:
        ...

    def get_default_storage_profile(self, *, provider: str | None = None) -> StorageProfile | None:
        ...

    def list_access_logs(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        file_id: int | None = None,
        action: str = "",
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[FileAccessLog], int]:
        ...

    def list_index_jobs(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        file_id: int | None = None,
        status: str = "",
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[FileSearchIndexJob], int]:
        ...

    def mark_file_indexed(self, *, tenant_id: int, file_id: int) -> None:
        ...

    def create_index_job(
        self,
        *,
        tenant_id: int,
        file_id: int,
        job_type: str,
        status: str,
        payload: dict[str, Any] | None,
        actor: str,
        actor_id: int | None,
        last_error: str = "",
    ) -> FileSearchIndexJob:
        ...
