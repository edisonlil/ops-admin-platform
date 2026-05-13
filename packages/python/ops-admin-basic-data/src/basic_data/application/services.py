from __future__ import annotations

from typing import Any

from basic_data.application.ports import BasicDataRepository
from basic_data.domain.exceptions import BasicDataDomainError, BasicDataNotFoundError, BasicDataStorageNotReadyError
from basic_data.domain.models import DictionaryItem, DictionaryType, STATUS_ACTIVE


repository: BasicDataRepository | None = None


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
) -> dict[str, Any]:
    try:
        items, total = repo().list_dictionary_types(
            tenant_id=current_tenant_id(current_user),
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            category=category,
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def save_dictionary_type(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    normalized = normalize_type_payload(payload)
    ensure_unique_type_code(tenant_id=tenant_id, type_id=int(normalized.get("id") or 0), code=str(normalized.get("code") or ""))
    ensure_valid_type_parent(tenant_id=tenant_id, type_id=int(normalized.get("id") or 0), parent_id=normalized.get("parent_id"))
    dictionary_type = DictionaryType(id=int(normalized.get("id") or 0), tenant_id=tenant_id, create_time="", update_time="", **normalized_type_fields(normalized))
    dictionary_type.validate()
    try:
        item = repo().save_dictionary_type(
            tenant_id=tenant_id,
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise BasicDataStorageNotReadyError(str(exc)) from exc
    return {"item": item.to_dict()}


def delete_dictionary_type(*, type_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        item = repo().delete_dictionary_type(
            tenant_id=current_tenant_id(current_user),
            type_id=type_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
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
    data = {**payload, "id": item_id}
    return save_dictionary_item(existing.type_id, data, current_user)


def delete_dictionary_item(*, item_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        item = repo().delete_dictionary_item(
            tenant_id=current_tenant_id(current_user),
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
