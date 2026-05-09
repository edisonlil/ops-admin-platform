from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


THEME_STATUS_PUBLISHED = "published"


@dataclass(frozen=True)
class AppearancePayload:
    version: int
    preset_id: str
    token_overrides: dict[str, Any] = field(default_factory=dict)
    layout_overrides: dict[str, Any] = field(default_factory=dict)
    project_overrides: dict[str, Any] = field(default_factory=dict)
    skin_class: str = ""

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "AppearancePayload":
        version = int(payload.get("version", 1) or 1)
        preset_id = str(payload.get("preset_id") or payload.get("presetId") or "default").strip() or "default"
        token_overrides = payload.get("token_overrides", payload.get("tokenOverrides", {}))
        layout_overrides = payload.get("layout_overrides", payload.get("layoutOverrides", {}))
        project_overrides = payload.get("project_overrides", payload.get("projectOverrides", {}))
        skin_class = str(payload.get("skin_class", payload.get("skinClass", "")) or "")
        if not isinstance(token_overrides, dict):
            token_overrides = {}
        if not isinstance(layout_overrides, dict):
            layout_overrides = {}
        if not isinstance(project_overrides, dict):
            project_overrides = {}
        return cls(
            version=version,
            preset_id=preset_id,
            token_overrides=dict(token_overrides),
            layout_overrides=dict(layout_overrides),
            project_overrides=dict(project_overrides),
            skin_class=skin_class,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "preset_id": self.preset_id,
            "presetId": self.preset_id,
            "token_overrides": self.token_overrides,
            "tokenOverrides": self.token_overrides,
            "layout_overrides": self.layout_overrides,
            "layoutOverrides": self.layout_overrides,
            "project_overrides": self.project_overrides,
            "projectOverrides": self.project_overrides,
            "skin_class": self.skin_class,
            "skinClass": self.skin_class,
        }


@dataclass(frozen=True)
class AppearanceTheme:
    id: int
    tenant_id: int
    name: str
    status: str
    version: int
    payload: AppearancePayload
    draft_payload: AppearancePayload
    creator: str
    editor: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "status": self.status,
            "version": self.version,
            "creator": self.creator,
            "editor": self.editor,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "draft": self.draft_payload.to_dict(),
            **self.payload.to_dict(),
        }
