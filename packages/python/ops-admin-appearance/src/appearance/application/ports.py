from __future__ import annotations

from typing import Protocol

from appearance.domain.branding import PlatformBranding
from appearance.domain.theme import AppearancePayload, AppearanceTheme


class AppearanceRepository(Protocol):
    def list_themes(self) -> list[AppearanceTheme]: ...

    def get_theme(self, theme_id: int) -> AppearanceTheme | None: ...

    def get_platform_branding(self) -> PlatformBranding: ...

    def save_platform_branding(
        self,
        *,
        platform_name: str,
        logo_url: str,
        platform_name_font_size: int,
        actor: str,
    ) -> PlatformBranding: ...

    def create_theme(self, *, name: str, payload: AppearancePayload, actor: str) -> AppearanceTheme: ...

    def update_theme(
        self,
        *,
        theme_id: int,
        name: str,
        payload: AppearancePayload,
        actor: str,
    ) -> AppearanceTheme | None: ...

    def publish_theme(self, *, theme_id: int, actor: str) -> AppearanceTheme | None: ...

    def disable_theme(self, *, theme_id: int, actor: str) -> AppearanceTheme | None: ...

    def assign_platform_default_theme(self, *, theme_id: int, actor: str) -> AppearanceTheme | None: ...

    def get_tenant_assigned_theme(self, tenant_id: int) -> AppearanceTheme | None: ...

    def assign_theme_to_tenant(
        self,
        *,
        tenant_id: int,
        theme_id: int | None,
        actor: str,
    ) -> AppearanceTheme | None: ...

    def get_effective_tenant_theme(self, tenant_id: int) -> AppearanceTheme | None: ...

    def save_published_tenant_theme(
        self,
        *,
        tenant_id: int,
        name: str,
        payload: AppearancePayload,
        actor: str,
    ) -> AppearanceTheme: ...
