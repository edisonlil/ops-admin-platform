from __future__ import annotations

from typing import Any, Protocol

from datasets.domain.models import Dataset, DatasetField, DatasetVersion
from system.application.data_access import DataAccessPredicate


class DatasetRepository(Protocol):
    def list_datasets(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        keyword: str = "",
        status: str | None = None,
        dataset_type: str = "",
        sort_by: str | None = None,
        sort_dir: str | None = None,
        data_scope: DataAccessPredicate | None = None,
    ) -> tuple[list[Dataset], int]:
        ...

    def get_dataset(self, *, tenant_id: int, dataset_id: int) -> Dataset | None:
        ...

    def get_dataset_row(self, *, tenant_id: int, dataset_id: int) -> dict[str, Any] | None:
        ...

    def get_dataset_by_key(self, *, tenant_id: int, key: str) -> Dataset | None:
        ...

    def save_dataset(self, *, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> Dataset:
        ...

    def delete_dataset(self, *, tenant_id: int, dataset_id: int, actor: str, actor_id: int | None) -> Dataset | None:
        ...

    def list_fields(self, *, tenant_id: int, dataset_id: int) -> list[DatasetField]:
        ...

    def replace_fields(self, *, tenant_id: int, dataset_id: int, fields: list[dict[str, Any]], actor: str, actor_id: int | None) -> list[DatasetField]:
        ...

    def replace_manual_rows(self, *, tenant_id: int, dataset_id: int, rows: list[dict[str, Any]], actor: str, actor_id: int | None) -> int:
        ...

    def list_manual_rows(self, *, tenant_id: int, dataset_id: int, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
        ...

    def publish_dataset(
        self,
        *,
        tenant_id: int,
        dataset_id: int,
        schema: dict[str, Any],
        query_config: dict[str, Any],
        sample_rows: list[dict[str, Any]],
        actor: str,
        actor_id: int | None,
    ) -> DatasetVersion:
        ...


class ExternalDatasetExecutorPort(Protocol):
    def execute_preview(
        self,
        *,
        dataset: Dataset,
        fields: list[DatasetField],
        page: int,
        page_size: int,
        variables: dict[str, Any],
        current_user: dict[str, Any],
        apply_data_access: bool = True,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        ...


class SourceSchemaInspectorPort(Protocol):
    def inspect_source_schema(self) -> dict[str, Any]:
        ...
