from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DatasetRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    dataset_type: str = "manual"
    status: str = "draft"
    visibility: str = "platform"
    query_config: dict[str, Any] = Field(default_factory=dict)


class DatasetFieldRequest(BaseModel):
    field_key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    data_type: str = "text"
    semantic_type: str = ""
    unit: str = ""
    precision: int | None = None
    nullable: bool = True
    visible: bool = True
    sort_order: int = 0
    expression: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class DatasetFieldsRequest(BaseModel):
    fields: list[DatasetFieldRequest] = Field(default_factory=list)


class DatasetRowsRequest(BaseModel):
    rows: list[Any] = Field(default_factory=list)


class DatasetPreviewRequest(BaseModel):
    variables: dict[str, Any] = Field(default_factory=dict)


class DatasetQueryExecuteRequest(BaseModel):
    query_config: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
