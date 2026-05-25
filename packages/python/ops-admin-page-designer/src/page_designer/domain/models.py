from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from page_designer.domain.exceptions import PageDesignerDomainError


PAGE_TYPE_DASHBOARD = "dashboard"
SUPPORTED_PAGE_TYPES = {PAGE_TYPE_DASHBOARD}
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_DISABLED = "disabled"
SUPPORTED_STATUSES = {STATUS_DRAFT, STATUS_PUBLISHED, STATUS_DISABLED}
DEFAULT_SCHEMA_VERSION = "1.0"


@dataclass(slots=True)
class PageDefinition:
    id: int
    tenant_id: int
    page_key: str
    name: str
    description: str
    page_type: str = PAGE_TYPE_DASHBOARD
    status: str = STATUS_DRAFT
    current_version_id: int | None = None
    thumbnail_file_id: int | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    menu_mounted: bool = False
    menu_key: str = ""
    create_time: str = ""
    update_time: str = ""

    def validate(self) -> None:
        validate_key(self.page_key, "page_key")
        if not self.name.strip():
            raise PageDesignerDomainError("页面名称不能为空")
        if self.page_type not in SUPPORTED_PAGE_TYPES:
            raise PageDesignerDomainError(f"不支持的页面类型: {self.page_type}")
        if self.status not in SUPPORTED_STATUSES:
            raise PageDesignerDomainError(f"不支持的页面状态: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "page_key": self.page_key,
            "name": self.name,
            "description": self.description,
            "page_type": self.page_type,
            "status": self.status,
            "current_version_id": self.current_version_id,
            "thumbnail_file_id": self.thumbnail_file_id,
            "settings": self.settings,
            "menu_mounted": self.menu_mounted,
            "menu_key": self.menu_key,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(slots=True)
class PageVersion:
    id: int
    tenant_id: int
    page_id: int
    version_no: int
    schema_version: str
    layout: dict[str, Any] = field(default_factory=dict)
    components: list[dict[str, Any]] = field(default_factory=list)
    data_bindings: dict[str, Any] = field(default_factory=dict)
    interactions: dict[str, Any] = field(default_factory=dict)
    status: str = STATUS_DRAFT
    create_time: str = ""
    update_time: str = ""

    def validate(self, page_type: str = PAGE_TYPE_DASHBOARD) -> None:
        if page_type not in SUPPORTED_PAGE_TYPES:
            raise PageDesignerDomainError(f"不支持的页面类型: {page_type}")
        if self.status not in SUPPORTED_STATUSES:
            raise PageDesignerDomainError(f"不支持的页面版本状态: {self.status}")
        if not self.schema_version.strip():
            raise PageDesignerDomainError("schema_version 不能为空")
        validate_dashboard_layout(self.layout, self.components)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "page_id": self.page_id,
            "version_no": self.version_no,
            "schema_version": self.schema_version,
            "layout": self.layout,
            "components": self.components,
            "data_bindings": self.data_bindings,
            "interactions": self.interactions,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


def validate_key(value: str, field_name: str) -> None:
    normalized = value.strip()
    if not normalized:
        raise PageDesignerDomainError(f"{field_name} 不能为空")
    if len(normalized) > 120:
        raise PageDesignerDomainError(f"{field_name} 不能超过 120 个字符")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if any(char not in allowed for char in normalized):
        raise PageDesignerDomainError(f"{field_name} 只能包含字母、数字、下划线和短横线")


def validate_dashboard_layout(layout: dict[str, Any], components: list[dict[str, Any]]) -> None:
    if not isinstance(layout, dict):
        raise PageDesignerDomainError("布局配置必须是对象")
    cols = int(layout.get("cols") or 24)
    if cols < 1 or cols > 48:
        raise PageDesignerDomainError("布局列数必须在 1 到 48 之间")
    row_height = int(layout.get("rowHeight") or layout.get("row_height") or 64)
    if row_height < 24 or row_height > 240:
        raise PageDesignerDomainError("布局行高必须在 24 到 240 之间")
    items = layout.get("items") or []
    if not isinstance(items, list):
        raise PageDesignerDomainError("布局 items 必须是数组")
    component_ids = {str(item.get("id") or "") for item in components if isinstance(item, dict)}
    layout_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise PageDesignerDomainError("布局项必须是对象")
        item_id = str(item.get("id") or "").strip()
        validate_key(item_id, "布局项 id")
        if item_id in layout_ids:
            raise PageDesignerDomainError(f"布局项 id 重复: {item_id}")
        layout_ids.add(item_id)
        x = int(item.get("x") or 0)
        y = int(item.get("y") or 0)
        w = int(item.get("w") or 1)
        h = int(item.get("h") or 1)
        if x < 0 or y < 0 or w < 1 or h < 1 or x + w > cols:
            raise PageDesignerDomainError(f"布局项位置不合法: {item_id}")
    for component in components:
        if not isinstance(component, dict):
            raise PageDesignerDomainError("组件配置必须是对象")
        component_id = str(component.get("id") or "").strip()
        validate_key(component_id, "组件 id")
        component_type = str(component.get("type") or "").strip()
        validate_key(component_type, "组件类型")
    if component_ids and not layout_ids.issuperset(component_ids):
        missing = ", ".join(sorted(component_ids - layout_ids))
        raise PageDesignerDomainError(f"组件缺少布局项: {missing}")


def default_dashboard_layout() -> dict[str, Any]:
    return {"cols": 24, "rowHeight": 64, "items": []}
