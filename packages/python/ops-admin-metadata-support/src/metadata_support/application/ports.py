from __future__ import annotations

from typing import Any, Protocol

from metadata_support.domain.models import MetadataFieldDefinition, MetadataResourceType, MetadataTag, MetadataTagGroup, ResourceMetadata


class MetadataSupportRepository(Protocol):
    def list_resource_types(self, *, tenant_id: int, page: int, page_size: int, keyword: str, status: str | None) -> tuple[list[MetadataResourceType], int]:
        ...

    def save_resource_type(self, *, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MetadataResourceType:
        ...

    def list_field_definitions(
        self, *, tenant_id: int, resource_type_code: str, page: int, page_size: int, keyword: str, status: str | None
    ) -> tuple[list[MetadataFieldDefinition], int]:
        ...

    def save_field_definition(self, *, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MetadataFieldDefinition:
        ...

    def list_tag_groups(self, *, tenant_id: int, page: int, page_size: int, keyword: str, status: str | None) -> tuple[list[MetadataTagGroup], int]:
        ...

    def save_tag_group(self, *, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MetadataTagGroup:
        ...

    def list_tags(
        self, *, tenant_id: int, page: int, page_size: int, keyword: str, group_id: int | None, status: str | None
    ) -> tuple[list[MetadataTag], int]:
        ...

    def save_tag(self, *, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> MetadataTag:
        ...

    def ensure_tag(self, *, tenant_id: int, code: str, actor: str, actor_id: int | None) -> MetadataTag:
        ...

    def bind_resource(
        self,
        *,
        tenant_id: int,
        resource_type_code: str,
        resource_id: str,
        metadata: dict[str, Any],
        tag_codes: list[str],
        actor: str,
        actor_id: int | None,
    ) -> ResourceMetadata:
        ...

    def get_resource(self, *, tenant_id: int, resource_type_code: str, resource_id: str) -> tuple[ResourceMetadata | None, list[MetadataTag]]:
        ...

    def search_resource_ids(
        self,
        *,
        tenant_id: int,
        resource_type_code: str,
        metadata_filters: list[dict[str, Any]],
        tag_codes: list[str],
        max_results: int,
        start: int,
    ) -> tuple[list[str], int]:
        ...
