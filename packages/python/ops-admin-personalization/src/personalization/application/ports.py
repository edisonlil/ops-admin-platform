from __future__ import annotations

from typing import Any, Protocol

from personalization.domain.models import TableColumnPreference


class PersonalizationRepository(Protocol):
    def get_table_column_preference(
        self,
        *,
        tenant_id: int,
        user_id: int,
        view_key: str,
    ) -> TableColumnPreference | None: ...

    def save_table_column_preference(
        self,
        *,
        tenant_id: int,
        user_id: int,
        view_key: str,
        visible_column_keys: list[str],
        column_order_keys: list[str],
        settings: dict[str, Any],
        actor: str,
        actor_id: int | None,
    ) -> TableColumnPreference: ...

    def delete_table_column_preference(
        self,
        *,
        tenant_id: int,
        user_id: int,
        view_key: str,
        actor: str,
        actor_id: int | None,
    ) -> None: ...
