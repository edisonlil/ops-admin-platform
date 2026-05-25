from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datasets.domain.exceptions import DatasetDomainError


DATASET_TYPE_MANUAL = "manual"
DATASET_TYPE_API_CONTRACT = "api_contract"
DATASET_TYPE_SOURCE_QUERY = "source_query"
DATASET_TYPES = {DATASET_TYPE_MANUAL, DATASET_TYPE_API_CONTRACT, DATASET_TYPE_SOURCE_QUERY}

STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
DATASET_STATUSES = {STATUS_DRAFT, STATUS_ACTIVE, STATUS_DISABLED}

VERSION_STATUS_PUBLISHED = "published"

FIELD_TYPE_TEXT = "text"
FIELD_TYPE_NUMBER = "number"
FIELD_TYPE_INTEGER = "integer"
FIELD_TYPE_BOOLEAN = "boolean"
FIELD_TYPE_DATE = "date"
FIELD_TYPE_DATETIME = "datetime"
FIELD_TYPES = {
    FIELD_TYPE_TEXT,
    FIELD_TYPE_NUMBER,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_BOOLEAN,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DATETIME,
}


@dataclass(slots=True)
class DatasetField:
    id: int
    tenant_id: int
    dataset_id: int
    field_key: str
    label: str
    data_type: str = FIELD_TYPE_TEXT
    semantic_type: str = ""
    unit: str = ""
    precision: int | None = None
    nullable: bool = True
    visible: bool = True
    sort_order: int = 0
    expression: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    create_time: str = ""
    update_time: str = ""

    def validate(self) -> None:
        if not self.field_key.strip():
            raise DatasetDomainError("field_key is required")
        if not self.label.strip():
            raise DatasetDomainError("field label is required")
        if self.data_type not in FIELD_TYPES:
            raise DatasetDomainError(f"unsupported field data_type: {self.data_type}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "dataset_id": self.dataset_id,
            "field_key": self.field_key,
            "label": self.label,
            "data_type": self.data_type,
            "semantic_type": self.semantic_type,
            "unit": self.unit,
            "precision": self.precision,
            "nullable": self.nullable,
            "visible": self.visible,
            "sort_order": self.sort_order,
            "expression": self.expression,
            "config": self.config,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(slots=True)
class Dataset:
    id: int
    tenant_id: int
    key: str
    name: str
    description: str = ""
    dataset_type: str = DATASET_TYPE_MANUAL
    status: str = STATUS_DRAFT
    visibility: str = "tenant"
    owner_user_id: int | None = None
    owner_department_id: int | None = None
    published_version_id: int | None = None
    field_count: int = 0
    row_count: int = 0
    create_time: str = ""
    update_time: str = ""

    def validate(self) -> None:
        if not self.key.strip():
            raise DatasetDomainError("dataset key is required")
        if not self.name.strip():
            raise DatasetDomainError("dataset name is required")
        if self.dataset_type not in DATASET_TYPES:
            raise DatasetDomainError(f"unsupported dataset_type: {self.dataset_type}")
        if self.status not in DATASET_STATUSES:
            raise DatasetDomainError(f"unsupported dataset status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "dataset_type": self.dataset_type,
            "status": self.status,
            "visibility": self.visibility,
            "owner_user_id": self.owner_user_id,
            "owner_department_id": self.owner_department_id,
            "published_version_id": self.published_version_id,
            "field_count": self.field_count,
            "row_count": self.row_count,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(slots=True)
class DatasetVersion:
    id: int
    tenant_id: int
    dataset_id: int
    version_no: int
    status: str
    schema: dict[str, Any]
    query_config: dict[str, Any]
    sample_rows: list[dict[str, Any]]
    published_time: str | None = None
    create_time: str = ""
    update_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "dataset_id": self.dataset_id,
            "version_no": self.version_no,
            "status": self.status,
            "schema": self.schema,
            "query_config": self.query_config,
            "sample_rows": self.sample_rows,
            "published_time": self.published_time,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
