from __future__ import annotations

from typing import Any, Protocol

from page_designer.domain.models import PageDefinition, PageVersion


class PageDesignerRepository(Protocol):
    def list_pages(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        keyword: str = "",
        page_type: str | None = None,
        status: str | None = None,
    ) -> tuple[list[PageDefinition], int]:
        ...

    def get_page(self, *, tenant_id: int, page_id: int) -> PageDefinition | None:
        ...

    def get_page_by_key(self, *, tenant_id: int, page_key: str) -> PageDefinition | None:
        ...

    def create_page(self, *, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> PageDefinition:
        ...

    def update_page(self, *, tenant_id: int, page_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> PageDefinition:
        ...

    def delete_page(self, *, tenant_id: int, page_id: int, actor: str, actor_id: int | None) -> PageDefinition | None:
        ...

    def save_draft_version(self, *, tenant_id: int, page_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> PageVersion:
        ...

    def get_version(self, *, tenant_id: int, version_id: int) -> PageVersion | None:
        ...

    def latest_version(self, *, tenant_id: int, page_id: int, status: str | None = None) -> PageVersion | None:
        ...

    def publish_page(self, *, tenant_id: int, page_id: int, version_id: int, actor: str, actor_id: int | None) -> PageDefinition:
        ...

    def unpublish_page(self, *, tenant_id: int, page_id: int, actor: str, actor_id: int | None) -> PageDefinition:
        ...

    def save_menu_mount(self, *, tenant_id: int, page_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> dict[str, Any]:
        ...

    def delete_menu_mount(self, *, tenant_id: int, page_id: int, actor: str, actor_id: int | None) -> dict[str, Any] | None:
        ...


class MenuMountPort(Protocol):
    def upsert_page_menu(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def delete_page_menu(self, menu_key: str) -> dict[str, Any] | None:
        ...
