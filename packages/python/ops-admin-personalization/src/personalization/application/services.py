from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from personalization.infrastructure.persistence import repositories


def get_table_columns(view_key: str, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    user_id = current_user_id(current_user)
    try:
        item = repositories.get_table_column_preference(
            tenant_id=tenant_id,
            user_id=user_id,
            view_key=normalize_view_key(view_key),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"item": item.to_dict() if item else None}


def save_table_columns(view_key: str, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    user_id = current_user_id(current_user)
    actor = current_actor(current_user)
    actor_id = current_user_id_or_none(current_user)
    try:
        item = repositories.save_table_column_preference(
            tenant_id=tenant_id,
            user_id=user_id,
            view_key=normalize_view_key(view_key),
            visible_column_keys=normalize_string_list(payload.get("visible_column_keys")),
            column_order_keys=normalize_string_list(payload.get("column_order_keys")),
            settings=payload.get("settings") if isinstance(payload.get("settings"), dict) else {},
            actor=actor,
            actor_id=actor_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"item": item.to_dict()}


def reset_table_columns(view_key: str, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    user_id = current_user_id(current_user)
    actor = current_actor(current_user)
    actor_id = current_user_id_or_none(current_user)
    try:
        repositories.delete_table_column_preference(
            tenant_id=tenant_id,
            user_id=user_id,
            view_key=normalize_view_key(view_key),
            actor=actor,
            actor_id=actor_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"deleted": True}


def normalize_view_key(value: str) -> str:
    view_key = str(value or "").strip()
    if not view_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="view_key is required")
    if len(view_key) > 160:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="view_key is too long")
    return view_key


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current = current_user.get("current_tenant") or {}
    return int(current.get("id", 0) or 0)


def current_user_id(current_user: dict[str, Any]) -> int:
    user_id = current_user_id_or_none(current_user)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user is required")
    return user_id


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    for key in ("id", "user_id", "sub"):
        value = current_user.get(key)
        if value is not None and str(value).strip():
            return int(value)
    return None


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("account") or current_user.get("email") or "system")
