from __future__ import annotations

import csv
import io
import json
from typing import Any

from basic_data.application.ports import BasicDataRepository
from basic_data.domain.exceptions import BasicDataDomainError, BasicDataNotFoundError, BasicDataStorageNotReadyError
from basic_data.domain.models import (
    DictionaryItem,
    DictionaryType,
    Region,
    REGION_LEVEL_CITY,
    REGION_LEVEL_DISTRICT,
    REGION_LEVEL_PROVINCE,
    REGION_LEVELS,
    STATUS_ACTIVE,
)
from system.application.data_access import ResourceDescriptor, data_access_for, data_owner_fields, ensure_data_access_record
from system.application.sorting import InvalidSortError


repository: BasicDataRepository | None = None
DICTIONARY_RESOURCE = ResourceDescriptor(resource_key="basic-data.dictionary")
REGION_RESOURCE = ResourceDescriptor(resource_key="basic-data.region")
REGION_LEVEL_ALIASES = {
    "province": REGION_LEVEL_PROVINCE,
    "省": REGION_LEVEL_PROVINCE,
    "省份": REGION_LEVEL_PROVINCE,
    "city": REGION_LEVEL_CITY,
    "市": REGION_LEVEL_CITY,
    "城市": REGION_LEVEL_CITY,
    "district": REGION_LEVEL_DISTRICT,
    "区": REGION_LEVEL_DISTRICT,
    "区县": REGION_LEVEL_DISTRICT,
    "县": REGION_LEVEL_DISTRICT,
}


def configure_repository(basic_data_repository: BasicDataRepository) -> None:
    global repository
    repository = basic_data_repository


def repo() -> BasicDataRepository:
    if repository is None:
        raise BasicDataStorageNotReadyError("basic data repository is not configured")
    return repository


def list_dictionary_types(
    *,
    page: int,
    page_size: int,
    keyword: str,
    status: str | None,
    category: str,
    current_user: dict[str, Any],
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    try:
        items, total = repo().list_dictionary_types(
            tenant_id=current_tenant_id(current_user),
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            category=category,
            sort_by=sort_by,
            sort_dir=sort_dir,
            data_scope=data_access_for(current_user, DICTIONARY_RESOURCE).read(),
        )
    except InvalidSortError as exc:
        raise BasicDataDomainError(str(exc)) from exc
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def save_dictionary_type(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    normalized = normalize_type_payload(payload)
    type_id = int(normalized.get("id") or 0)
    if type_id:
        ensure_record_access(
            tenant_id=tenant_id,
            row=repo().get_dictionary_type_row(tenant_id=tenant_id, type_id=type_id),
            current_user=current_user,
            resource=DICTIONARY_RESOURCE,
            action="write",
            not_found_message="dictionary type not found",
        )
    normalized.update(data_owner_fields(current_user))
    ensure_unique_type_code(tenant_id=tenant_id, type_id=type_id, code=str(normalized.get("code") or ""))
    ensure_valid_type_parent(tenant_id=tenant_id, type_id=type_id, parent_id=normalized.get("parent_id"))
    dictionary_type = DictionaryType(id=type_id, tenant_id=tenant_id, create_time="", update_time="", **normalized_type_fields(normalized))
    dictionary_type.validate()
    try:
        item = repo().save_dictionary_type(
            tenant_id=tenant_id,
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except InvalidSortError as exc:
        raise BasicDataDomainError(str(exc)) from exc
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {"item": item.to_dict()}


def delete_dictionary_type(*, type_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    ensure_record_access(
        tenant_id=tenant_id,
        row=repo().get_dictionary_type_row(tenant_id=tenant_id, type_id=type_id),
        current_user=current_user,
        resource=DICTIONARY_RESOURCE,
        action="manage",
        not_found_message="dictionary type not found",
    )
    try:
        item = repo().delete_dictionary_type(
            tenant_id=tenant_id,
            type_id=type_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except InvalidSortError as exc:
        raise BasicDataDomainError(str(exc)) from exc
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    if not item:
        raise BasicDataNotFoundError("dictionary type not found")
    return {"id": item.id, "deleted": True}


def list_dictionary_items(
    *,
    type_id: int,
    page: int,
    page_size: int,
    keyword: str,
    status: str | None,
    current_user: dict[str, Any],
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    ensure_dictionary_type_exists(tenant_id=tenant_id, type_id=type_id)
    try:
        items, total = repo().list_dictionary_items(
            tenant_id=tenant_id,
            type_id=type_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            data_scope=data_access_for(current_user, DICTIONARY_RESOURCE).read(),
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def save_dictionary_item(type_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    ensure_dictionary_type_exists(tenant_id=tenant_id, type_id=type_id)
    normalized = normalize_item_payload(payload)
    normalized.update(data_owner_fields(current_user))
    item = DictionaryItem(
        id=int(normalized.get("id") or 0),
        tenant_id=tenant_id,
        type_id=type_id,
        type_code="",
        create_time="",
        update_time="",
        **normalized_item_fields(normalized),
    )
    item.validate()
    try:
        saved = repo().save_dictionary_item(
            tenant_id=tenant_id,
            type_id=type_id,
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {"item": saved.to_dict()}


def update_dictionary_item(item_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        existing = repo().get_dictionary_item(tenant_id=tenant_id, item_id=item_id)
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    if not existing:
        raise BasicDataNotFoundError("dictionary item not found")
    ensure_record_access(
        tenant_id=tenant_id,
        row=repo().get_dictionary_item_row(tenant_id=tenant_id, item_id=item_id),
        current_user=current_user,
        resource=DICTIONARY_RESOURCE,
        action="write",
        not_found_message="dictionary item not found",
    )
    data = {**payload, "id": item_id}
    return save_dictionary_item(existing.type_id, data, current_user)


def delete_dictionary_item(*, item_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    ensure_record_access(
        tenant_id=tenant_id,
        row=repo().get_dictionary_item_row(tenant_id=tenant_id, item_id=item_id),
        current_user=current_user,
        resource=DICTIONARY_RESOURCE,
        action="manage",
        not_found_message="dictionary item not found",
    )
    try:
        item = repo().delete_dictionary_item(
            tenant_id=tenant_id,
            item_id=item_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    if not item:
        raise BasicDataNotFoundError("dictionary item not found")
    return {"id": item.id, "deleted": True}


def list_items_by_type_code(*, type_code: str, active_only: bool, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        items = repo().list_items_by_type_code(
            tenant_id=current_tenant_id(current_user),
            type_code=type_code.strip(),
            active_only=active_only,
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {"items": [item.to_dict() for item in items]}


def list_regions(
    *,
    page: int,
    page_size: int,
    keyword: str,
    status: str | None,
    level: str | None,
    parent_id: int | None,
    current_user: dict[str, Any],
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    normalized_level = normalize_region_level_filter(level)
    try:
        items, total = repo().list_regions(
            tenant_id=current_tenant_id(current_user),
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            level=normalized_level,
            parent_id=parent_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
            data_scope=data_access_for(current_user, REGION_RESOURCE).read(),
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def list_region_tree(*, include_disabled: bool, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        regions = repo().list_all_regions(tenant_id=current_tenant_id(current_user), include_disabled=include_disabled)
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {"items": build_region_tree([item.to_dict() for item in regions])}


def list_region_children(*, parent_id: int | None, active_only: bool, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        items = repo().list_region_children(
            tenant_id=current_tenant_id(current_user),
            parent_id=parent_id,
            active_only=active_only,
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {"items": [item.to_dict() for item in items]}


def list_region_options(*, parent_id: int | None, current_user: dict[str, Any]) -> dict[str, Any]:
    payload = list_region_children(parent_id=parent_id, active_only=True, current_user=current_user)
    return {
        "items": [
            {
                "label": item["name"],
                "value": item["id"],
                "code": item["code"],
                "level": item["level"],
                "is_leaf": item["level"] == REGION_LEVEL_DISTRICT,
            }
            for item in payload["items"]
        ]
    }


def save_region(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    normalized = normalize_region_payload(payload)
    region_id = int(normalized.get("id") or 0)
    if region_id:
        ensure_record_access(
            tenant_id=tenant_id,
            row=repo().get_region_row(tenant_id=tenant_id, region_id=region_id),
            current_user=current_user,
            resource=REGION_RESOURCE,
            action="write",
            not_found_message="region not found",
        )
    ensure_unique_region_code(tenant_id=tenant_id, region_id=region_id, code=str(normalized.get("code") or ""))
    parent = ensure_valid_region_parent(tenant_id=tenant_id, region_id=region_id, parent_id=normalized.get("parent_id"), level=str(normalized.get("level") or ""))
    normalized["parent_code"] = parent.code if parent else ""
    normalized.update(data_owner_fields(current_user))
    region = Region(
        id=region_id,
        tenant_id=tenant_id,
        parent_id=normalized.get("parent_id"),
        parent_code=normalized.get("parent_code") or "",
        code=normalized.get("code") or "",
        name=normalized.get("name") or "",
        short_name=normalized.get("short_name") or "",
        level=normalized.get("level") or "",
        path="",
        status=normalized.get("status") or STATUS_ACTIVE,
        sort_order=int(normalized.get("sort_order") or 0),
        extra=normalized.get("extra") if isinstance(normalized.get("extra"), dict) else {},
        create_time="",
        update_time="",
    )
    region.validate()
    try:
        item = repo().save_region(
            tenant_id=tenant_id,
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {"item": item.to_dict()}


def delete_region(*, region_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    ensure_record_access(
        tenant_id=tenant_id,
        row=repo().get_region_row(tenant_id=tenant_id, region_id=region_id),
        current_user=current_user,
        resource=REGION_RESOURCE,
        action="manage",
        not_found_message="region not found",
    )
    try:
        item = repo().delete_region(
            tenant_id=tenant_id,
            region_id=region_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    if not item:
        raise BasicDataNotFoundError("region not found")
    return {"id": item.id, "deleted": True}


def import_regions(
    *,
    content: bytes,
    filename: str,
    dry_run: bool,
    mode: str,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    rows, warnings = parse_region_import_rows(content=content, filename=filename)
    mode = mode if mode in {"upsert", "create_only"} else "upsert"
    tenant_id = current_tenant_id(current_user)
    summary: dict[str, Any] = {
        "created_count": 0,
        "updated_count": 0,
        "skipped_count": 0,
        "error_count": 0,
        "errors": [],
        "warnings": warnings,
        "dry_run": dry_run,
        "mode": mode,
    }
    if not rows:
        summary["warnings"].append({"row": None, "message": "import file has no rows"})
        return summary
    normalized_rows = normalize_region_import_rows(rows)
    errors = validate_region_import_rows(tenant_id=tenant_id, rows=normalized_rows)
    if errors:
        summary["errors"] = errors
        summary["error_count"] = len(errors)
        return summary

    existing_by_code = {item.code: item for item in repo().list_all_regions(tenant_id=tenant_id, include_disabled=True)}
    for row in sorted_region_import_rows(normalized_rows):
        existing = existing_by_code.get(row["code"])
        if existing and mode == "create_only":
            summary["skipped_count"] += 1
            continue
        parent = existing_by_code.get(row["parent_code"]) if row["parent_code"] else None
        payload = {
            "id": existing.id if existing else 0,
            "parent_id": parent.id if parent else None,
            "code": row["code"],
            "name": row["name"],
            "short_name": row["short_name"],
            "level": row["level"],
            "status": row["status"],
            "sort_order": row["sort_order"],
            "extra": row["extra"],
        }
        if existing:
            summary["updated_count"] += 1
        else:
            summary["created_count"] += 1
        if dry_run:
            continue
        saved = save_region(payload, current_user)["item"]
        existing_by_code[row["code"]] = Region(
            id=int(saved["id"]),
            tenant_id=tenant_id,
            parent_id=saved.get("parent_id"),
            parent_code=str(saved.get("parent_code") or ""),
            code=str(saved.get("code") or ""),
            name=str(saved.get("name") or ""),
            short_name=str(saved.get("short_name") or ""),
            level=str(saved.get("level") or ""),
            path=str(saved.get("path") or ""),
            status=str(saved.get("status") or STATUS_ACTIVE),
            sort_order=int(saved.get("sort_order") or 0),
            extra=saved.get("extra") if isinstance(saved.get("extra"), dict) else {},
            create_time=str(saved.get("create_time") or ""),
            update_time=str(saved.get("update_time") or ""),
        )
    return summary


def ensure_dictionary_type_exists(*, tenant_id: int, type_id: int) -> DictionaryType:
    try:
        item = repo().get_dictionary_type(tenant_id=tenant_id, type_id=type_id)
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    if not item:
        raise BasicDataNotFoundError("dictionary type not found")
    return item


def ensure_unique_type_code(*, tenant_id: int, type_id: int, code: str) -> None:
    try:
        existing = repo().get_dictionary_type_by_code(tenant_id=tenant_id, code=code.strip())
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    if existing and existing.id != type_id:
        raise BasicDataDomainError("dictionary type code already exists")


def ensure_valid_type_parent(*, tenant_id: int, type_id: int, parent_id: int | None) -> None:
    if not parent_id:
        return
    if type_id and parent_id == type_id:
        raise BasicDataDomainError("dictionary type parent cannot be itself")
    parent = ensure_dictionary_type_exists(tenant_id=tenant_id, type_id=parent_id)
    visited = {type_id} if type_id else set()
    current = parent
    while current.parent_id:
        if current.parent_id in visited:
            raise BasicDataDomainError("dictionary type parent cannot be a descendant")
        visited.add(current.id)
        next_parent = repo().get_dictionary_type(tenant_id=tenant_id, type_id=current.parent_id)
        if not next_parent:
            break
        current = next_parent


def ensure_region_exists(*, tenant_id: int, region_id: int) -> Region:
    try:
        item = repo().get_region(tenant_id=tenant_id, region_id=region_id)
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    if not item:
        raise BasicDataNotFoundError("region not found")
    return item


def ensure_unique_region_code(*, tenant_id: int, region_id: int, code: str) -> None:
    try:
        existing = repo().get_region_by_code(tenant_id=tenant_id, code=code.strip())
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    if existing and existing.id != region_id:
        raise BasicDataDomainError("region code already exists")


def ensure_valid_region_parent(*, tenant_id: int, region_id: int, parent_id: int | None, level: str) -> Region | None:
    if level == REGION_LEVEL_PROVINCE:
        if parent_id:
            raise BasicDataDomainError("province region cannot have parent")
        return None
    if not parent_id:
        raise BasicDataDomainError("city and district regions require parent")
    if region_id and parent_id == region_id:
        raise BasicDataDomainError("region parent cannot be itself")
    parent = ensure_region_exists(tenant_id=tenant_id, region_id=parent_id)
    expected_parent_level = REGION_LEVEL_PROVINCE if level == REGION_LEVEL_CITY else REGION_LEVEL_CITY
    if parent.level != expected_parent_level:
        raise BasicDataDomainError(f"{level} region parent must be {expected_parent_level}")
    if region_id and is_region_descendant(tenant_id=tenant_id, candidate_id=parent_id, ancestor_id=region_id):
        raise BasicDataDomainError("region parent cannot be a descendant")
    return parent


def is_region_descendant(*, tenant_id: int, candidate_id: int, ancestor_id: int) -> bool:
    current = ensure_region_exists(tenant_id=tenant_id, region_id=candidate_id)
    visited: set[int] = set()
    while current.parent_id:
        if current.parent_id == ancestor_id:
            return True
        if current.parent_id in visited:
            return False
        visited.add(current.parent_id)
        next_parent = repo().get_region(tenant_id=tenant_id, region_id=current.parent_id)
        if not next_parent:
            return False
        current = next_parent
    return False


def normalize_type_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(payload.get("id") or 0),
        "parent_id": int(payload.get("parent_id") or 0) or None,
        "code": str(payload.get("code") or "").strip(),
        "name": str(payload.get("name") or "").strip(),
        "category": str(payload.get("category") or "general").strip() or "general",
        "description": str(payload.get("description") or "").strip(),
        "status": str(payload.get("status") or STATUS_ACTIVE).strip() or STATUS_ACTIVE,
        "sort_order": int(payload.get("sort_order") or 0),
    }


def normalize_item_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(payload.get("id") or 0),
        "code": str(payload.get("code") or "").strip(),
        "value": str(payload.get("value") or "").strip(),
        "color": str(payload.get("color") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "extra": payload.get("extra") if isinstance(payload.get("extra"), dict) else {},
        "status": str(payload.get("status") or STATUS_ACTIVE).strip() or STATUS_ACTIVE,
        "sort_order": int(payload.get("sort_order") or 0),
    }


def normalize_region_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(payload.get("id") or 0),
        "parent_id": int(payload.get("parent_id") or 0) or None,
        "code": str(payload.get("code") or "").strip(),
        "name": str(payload.get("name") or "").strip(),
        "short_name": str(payload.get("short_name") or "").strip(),
        "level": normalize_region_level(payload.get("level")),
        "status": str(payload.get("status") or STATUS_ACTIVE).strip() or STATUS_ACTIVE,
        "sort_order": int(payload.get("sort_order") or 0),
        "extra": payload.get("extra") if isinstance(payload.get("extra"), dict) else {},
    }


def normalize_region_level(value: Any) -> str:
    raw = str(value or "").strip()
    level = REGION_LEVEL_ALIASES.get(raw.lower()) or REGION_LEVEL_ALIASES.get(raw)
    if not level:
        raise BasicDataDomainError(f"unsupported region level: {raw}")
    return level


def normalize_region_level_filter(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return normalize_region_level(raw)


def build_region_tree(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes = {int(item["id"]): {**item, "children": []} for item in items}
    roots: list[dict[str, Any]] = []
    for node in nodes.values():
        parent_id = int(node.get("parent_id") or 0)
        parent = nodes.get(parent_id)
        if parent and parent["id"] != node["id"]:
            parent["children"].append(node)
        else:
            roots.append(node)
    for node in nodes.values():
        if not node["children"]:
            node.pop("children", None)
    return roots


def parse_region_import_rows(*, content: bytes, filename: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not filename.lower().endswith(".csv"):
        raise BasicDataDomainError("only csv region import is supported")
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    warnings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(reader, start=2):
        normalized = {str(key or "").strip(): value for key, value in row.items() if key}
        if "path" in normalized:
            warnings.append({"row": index, "message": "path column is ignored; region path is generated by server"})
            normalized.pop("path", None)
        normalized["_row"] = index
        rows.append(normalized)
    return rows, warnings


def normalize_region_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        extra: dict[str, Any] = {}
        extra_text = str(row.get("extra_json") or "").strip()
        if extra_text:
            try:
                parsed = json.loads(extra_text)
            except json.JSONDecodeError as exc:
                raise BasicDataDomainError(f"invalid extra_json at row {row.get('_row')}") from exc
            if not isinstance(parsed, dict):
                raise BasicDataDomainError(f"extra_json must be object at row {row.get('_row')}")
            extra = parsed
        normalized_rows.append(
            {
                "row": int(row.get("_row") or 0),
                "code": str(row.get("code") or "").strip(),
                "parent_code": str(row.get("parent_code") or "").strip(),
                "name": str(row.get("name") or "").strip(),
                "short_name": str(row.get("short_name") or "").strip(),
                "level": normalize_region_level(row.get("level")),
                "status": str(row.get("status") or STATUS_ACTIVE).strip() or STATUS_ACTIVE,
                "sort_order": int(row.get("sort_order") or 0),
                "extra": extra,
            }
        )
    return normalized_rows


def validate_region_import_rows(*, tenant_id: int, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    row_by_code = {str(row["code"]): row for row in rows if row.get("code")}
    existing_by_code = {item.code: item for item in repo().list_all_regions(tenant_id=tenant_id, include_disabled=True)}
    for row in rows:
        code = str(row.get("code") or "")
        if not code:
            errors.append({"row": row["row"], "message": "region code is required"})
            continue
        if code in seen_codes:
            errors.append({"row": row["row"], "message": f"duplicate code in import file: {code}"})
        seen_codes.add(code)
        if not str(row.get("name") or "").strip():
            errors.append({"row": row["row"], "message": "region name is required"})
        level = str(row.get("level") or "")
        parent_code = str(row.get("parent_code") or "")
        if level == REGION_LEVEL_PROVINCE and parent_code:
            errors.append({"row": row["row"], "message": "province region cannot have parent_code"})
        if level in {REGION_LEVEL_CITY, REGION_LEVEL_DISTRICT} and not parent_code:
            errors.append({"row": row["row"], "message": f"{level} region requires parent_code"})
        if parent_code:
            parent_row = row_by_code.get(parent_code)
            parent_existing = existing_by_code.get(parent_code)
            parent_level = str(parent_row.get("level") if parent_row else parent_existing.level if parent_existing else "")
            if not parent_level:
                errors.append({"row": row["row"], "message": f"parent_code not found: {parent_code}"})
            else:
                expected = REGION_LEVEL_PROVINCE if level == REGION_LEVEL_CITY else REGION_LEVEL_CITY
                if parent_level != expected:
                    errors.append({"row": row["row"], "message": f"{level} region parent must be {expected}"})
    return errors


def sorted_region_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {REGION_LEVEL_PROVINCE: 0, REGION_LEVEL_CITY: 1, REGION_LEVEL_DISTRICT: 2}
    return sorted(rows, key=lambda item: (order.get(str(item.get("level")), 99), int(item.get("sort_order") or 0), str(item.get("code") or "")))


def normalized_type_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "parent_id": int(payload.get("parent_id") or 0) or None,
        "code": str(payload.get("code") or ""),
        "name": str(payload.get("name") or ""),
        "category": str(payload.get("category") or ""),
        "description": str(payload.get("description") or ""),
        "status": str(payload.get("status") or STATUS_ACTIVE),
        "sort_order": int(payload.get("sort_order") or 0),
    }


def normalized_item_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(payload.get("code") or ""),
        "value": str(payload.get("value") or ""),
        "color": str(payload.get("color") or ""),
        "description": str(payload.get("description") or ""),
        "extra": payload.get("extra") if isinstance(payload.get("extra"), dict) else {},
        "status": str(payload.get("status") or STATUS_ACTIVE),
        "sort_order": int(payload.get("sort_order") or 0),
    }


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current_tenant = current_user.get("current_tenant") or {}
    tenant_id = current_tenant.get("id") or current_user.get("tenant_id") or 1
    return int(tenant_id)


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None


def ensure_record_access(
    *,
    tenant_id: int,
    row: dict[str, Any] | None,
    current_user: dict[str, Any],
    resource: ResourceDescriptor,
    action: str,
    not_found_message: str,
) -> None:
    if not row:
        raise BasicDataNotFoundError(not_found_message)
    if int(row.get("tenant_id") or 0) != tenant_id:
        raise BasicDataNotFoundError(not_found_message)
    ensure_data_access_record(
        row,
        current_user=current_user,
        resource=resource,
        action=action,
        denied=BasicDataNotFoundError(not_found_message),
    )
