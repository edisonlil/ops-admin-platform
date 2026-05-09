from __future__ import annotations

from dataclasses import dataclass


DEFAULT_PLATFORM_NAME = "fg-agent"
DEFAULT_PLATFORM_NAME_FONT_SIZE = 20
MIN_PLATFORM_NAME_FONT_SIZE = 12
MAX_PLATFORM_NAME_FONT_SIZE = 32


@dataclass(frozen=True)
class PlatformBranding:
    platform_name: str
    logo_url: str
    platform_name_font_size: int
    editor: str
    update_time: str

    @classmethod
    def from_values(
        cls,
        *,
        platform_name: str | None,
        logo_url: str | None,
        platform_name_font_size: int | str | None = DEFAULT_PLATFORM_NAME_FONT_SIZE,
        editor: str = "",
        update_time: str = "",
    ) -> "PlatformBranding":
        name = str(platform_name or DEFAULT_PLATFORM_NAME).strip() or DEFAULT_PLATFORM_NAME
        logo = str(logo_url or "").strip()
        try:
            font_size = int(platform_name_font_size or DEFAULT_PLATFORM_NAME_FONT_SIZE)
        except (TypeError, ValueError):
            font_size = DEFAULT_PLATFORM_NAME_FONT_SIZE
        font_size = max(MIN_PLATFORM_NAME_FONT_SIZE, min(MAX_PLATFORM_NAME_FONT_SIZE, font_size))
        return cls(
            platform_name=name,
            logo_url=logo,
            platform_name_font_size=font_size,
            editor=editor,
            update_time=update_time,
        )

    def to_dict(self) -> dict[str, str | int]:
        return {
            "platform_name": self.platform_name,
            "platformName": self.platform_name,
            "logo_url": self.logo_url,
            "logoUrl": self.logo_url,
            "platform_name_font_size": self.platform_name_font_size,
            "platformNameFontSize": self.platform_name_font_size,
            "editor": self.editor,
            "update_time": self.update_time,
        }
