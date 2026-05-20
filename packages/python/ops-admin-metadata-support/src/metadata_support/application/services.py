from __future__ import annotations

from typing import Any

from metadata_support.application.ports import MetadataSupportRepository
from metadata_support.domain.exceptions import MetadataSupportStorageNotReadyError, MetadataSupportValidationError
from metadata_support.domain.models import (
    MetadataFieldDefinition,
    MetadataResourceType,
    MetadataTag,
    MetadataTagGroup,
    RESOURCE_TYPE_FILE_OBJECT,
    STATUS_ACTIVE,
    STATUSES,
    VALUE_TYPE_BOOLEAN,
    VALUE_TYPE_DATETIME,
    VALUE_TYPE_NUMBER,
    VALUE_TYPE_STRING,
    VALUE_TYPES,
)


repository: MetadataSupportRepository | None = None


def configure_repository(metadata_repository: MetadataSupportRepository) -> None:
    global repository
    repository = metadata_repository


def repo() -> MetadataSupportRepository:
    if repository is None:
        raise MetadataSupportStorageNotReadyError("metadata support repository is not configured")
    return repository


def list_resource_types(*, page: int, page_size: int, keyword: str, status: str | None, current_user: dict[str, Any]) -> dict[str, Any]:
    items, total = repo().list_resource_types(
        tenant_id=current_tenant_id(current_user),
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=normalize_optional_status(status),
    )
    return {"items": [item.to_dict() for item in items], "pagination": {"page": page, "page_size": page_size, "total": total}}


def save_resource_type(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    normalized = {
        "id": int(payload.get("id") or 0),
        "code": normalize_resource_type_code(payload.get("code")),
        "name": str(payload.get("name") or "").strip(),
        "owner_context": str(payload.get("owner_context") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "status": normalize_status(payload.get("status")),
    }
    item = MetadataResourceType(id=int(normalized["id"]), tenant_id=tenant_id, create_time="", update_time="", **{k: v for k, v in normalized.items() if k != "id"})
    item.validate()
    saved = repo().save_resource_type(
        tenant_id=tenant_id,
        payload=normalized,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    return {"item": saved.to_dict()}


def list_field_definitions(
    *,
    resource_type_code: str,
    page: int,
    page_size: int,
    keyword: str,
    status: str | None,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    items, total = repo().list_field_definitions(
        tenant_id=current_tenant_id(current_user),
        resource_type_code=normalize_resource_type_code(resource_type_code),
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=normalize_optional_status(status),
    )
    return {"items": [item.to_dict() for item in items], "pagination": {"page": page, "page_size": page_size, "total": total}}


def save_field_definition(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    normalized = {
        "id": int(payload.get("id") or 0),
        "resource_type_code": normalize_resource_type_code(payload.get("resource_type_code")),
        "field_key": normalize_field_key(payload.get("field_key")),
        "display_name": str(payload.get("display_name") or "").strip(),
        "value_type": normalize_value_type(payload.get("value_type")),
        "required": bool(payload.get("required", False)),
        "searchable": bool(payload.get("searchable", True)),
        "sort_order": int(payload.get("sort_order") or 0),
        "status": normalize_status(payload.get("status")),
    }
    item = MetadataFieldDefinition(
        id=int(normalized["id"]),
        tenant_id=tenant_id,
        create_time="",
        update_time="",
        **{k: v for k, v in normalized.items() if k != "id"},
    )
    item.validate()
    saved = repo().save_field_definition(
        tenant_id=tenant_id,
        payload=normalized,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    return {"item": saved.to_dict()}


def list_tag_groups(*, page: int, page_size: int, keyword: str, status: str | None, current_user: dict[str, Any]) -> dict[str, Any]:
    items, total = repo().list_tag_groups(
        tenant_id=current_tenant_id(current_user),
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=normalize_optional_status(status),
    )
    return {"items": [item.to_dict() for item in items], "pagination": {"page": page, "page_size": page_size, "total": total}}


def save_tag_group(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    normalized = normalize_tag_group_payload(payload)
    item = MetadataTagGroup(id=int(normalized["id"]), tenant_id=tenant_id, create_time="", update_time="", **{k: v for k, v in normalized.items() if k != "id"})
    item.validate()
    saved = repo().save_tag_group(
        tenant_id=tenant_id,
        payload=normalized,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    return {"item": saved.to_dict()}


def list_tags(
    *, page: int, page_size: int, keyword: str, group_id: int | None, status: str | None, current_user: dict[str, Any]
) -> dict[str, Any]:
    items, total = repo().list_tags(
        tenant_id=current_tenant_id(current_user),
        page=page,
        page_size=page_size,
        keyword=keyword,
        group_id=group_id,
        status=normalize_optional_status(status),
    )
    return {"items": [item.to_dict() for item in items], "pagination": {"page": page, "page_size": page_size, "total": total}}


def save_tag(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    normalized = normalize_tag_payload(payload)
    item = MetadataTag(id=int(normalized["id"]), tenant_id=tenant_id, create_time="", update_time="", **{k: v for k, v in normalized.items() if k != "id"})
    item.validate()
    saved = repo().save_tag(
        tenant_id=tenant_id,
        payload=normalized,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    return {"item": saved.to_dict()}


def bind_resource_metadata(
    *,
    tenant_id: int,
    resource_type_code: str,
    resource_id: str | int,
    metadata: dict[str, Any],
    tag_codes: list[str] | None,
    actor: str,
    actor_id: int | None,
) -> dict[str, Any]:
    normalized_metadata = normalize_metadata(metadata)
    normalized_tags = normalize_tag_codes(tag_codes or [])
    item = repo().bind_resource(
        tenant_id=tenant_id,
        resource_type_code=normalize_resource_type_code(resource_type_code),
        resource_id=normalize_resource_id(resource_id),
        metadata=normalized_metadata,
        tag_codes=normalized_tags,
        actor=actor,
        actor_id=actor_id,
    )
    return {"item": item.to_dict(), "tag_codes": normalized_tags}


def get_resource_metadata(*, resource_type_code: str, resource_id: str | int, current_user: dict[str, Any]) -> dict[str, Any]:
    item, tags = repo().get_resource(
        tenant_id=current_tenant_id(current_user),
        resource_type_code=normalize_resource_type_code(resource_type_code),
        resource_id=normalize_resource_id(resource_id),
    )
    return {"item": item.to_dict() if item else None, "tags": [tag.to_dict() for tag in tags]}


def get_resource_tag_codes(*, tenant_id: int, resource_type_code: str, resource_id: str | int) -> list[str]:
    _, tags = repo().get_resource(
        tenant_id=tenant_id,
        resource_type_code=normalize_resource_type_code(resource_type_code),
        resource_id=normalize_resource_id(resource_id),
    )
    return [tag.code for tag in tags]


def search_resource_ids(
    *,
    tenant_id: int,
    resource_type_code: str,
    metadata_filters: list[dict[str, Any]] | None = None,
    tag_codes: list[str] | None = None,
    max_results: int = 2000,
    start: int = 0,
) -> dict[str, Any]:
    normalized_filters = [normalize_filter(item) for item in metadata_filters or []]
    normalized_tags = normalize_tag_codes(tag_codes or [])
    ids, total = repo().search_resource_ids(
        tenant_id=tenant_id,
        resource_type_code=normalize_resource_type_code(resource_type_code),
        metadata_filters=normalized_filters,
        tag_codes=normalized_tags,
        max_results=min(max(int(max_results or 100), 1), 5000),
        start=max(int(start or 0), 0),
    )
    return {"resource_ids": ids, "total": total}


def search_resources(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    result = search_resource_ids(
        tenant_id=current_tenant_id(current_user),
        resource_type_code=str(payload.get("resource_type_code") or RESOURCE_TYPE_FILE_OBJECT),
        metadata_filters=list(payload.get("metadata_filters") or []),
        tag_codes=list(payload.get("tag_codes") or []),
        max_results=int(payload.get("max_results") or 2000),
        start=int(payload.get("start") or 0),
    )
    return {"items": [{"resource_id": resource_id} for resource_id in result["resource_ids"]], "total": result["total"]}


def normalize_resource_type_code(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise MetadataSupportValidationError("resource_type_code is required")
    return text


def normalize_resource_id(value: str | int) -> str:
    text = str(value or "").strip()
    if not text:
        raise MetadataSupportValidationError("resource_id is required")
    return text


def normalize_field_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise MetadataSupportValidationError("field_key is required")
    return text


def normalize_value_type(value: Any) -> str:
    text = str(value or VALUE_TYPE_STRING).strip().lower()
    if text not in VALUE_TYPES:
        raise MetadataSupportValidationError(f"unsupported metadata value_type: {text}")
    return text


def normalize_status(value: Any) -> str:
    text = str(value or STATUS_ACTIVE).strip().lower()
    if text not in STATUSES:
        raise MetadataSupportValidationError(f"unsupported status: {text}")
    return text


def normalize_optional_status(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return normalize_status(value)


def normalize_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise MetadataSupportValidationError("metadata must be an object")
    return value


def normalize_tag_codes(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


def normalize_filter(item: dict[str, Any]) -> dict[str, Any]:
    field_key = normalize_field_key(item.get("field_key") or item.get("key"))
    op = str(item.get("op") or "eq").strip().lower()
    if op not in {"eq", "ne", "contains", "gt", "gte", "lt", "lte", "between"}:
        raise MetadataSupportValidationError(f"unsupported metadata filter op: {op}")
    value = item.get("value")
    value_type = str(item.get("value_type") or infer_value_type(value)).strip().lower()
    if value_type not in VALUE_TYPES:
        raise MetadataSupportValidationError(f"unsupported metadata filter value_type: {value_type}")
    return {"field_key": field_key, "op": op, "value": value, "value_type": value_type}


def infer_value_type(value: Any) -> str:
    if isinstance(value, bool):
        return VALUE_TYPE_BOOLEAN
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return VALUE_TYPE_NUMBER
    return VALUE_TYPE_STRING


def normalize_tag_group_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(payload.get("id") or 0),
        "code": str(payload.get("code") or "").strip(),
        "name": str(payload.get("name") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "sort_order": int(payload.get("sort_order") or 0),
        "status": normalize_status(payload.get("status")),
    }


def normalize_tag_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(payload.get("id") or 0),
        "group_id": int(payload.get("group_id") or 0) or None,
        "code": str(payload.get("code") or "").strip(),
        "name": str(payload.get("name") or "").strip(),
        "color": str(payload.get("color") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "sort_order": int(payload.get("sort_order") or 0),
        "status": normalize_status(payload.get("status")),
    }


def current_tenant_id(current_user: dict[str, Any]) -> int:
    tenant_id = current_user.get("tenant_id") or current_user.get("tenantId") or 1
    return int(tenant_id)


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or current_user.get("account") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    value = current_user.get("id") or current_user.get("user_id") or current_user.get("userId")
    return int(value) if value not in (None, "") else None
