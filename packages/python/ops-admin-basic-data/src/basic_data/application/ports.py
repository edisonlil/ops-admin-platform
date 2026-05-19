from __future__ import annotations

from typing import Any, Protocol

from basic_data.domain.models import DictionaryItem, DictionaryType, Region
from system.application.data_access import DataAccessPredicate


class BasicDataRepository(Protocol):
    def list_dictionary_types(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        keyword: str,
        status: str | None,
        category: str,
        sort_by: str | None = None,
        sort_dir: str | None = None,
        data_scope: DataAccessPredicate | None = None,
    ) -> tuple[list[DictionaryType], int]: ...

    def get_dictionary_type(self, *, tenant_id: int, type_id: int) -> DictionaryType | None: ...

    def get_dictionary_type_row(self, *, tenant_id: int, type_id: int) -> dict[str, Any] | None: ...

    def get_dictionary_type_by_code(self, *, tenant_id: int, code: str) -> DictionaryType | None: ...

    def save_dictionary_type(
        self,
        *,
        tenant_id: int,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> DictionaryType: ...

    def delete_dictionary_type(
        self,
        *,
        tenant_id: int,
        type_id: int,
        actor: str,
        actor_id: int | None,
    ) -> DictionaryType | None: ...

    def list_dictionary_items(
        self,
        *,
        tenant_id: int,
        type_id: int,
        page: int,
        page_size: int,
        keyword: str,
        status: str | None,
        sort_by: str | None = None,
        sort_dir: str | None = None,
        data_scope: DataAccessPredicate | None = None,
    ) -> tuple[list[DictionaryItem], int]: ...

    def get_dictionary_item(self, *, tenant_id: int, item_id: int) -> DictionaryItem | None: ...

    def get_dictionary_item_row(self, *, tenant_id: int, item_id: int) -> dict[str, Any] | None: ...

    def save_dictionary_item(
        self,
        *,
        tenant_id: int,
        type_id: int,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> DictionaryItem: ...

    def delete_dictionary_item(
        self,
        *,
        tenant_id: int,
        item_id: int,
        actor: str,
        actor_id: int | None,
    ) -> DictionaryItem | None: ...

    def list_items_by_type_code(
        self,
        *,
        tenant_id: int,
        type_code: str,
        active_only: bool,
    ) -> list[DictionaryItem]: ...

    def list_regions(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        keyword: str,
        status: str | None,
        level: str | None,
        parent_id: int | None,
        sort_by: str | None = None,
        sort_dir: str | None = None,
        data_scope: DataAccessPredicate | None = None,
    ) -> tuple[list[Region], int]: ...

    def list_all_regions(self, *, tenant_id: int, include_disabled: bool = True) -> list[Region]: ...

    def get_region(self, *, tenant_id: int, region_id: int) -> Region | None: ...

    def get_region_row(self, *, tenant_id: int, region_id: int) -> dict[str, Any] | None: ...

    def get_region_by_code(self, *, tenant_id: int, code: str) -> Region | None: ...

    def save_region(
        self,
        *,
        tenant_id: int,
        payload: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> Region: ...

    def delete_region(
        self,
        *,
        tenant_id: int,
        region_id: int,
        actor: str,
        actor_id: int | None,
    ) -> Region | None: ...

    def list_region_children(
        self,
        *,
        tenant_id: int,
        parent_id: int | None,
        active_only: bool,
    ) -> list[Region]: ...
