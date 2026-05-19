from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TableColumnPreference:
    id: int
    tenant_id: int
    user_id: int
    view_key: str
    visible_column_keys: list[str] = field(default_factory=list)
    column_order_keys: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    create_time: str = ""
    update_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "view_key": self.view_key,
            "visible_column_keys": self.visible_column_keys,
            "column_order_keys": self.column_order_keys,
            "settings": self.settings,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
