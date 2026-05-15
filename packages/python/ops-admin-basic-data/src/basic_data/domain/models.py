from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from basic_data.domain.exceptions import BasicDataDomainError


STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUSES = {STATUS_ACTIVE, STATUS_DISABLED}
REGION_LEVEL_PROVINCE = "province"
REGION_LEVEL_CITY = "city"
REGION_LEVEL_DISTRICT = "district"
REGION_LEVELS = {REGION_LEVEL_PROVINCE, REGION_LEVEL_CITY, REGION_LEVEL_DISTRICT}
REGION_LEVEL_LABELS = {
    REGION_LEVEL_PROVINCE: "省",
    REGION_LEVEL_CITY: "市",
    REGION_LEVEL_DISTRICT: "区县",
}


@dataclass(frozen=True)
class DictionaryType:
    id: int
    tenant_id: int
    parent_id: int | None
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
            "parent_id": self.parent_id,
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
            "color": self.color,
            "description": self.description,
            "extra": self.extra,
            "status": self.status,
            "sort_order": self.sort_order,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class Region:
    id: int
    tenant_id: int
    parent_id: int | None
    parent_code: str
    code: str
    name: str
    short_name: str
    level: str
    path: str
    status: str
    sort_order: int
    extra: dict[str, Any]
    create_time: str
    update_time: str

    def validate(self) -> None:
        if self.tenant_id <= 0:
            raise BasicDataDomainError("tenant_id must be positive")
        if not self.code.strip():
            raise BasicDataDomainError("region code is required")
        if not self.name.strip():
            raise BasicDataDomainError("region name is required")
        if self.level not in REGION_LEVELS:
            raise BasicDataDomainError(f"unsupported region level: {self.level}")
        if self.status not in STATUSES:
            raise BasicDataDomainError(f"unsupported region status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "parent_id": self.parent_id,
            "parent_code": self.parent_code,
            "code": self.code,
            "name": self.name,
            "short_name": self.short_name,
            "level": self.level,
            "level_label": REGION_LEVEL_LABELS.get(self.level, self.level),
            "path": self.path,
            "status": self.status,
            "sort_order": self.sort_order,
            "extra": self.extra,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
