from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResourceTypeRequest(BaseModel):
    code: str
    name: str
    owner_context: str = ""
    description: str = ""
    status: str = "active"


class FieldDefinitionRequest(BaseModel):
    resource_type_code: str
    field_key: str
    display_name: str
    value_type: str = "string"
    required: bool = False
    searchable: bool = True
    sort_order: int = 0
    status: str = "active"


class TagGroupRequest(BaseModel):
    code: str
    name: str
    description: str = ""
    sort_order: int = 0
    status: str = "active"


class TagRequest(BaseModel):
    group_id: int | None = None
    code: str
    name: str
    color: str = ""
    description: str = ""
    sort_order: int = 0
    status: str = "active"


class ResourceMetadataRequest(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
    tag_codes: list[str] = Field(default_factory=list)


class MetadataFilterRequest(BaseModel):
    field_key: str
    op: str = "eq"
    value: Any
    value_type: str | None = None


class ResourceSearchRequest(BaseModel):
    resource_type_code: str
    metadata_filters: list[MetadataFilterRequest] = Field(default_factory=list)
    tag_codes: list[str] = Field(default_factory=list)
    max_results: int = 2000
    start: int = 0
