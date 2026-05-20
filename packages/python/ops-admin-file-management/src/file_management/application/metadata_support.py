from __future__ import annotations

from typing import Any

from file_management.application.ports import MetadataBindingPort


class NoopMetadataBinding:
    def bind_resource(
        self,
        *,
        tenant_id: int,
        resource_type_code: str,
        resource_id: str | int,
        metadata: dict[str, Any],
        tag_codes: list[str],
        actor: str,
        actor_id: int | None,
    ) -> None:
        return None

    def search_resource_ids(
        self,
        *,
        tenant_id: int,
        resource_type_code: str,
        metadata_filters: list[dict[str, Any]],
        tag_codes: list[str],
        max_results: int,
        offset: int,
    ) -> tuple[list[int], int]:
        return [], 0

    def resource_tag_codes(self, *, tenant_id: int, resource_type_code: str, resource_id: str | int) -> list[str]:
        return []


class OptionalMetadataSupportBinding:
    def bind_resource(
        self,
        *,
        tenant_id: int,
        resource_type_code: str,
        resource_id: str | int,
        metadata: dict[str, Any],
        tag_codes: list[str],
        actor: str,
        actor_id: int | None,
    ) -> None:
        try:
            from metadata_support.application import services as metadata_services
        except ImportError:
            return
        try:
            metadata_services.bind_resource_metadata(
                tenant_id=tenant_id,
                resource_type_code=resource_type_code,
                resource_id=resource_id,
                metadata=metadata,
                tag_codes=tag_codes,
                actor=actor,
                actor_id=actor_id,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "MetadataSupportStorageNotReadyError":
                return
            raise

    def search_resource_ids(
        self,
        *,
        tenant_id: int,
        resource_type_code: str,
        metadata_filters: list[dict[str, Any]],
        tag_codes: list[str],
        max_results: int,
        offset: int,
    ) -> tuple[list[int], int]:
        try:
            from metadata_support.application import services as metadata_services
        except ImportError:
            return [], 0
        result = metadata_services.search_resource_ids(
            tenant_id=tenant_id,
            resource_type_code=resource_type_code,
            metadata_filters=metadata_filters,
            tag_codes=tag_codes,
            max_results=max_results,
            start=offset,
        )
        ids: list[int] = []
        for value in result["resource_ids"]:
            try:
                ids.append(int(value))
            except (TypeError, ValueError):
                continue
        return ids, int(result["total"])

    def resource_tag_codes(self, *, tenant_id: int, resource_type_code: str, resource_id: str | int) -> list[str]:
        try:
            from metadata_support.application import services as metadata_services
        except ImportError:
            return []
        try:
            return metadata_services.get_resource_tag_codes(
                tenant_id=tenant_id,
                resource_type_code=resource_type_code,
                resource_id=resource_id,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "MetadataSupportStorageNotReadyError":
                return []
            raise


def default_metadata_binding() -> MetadataBindingPort:
    return OptionalMetadataSupportBinding()
