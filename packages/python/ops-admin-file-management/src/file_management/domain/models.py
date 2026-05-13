from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FILE_STATUS_AVAILABLE = "available"
FILE_STATUS_DELETED = "deleted"
FILE_STATUS_BLOCKED = "blocked"
LIBRARY_STATUS_ACTIVE = "active"
LIBRARY_STATUS_DISABLED = "disabled"
STORAGE_PROVIDER_MINIO = "minio"
STORAGE_PROVIDER_TENCENT_COS = "tencent_cos"
STORAGE_PROVIDER_ALIYUN_OSS = "aliyun_oss"
SUPPORTED_STORAGE_PROVIDERS = {STORAGE_PROVIDER_MINIO}
STORAGE_PROVIDER_OPTIONS = (
    {
        "provider": STORAGE_PROVIDER_MINIO,
        "label": "MinIO",
        "supported": True,
        "config_schema": {
            "endpoint": {"required": True},
            "bucket": {"required": True},
            "access_key_id": {"required": True},
            "secret_access_key": {"required": True},
            "path_style_enabled": {"required": False, "default": True},
            "tls_enabled": {"required": False, "default": True},
        },
    },
    {
        "provider": STORAGE_PROVIDER_TENCENT_COS,
        "label": "Tencent COS",
        "supported": False,
        "config_schema": {},
    },
    {
        "provider": STORAGE_PROVIDER_ALIYUN_OSS,
        "label": "Aliyun OSS",
        "supported": False,
        "config_schema": {},
    },
)
PREVIEW_PROVIDER_NATIVE = "native"
PREVIEW_PROVIDER_KKFILEVIEW = "kkfileview"
PREVIEW_PROVIDER_CUSTOM = "custom"
SUPPORTED_PREVIEW_PROVIDERS = {PREVIEW_PROVIDER_KKFILEVIEW, PREVIEW_PROVIDER_CUSTOM}
PREVIEW_PROVIDER_OPTIONS = (
    {
        "provider": PREVIEW_PROVIDER_NATIVE,
        "label": "Native Preview",
        "supported": True,
        "config_schema": {},
    },
    {
        "provider": PREVIEW_PROVIDER_KKFILEVIEW,
        "label": "kkFileView",
        "supported": True,
        "config_schema": {
            "base_url": {"required": True},
            "source_url_ttl_seconds": {"required": False, "default": 300},
            "url_param_name": {"required": False, "default": "url"},
        },
    },
    {
        "provider": PREVIEW_PROVIDER_CUSTOM,
        "label": "Custom External Preview",
        "supported": True,
        "config_schema": {
            "base_url": {"required": True},
            "source_url_ttl_seconds": {"required": False, "default": 300},
            "url_param_name": {"required": False, "default": "url"},
        },
    },
)

ACCESS_ACTION_DOWNLOAD = "download"
ACCESS_ACTION_PREVIEW = "preview"
ACCESS_ACTION_UPLOAD = "upload"
ACCESS_ACTION_DELETE = "delete"
ACCESS_RESULT_SUCCESS = "success"
ACCESS_RESULT_FAILED = "failed"
INDEX_JOB_STATUS_PENDING = "pending"
INDEX_JOB_STATUS_SUCCEEDED = "succeeded"
INDEX_JOB_STATUS_FAILED = "failed"


@dataclass(frozen=True)
class FileLibrary:
    id: int
    tenant_id: int
    name: str
    description: str
    library_type: str
    visibility: str
    status: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "library_type": self.library_type,
            "visibility": self.visibility,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class FileFolder:
    id: int
    tenant_id: int
    library_id: int
    parent_id: int | None
    name: str
    description: str
    status: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "library_id": self.library_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class ManagedFile:
    id: int
    tenant_id: int
    library_id: int | None
    folder_id: int | None
    original_name: str
    display_name: str
    extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    storage_provider: str
    storage_bucket: str
    storage_key: str
    status: str
    visibility: str
    metadata: dict[str, Any]
    indexed_at: str | None
    create_time: str
    update_time: str

    def to_dict(self, *, include_storage_key: bool = False) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "library_id": self.library_id,
            "folder_id": self.folder_id,
            "original_name": self.original_name,
            "display_name": self.display_name,
            "extension": self.extension,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "storage_provider": self.storage_provider,
            "storage_bucket": self.storage_bucket,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": self.metadata,
            "indexed_at": self.indexed_at,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
        if include_storage_key:
            payload["storage_key"] = self.storage_key
        return payload


@dataclass(frozen=True)
class TenantStorageQuota:
    id: int
    tenant_id: int
    quota_bytes: int
    max_file_size_bytes: int
    allowed_mime_types: list[str]
    blocked_extensions: list[str]
    enabled: bool
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "quota_bytes": self.quota_bytes,
            "max_file_size_bytes": self.max_file_size_bytes,
            "allowed_mime_types": self.allowed_mime_types,
            "blocked_extensions": self.blocked_extensions,
            "enabled": self.enabled,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class StorageProfile:
    id: int
    tenant_id: int
    provider: str
    name: str
    endpoint: str
    region: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    path_style_enabled: bool
    tls_enabled: bool
    is_default: bool
    enabled: bool
    extra_config: dict[str, Any]
    create_time: str
    update_time: str

    def to_dict(self, *, include_secret: bool = False) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "provider": self.provider,
            "name": self.name,
            "endpoint": self.endpoint,
            "region": self.region,
            "bucket": self.bucket,
            "access_key_id": self.access_key_id,
            "path_style_enabled": self.path_style_enabled,
            "tls_enabled": self.tls_enabled,
            "is_default": self.is_default,
            "enabled": self.enabled,
            "extra_config": self.extra_config,
            "secret_configured": bool(self.secret_access_key),
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
        if include_secret:
            payload["secret_access_key"] = self.secret_access_key
        return payload


@dataclass(frozen=True)
class PreviewProfile:
    id: int
    tenant_id: int
    provider: str
    name: str
    base_url: str
    enabled: bool
    is_default: bool
    supported_extensions: list[str]
    config: dict[str, Any]
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "provider": self.provider,
            "name": self.name,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "is_default": self.is_default,
            "supported_extensions": self.supported_extensions,
            "config": self.config,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class StorageUsage:
    tenant_id: int
    used_bytes: int
    file_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "used_bytes": self.used_bytes,
            "file_count": self.file_count,
        }


@dataclass(frozen=True)
class FileAccessLog:
    id: int
    tenant_id: int
    file_id: int | None
    action: str
    actor_user_id: int | None
    actor_name: str
    client_ip: str
    user_agent: str
    result: str
    detail: dict[str, Any]
    create_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "action": self.action,
            "actor_user_id": self.actor_user_id,
            "actor_name": self.actor_name,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "result": self.result,
            "detail": self.detail,
            "create_time": self.create_time,
        }


@dataclass(frozen=True)
class FileSearchIndexJob:
    id: int
    tenant_id: int
    file_id: int | None
    job_type: str
    status: str
    attempts: int
    last_error: str
    scheduled_time: str
    finished_time: str | None
    payload: dict[str, Any]
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "job_type": self.job_type,
            "status": self.status,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "scheduled_time": self.scheduled_time,
            "finished_time": self.finished_time,
            "payload": self.payload,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
