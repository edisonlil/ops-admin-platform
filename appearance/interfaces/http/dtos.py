from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TenantAppearanceThemeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(default="当前租户主题")
    version: int = Field(default=1)
    preset_id: str = Field(default="default", alias="presetId")
    token_overrides: dict[str, Any] = Field(default_factory=dict, alias="tokenOverrides")
    layout_overrides: dict[str, Any] = Field(default_factory=dict, alias="layoutOverrides")
    project_overrides: dict[str, Any] = Field(default_factory=dict, alias="projectOverrides")
    skin_class: str = Field(default="", alias="skinClass")


class TenantThemeAssignmentRequest(BaseModel):
    theme_id: int | None = None


class PlatformBrandingRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    platform_name: str = Field(default="fg-agent", alias="platformName", max_length=80)
    logo_url: str = Field(default="", alias="logoUrl", max_length=4096)
    platform_name_font_size: int = Field(default=20, alias="platformNameFontSize", ge=12, le=32)
