from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from basic_data.domain.exceptions import BasicDataDomainError


STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUSES = {STATUS_ACTIVE, STATUS_DISABLED}


@dataclass(frozen=True)
class DictionaryType:
    id: int
    tenant_id: int
    code: str
    name: str
    category: str
    description: str
    status: str
    sort_order: int
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.tenant_id <= 0:
            raise BasicDataDomainError("tenant_id must be positive")
        if not self.code.strip():
            raise BasicDataDomainError("dictionary type code is required")
        if not self.name.strip():
            raise BasicDataDomainError("dictionary type name is required")
        if self.status not in STATUSES:
            raise BasicDataDomainError(f"unsupported dictionary type status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "status": self.status,
            "sort_order": self.sort_order,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class DictionaryItem:
    id: int
    tenant_id: int
    type_id: int
    type_code: str
    code: str
    value: str
    label: str
    color: str
    description: str
    extra: dict[str, Any]
    status: str
    sort_order: int
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.tenant_id <= 0:
            raise BasicDataDomainError("tenant_id must be positive")
        if self.type_id <= 0:
            raise BasicDataDomainError("dictionary item type_id must be positive")
        if not self.code.strip():
            raise BasicDataDomainError("dictionary item code is required")
        if not self.value.strip():
            raise BasicDataDomainError("dictionary item value is required")
        if not self.label.strip():
            raise BasicDataDomainError("dictionary item label is required")
        if self.status not in STATUSES:
            raise BasicDataDomainError(f"unsupported dictionary item status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "type_id": self.type_id,
            "type_code": self.type_code,
            "code": self.code,
            "value": self.value,
            "label": self.label,
            "color": self.color,
            "description": self.description,
            "extra": self.extra,
            "status": self.status,
            "sort_order": self.sort_order,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
