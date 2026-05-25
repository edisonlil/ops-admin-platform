from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PageRequest(BaseModel):
    page_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    page_type: str = Field(default="dashboard", max_length=40)
    thumbnail_file_id: int | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class PageDraftRequest(BaseModel):
    schema_version: str = Field(default="1.0", max_length=40)
    layout: dict[str, Any] = Field(default_factory=dict)
    components: list[dict[str, Any]] = Field(default_factory=list)
    data_bindings: dict[str, Any] = Field(default_factory=dict)
    interactions: dict[str, Any] = Field(default_factory=dict)


class PageMenuMountRequest(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    menu_key: str | None = Field(default=None, max_length=120)
    parent_key: str | None = Field(default=None, max_length=120)
    path: str | None = Field(default=None, max_length=500)
    route_name: str | None = Field(default=None, max_length=120)
    icon: str | None = Field(default=None, max_length=120)
    permission_code: str | None = Field(default=None, max_length=200)
    sort_order: int = Field(default=869)
