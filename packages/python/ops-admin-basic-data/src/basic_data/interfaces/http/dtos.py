from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DictionaryTypeRequest(BaseModel):
    id: int | None = None
    parent_id: int | None = None
    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="general", max_length=120)
    description: str = Field(default="", max_length=1000)
    status: str = Field(default="active", max_length=40)
    sort_order: int = Field(default=0)


class DictionaryItemRequest(BaseModel):
    id: int | None = None
    code: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=300)
    color: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=1000)
    extra: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="active", max_length=40)
    sort_order: int = Field(default=0)


class RegionRequest(BaseModel):
    id: int | None = None
    parent_id: int | None = None
    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    short_name: str = Field(default="", max_length=200)
    level: str = Field(min_length=1, max_length=40)
    status: str = Field(default="active", max_length=40)
    sort_order: int = Field(default=0)
    extra: dict[str, Any] = Field(default_factory=dict)
