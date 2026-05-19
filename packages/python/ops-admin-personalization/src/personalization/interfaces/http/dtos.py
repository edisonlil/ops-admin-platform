from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TableColumnPreferenceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    visible_column_keys: list[str] = Field(default_factory=list, alias="visibleColumnKeys")
    column_order_keys: list[str] = Field(default_factory=list, alias="columnOrderKeys")
    settings: dict[str, Any] = Field(default_factory=dict)
