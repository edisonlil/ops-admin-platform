from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from metadata_support.domain.exceptions import MetadataSupportValidationError


STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUSES = {STATUS_ACTIVE, STATUS_DISABLED}
RESOURCE_TYPE_FILE_OBJECT = "file_management.file_object"
VALUE_TYPE_STRING = "string"
VALUE_TYPE_NUMBER = "number"
VALUE_TYPE_DATETIME = "datetime"
VALUE_TYPE_BOOLEAN = "boolean"
VALUE_TYPES = {VALUE_TYPE_STRING, VALUE_TYPE_NUMBER, VALUE_TYPE_DATETIME, VALUE_TYPE_BOOLEAN}


@dataclass(frozen=True)
class MetadataResourceType:
    id: int
    tenant_id: int
    code: str
    name: str
    owner_context: str
    description: str
    status: str
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.tenant_id < 0:
            raise MetadataSupportValidationError("tenant_id must be non-negative")
        if not self.code.strip():
            raise MetadataSupportValidationError("resource type code is required")
        if not self.name.strip():
            raise MetadataSupportValidationError("resource type name is required")
        if self.status not in STATUSES:
            raise MetadataSupportValidationError(f"unsupported resource type status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "code": self.code,
            "name": self.name,
            "owner_context": self.owner_context,
            "description": self.description,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class MetadataFieldDefinition:
    id: int
    tenant_id: int
    resource_type_code: str
    field_key: str
    display_name: str
    value_type: str
    required: bool
    searchable: bool
    sort_order: int
    status: str
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.tenant_id < 0:
            raise MetadataSupportValidationError("tenant_id must be non-negative")
        if not self.resource_type_code.strip():
            raise MetadataSupportValidationError("resource_type_code is required")
        if not self.field_key.strip():
            raise MetadataSupportValidationError("field_key is required")
        if not self.display_name.strip():
            raise MetadataSupportValidationError("display_name is required")
        if self.value_type not in VALUE_TYPES:
            raise MetadataSupportValidationError(f"unsupported metadata value_type: {self.value_type}")
        if self.status not in STATUSES:
            raise MetadataSupportValidationError(f"unsupported field status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "resource_type_code": self.resource_type_code,
            "field_key": self.field_key,
            "display_name": self.display_name,
            "value_type": self.value_type,
            "required": self.required,
            "searchable": self.searchable,
            "sort_order": self.sort_order,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class MetadataTagGroup:
    id: int
    tenant_id: int
    code: str
    name: str
    description: str
    sort_order: int
    status: str
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.tenant_id < 0:
            raise MetadataSupportValidationError("tenant_id must be non-negative")
        if not self.code.strip():
            raise MetadataSupportValidationError("tag group code is required")
        if not self.name.strip():
            raise MetadataSupportValidationError("tag group name is required")
        if self.status not in STATUSES:
            raise MetadataSupportValidationError(f"unsupported tag group status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "sort_order": self.sort_order,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class MetadataTag:
    id: int
    tenant_id: int
    group_id: int | None
    code: str
    name: str
    color: str
    description: str
    sort_order: int
    status: str
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.tenant_id < 0:
            raise MetadataSupportValidationError("tenant_id must be non-negative")
        if not self.code.strip():
            raise MetadataSupportValidationError("tag code is required")
        if not self.name.strip():
            raise MetadataSupportValidationError("tag name is required")
        if self.status not in STATUSES:
            raise MetadataSupportValidationError(f"unsupported tag status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "group_id": self.group_id,
            "code": self.code,
            "name": self.name,
            "color": self.color,
            "description": self.description,
            "sort_order": self.sort_order,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class ResourceMetadata:
    id: int
    tenant_id: int
    resource_type_code: str
    resource_id: str
    metadata: dict[str, Any]
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "resource_type_code": self.resource_type_code,
            "resource_id": self.resource_id,
            "metadata": self.metadata,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
