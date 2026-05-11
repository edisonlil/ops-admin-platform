from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from messaging.infrastructure.persistence import repositories


def send_in_app_message(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    recipient_user_ids = normalize_recipient_ids(payload.get("recipient_user_ids"))
    if not recipient_user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recipient_user_ids is required")
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title is required")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="content is required")
    actor = str(current_user.get("username") or current_user.get("name") or "")
    sender_user_id = int(current_user.get("id", 0) or 0) or None
    try:
        message = repositories.create_in_app_message(
            tenant_id=tenant_id,
            title=title,
            content=content,
            recipient_user_ids=recipient_user_ids,
            message_type=str(payload.get("message_type") or "system"),
            priority=str(payload.get("priority") or "normal"),
            payload=payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
            sender_user_id=sender_user_id,
            sender_name=actor,
            actor=actor,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"item": message.to_dict()}


def list_messages(*, page: int, page_size: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        items, total = repositories.list_messages(
            tenant_id=current_tenant_id(current_user),
            page=page,
            page_size=page_size,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def list_my_inbox(*, page: int, page_size: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        items, total = repositories.list_inbox(
            tenant_id=current_tenant_id(current_user),
            user_id=current_user_id(current_user),
            page=page,
            page_size=page_size,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def unread_count(current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        count = repositories.unread_count(
            tenant_id=current_tenant_id(current_user),
            user_id=current_user_id(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"count": count}


def mark_read(recipient_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        item = repositories.mark_read(
            tenant_id=current_tenant_id(current_user),
            user_id=current_user_id(current_user),
            recipient_id=recipient_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message recipient not found")
    return {"item": item.to_dict()}


def mark_all_read(current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        count = repositories.mark_all_read(
            tenant_id=current_tenant_id(current_user),
            user_id=current_user_id(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"updated": count}


def list_templates(current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        items = repositories.list_templates(tenant_id=current_tenant_id(current_user))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"items": [item.to_dict() for item in items]}


def save_template(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    template_key = str(payload.get("template_key") or "").strip()
    name = str(payload.get("name") or "").strip()
    title_template = str(payload.get("title_template") or "").strip()
    content_template = str(payload.get("content_template") or "").strip()
    if not template_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="template_key is required")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    if not title_template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title_template is required")
    if not content_template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="content_template is required")
    actor = current_actor(current_user)
    try:
        item = repositories.save_template(
            tenant_id=current_tenant_id(current_user),
            payload=payload,
            actor=actor,
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"item": item.to_dict()}


def set_template_status(template_id: int, next_status: str, current_user: dict[str, Any]) -> dict[str, Any]:
    actor = current_actor(current_user)
    try:
        item = repositories.set_template_status(
            tenant_id=current_tenant_id(current_user),
            template_id=template_id,
            status=next_status,
            actor=actor,
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message template not found")
    return {"item": item.to_dict()}


def list_channel_accounts(current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        items = repositories.list_channel_accounts(tenant_id=current_tenant_id(current_user))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"items": [item.to_dict() for item in items]}


def save_channel_account(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    channel = str(payload.get("channel") or "").strip()
    name = str(payload.get("name") or "").strip()
    if not channel:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="channel is required")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    actor = current_actor(current_user)
    try:
        item = repositories.save_channel_account(
            tenant_id=current_tenant_id(current_user),
            payload=payload,
            actor=actor,
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"item": item.to_dict()}


def set_channel_account_enabled(account_id: int, enabled: bool, current_user: dict[str, Any]) -> dict[str, Any]:
    actor = current_actor(current_user)
    try:
        item = repositories.set_channel_account_enabled(
            tenant_id=current_tenant_id(current_user),
            account_id=account_id,
            enabled=enabled,
            actor=actor,
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message channel account not found")
    return {"item": item.to_dict()}


def test_channel_account(account_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        item = repositories.get_channel_account(tenant_id=current_tenant_id(current_user), account_id=account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message channel account not found")
    if item.channel == "in_app":
        return {"ok": True, "channel": item.channel, "message": "站内信通道可用"}
    return {"ok": False, "channel": item.channel, "message": "该外部通道适配器尚未接入"}


def list_preferences(current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        items = repositories.list_preferences(
            tenant_id=current_tenant_id(current_user),
            user_id=current_user_id(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"items": [item.to_dict() for item in items]}


def save_preferences(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    preferences = payload.get("items")
    if not isinstance(preferences, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="items is required")
    actor = current_actor(current_user)
    try:
        items = repositories.save_preferences(
            tenant_id=current_tenant_id(current_user),
            user_id=current_user_id(current_user),
            preferences=preferences,
            actor=actor,
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"items": [item.to_dict() for item in items]}


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current_tenant = current_user.get("current_tenant") or {}
    tenant_id = current_tenant.get("id") or current_user.get("tenant_id") or 1
    return int(tenant_id)


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None


def current_user_id(current_user: dict[str, Any]) -> int:
    user_id = int(current_user.get("id", 0) or 0)
    if user_id <= 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user is required")
    return user_id


def normalize_recipient_ids(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    normalized: list[int] = []
    for item in value:
        try:
            user_id = int(item)
        except (TypeError, ValueError):
            continue
        if user_id > 0 and user_id not in normalized:
            normalized.append(user_id)
    return normalized
