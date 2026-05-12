from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FileLibraryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=800)
    library_type: str = Field(default="general", max_length=60)
    visibility: str = Field(default="tenant", max_length=60)
    status: str = Field(default="active", max_length=60)


class TenantStorageQuotaRequest(BaseModel):
    quota_bytes: int = Field(default=0, ge=0)
    max_file_size_bytes: int = Field(default=0, ge=0)
    allowed_mime_types: list[str] = Field(default_factory=list)
    blocked_extensions: list[str] = Field(default_factory=list)
    enabled: bool = True


class StorageProfileRequest(BaseModel):
    provider: str = Field(default="minio", max_length=60)
    name: str = Field(min_length=1, max_length=160)
    endpoint: str = Field(min_length=1, max_length=300)
    region: str = Field(default="", max_length=120)
    bucket: str = Field(min_length=1, max_length=160)
    access_key_id: str = Field(default="", max_length=300)
    secret_access_key: str = Field(default="", max_length=500)
    path_style_enabled: bool = True
    tls_enabled: bool = True
    is_default: bool = False
    enabled: bool = True
    extra_config: dict[str, Any] = Field(default_factory=dict)
