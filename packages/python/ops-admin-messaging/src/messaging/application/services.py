from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException, status

from messaging.application.ports import ChatBotSenderPort, UnavailableChatBotSender
from messaging.infrastructure.persistence import repositories
from system.application.sorting import InvalidSortError
from system.application.data_access import (
    ResourceDescriptor,
    current_user_primary_department_id,
    resolve_data_access_filter,
)

TEMPLATE_VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
MESSAGE_RESOURCE = ResourceDescriptor(resource_key="messaging.message")
SUPPORTED_CHAT_BOT_PLATFORMS = ("wps", "wecom", "feishu", "dingtalk")
chat_bot_sender: ChatBotSenderPort = UnavailableChatBotSender()


def configure_chat_bot_sender(sender: ChatBotSenderPort) -> None:
    global chat_bot_sender
    chat_bot_sender = sender


def send_in_app_message(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    recipient_user_ids = normalize_recipient_ids(payload.get("recipient_user_ids"))
    chat_bot_ids = normalize_id_list(payload.get("chat_bot_ids"))
    if not recipient_user_ids and not chat_bot_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recipient_user_ids or chat_bot_ids is required")
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title is required")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="content is required")
    actor = str(current_user.get("username") or current_user.get("name") or "")
    sender_user_id = int(current_user.get("id", 0) or 0) or None
    try:
        message = repositories.create_message(
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
            template_id=None,
            channels=["in_app"] if recipient_user_ids else [],
            chat_bot_ids=chat_bot_ids,
            owner_department_id=current_user_primary_department_id(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    chat_bot_results = dispatch_chat_bots(tenant_id=tenant_id, chat_bot_ids=chat_bot_ids, title=title, content=content)
    return {"item": message.to_dict(), "chat_bot_results": chat_bot_results}


def send_template_message(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    recipient_user_ids = normalize_recipient_ids(payload.get("recipient_user_ids"))
    chat_bot_ids = normalize_id_list(payload.get("chat_bot_ids"))
    if not recipient_user_ids and not chat_bot_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recipient_user_ids or chat_bot_ids is required")
    template_key = str(payload.get("template_key") or "").strip()
    if not template_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="template_key is required")
    template = get_enabled_template(tenant_id=tenant_id, template_key=template_key)
    variables = payload.get("variables") if isinstance(payload.get("variables"), dict) else {}
    rendered = render_template_values(
        title_template=template.title_template,
        content_template=template.content_template,
        variables=variables,
    )
    actor = current_actor(current_user)
    sender_user_id = current_user_id_or_none(current_user)
    channels_payload = payload.get("channels")
    channels = normalize_channels(channels_payload)
    if channels_payload is None and not channels:
        channels = template.channels
    business_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    business_payload = {
        **business_payload,
        "template_key": template.template_key,
        "template_variables": variables,
        "channels": channels,
        "chat_bot_ids": chat_bot_ids,
    }
    try:
        message = repositories.create_message(
            tenant_id=tenant_id,
            title=rendered["title"],
            content=rendered["content"],
            recipient_user_ids=recipient_user_ids,
            message_type=str(payload.get("message_type") or "system"),
            priority=str(payload.get("priority") or "normal"),
            payload=business_payload,
            sender_user_id=sender_user_id,
            sender_name=actor,
            actor=actor,
            template_id=template.id,
            channels=channels,
            chat_bot_ids=chat_bot_ids,
            owner_department_id=current_user_primary_department_id(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    chat_bot_results = dispatch_chat_bots(
        tenant_id=tenant_id,
        chat_bot_ids=chat_bot_ids,
        title=rendered["title"],
        content=rendered["content"],
    )
    return {"item": message.to_dict(), "rendered": rendered, "channels": channels, "chat_bot_results": chat_bot_results}


def list_messages(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    try:
        items, total = repositories.list_messages(
            tenant_id=current_tenant_id(current_user),
            page=page,
            page_size=page_size,
            data_scope=resolve_data_access_filter(current_user=current_user, resource=MESSAGE_RESOURCE, action="read"),
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except InvalidSortError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def list_my_inbox(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    try:
        items, total = repositories.list_inbox(
            tenant_id=current_tenant_id(current_user),
            user_id=current_user_id(current_user),
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except InvalidSortError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def page_items(items: list[dict[str, Any]], *, page: int, page_size: int) -> dict[str, Any]:
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, int(page_size or 20))
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    return {
        "items": items[start:start + safe_page_size],
        "pagination": {"page": safe_page, "page_size": safe_page_size, "total": total},
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


def list_templates(
    current_user: dict[str, Any],
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    try:
        items = repositories.list_templates(tenant_id=current_tenant_id(current_user), sort_by=sort_by, sort_dir=sort_dir)
    except InvalidSortError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return page_items([item.to_dict() for item in items], page=page, page_size=page_size)


def render_template(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    template_key = str(payload.get("template_key") or "").strip()
    if not template_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="template_key is required")
    template = get_enabled_template(tenant_id=current_tenant_id(current_user), template_key=template_key)
    variables = payload.get("variables") if isinstance(payload.get("variables"), dict) else {}
    rendered = render_template_values(
        title_template=template.title_template,
        content_template=template.content_template,
        variables=variables,
    )
    return {"template": template.to_dict(), "rendered": rendered, "missing_variables": rendered["missing_variables"]}


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


def list_channel_accounts(
    current_user: dict[str, Any],
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    try:
        items = repositories.list_channel_accounts(tenant_id=current_tenant_id(current_user), sort_by=sort_by, sort_dir=sort_dir)
    except InvalidSortError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return page_items([item.to_dict() for item in items], page=page, page_size=page_size)


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
        return {"ok": True, "channel": item.channel, "message": "站内信渠道已启用"}
    return {"ok": False, "channel": item.channel, "message": "外部渠道适配器尚未接入，请使用群聊机器人配置 Webhook"}


def list_chat_bots(
    current_user: dict[str, Any],
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    try:
        items = repositories.list_chat_bots(tenant_id=current_tenant_id(current_user), sort_by=sort_by, sort_dir=sort_dir)
    except InvalidSortError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return page_items([item.to_dict() for item in items], page=page, page_size=page_size)


def save_chat_bot(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    validate_chat_bot_payload(payload)
    actor = current_actor(current_user)
    try:
        item = repositories.save_chat_bot(
            tenant_id=current_tenant_id(current_user),
            payload=payload,
            actor=actor,
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"item": item.to_dict()}


def set_chat_bot_enabled(chat_bot_id: int, enabled: bool, current_user: dict[str, Any]) -> dict[str, Any]:
    actor = current_actor(current_user)
    try:
        item = repositories.set_chat_bot_enabled(
            tenant_id=current_tenant_id(current_user),
            chat_bot_id=chat_bot_id,
            enabled=enabled,
            actor=actor,
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message chat bot not found")
    return {"item": item.to_dict()}


def test_chat_bot(chat_bot_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    actor = current_actor(current_user)
    try:
        item = repositories.get_chat_bot(tenant_id=tenant_id, chat_bot_id=chat_bot_id, mask_secrets=False)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message chat bot not found")
    if not item.enabled:
        result = {"ok": False, "message": "群聊机器人未启用", "status_code": 0, "response": {}}
    else:
        delivery = chat_bot_sender.send(chat_bot=item, title="消息中心测试", content="这是一条群聊机器人测试消息。")
        result = {
            "ok": delivery.ok,
            "message": delivery.message,
            "status_code": delivery.status_code,
            "response": delivery.response,
        }
    updated = repositories.update_chat_bot_test_result(
        tenant_id=tenant_id,
        chat_bot_id=chat_bot_id,
        status="success" if result["ok"] else "failed",
        message=str(result["message"]),
        actor=actor,
        actor_id=current_user_id_or_none(current_user),
    )
    return {"item": updated.to_dict() if updated else item.to_dict(), **result}


def get_enabled_template(*, tenant_id: int, template_key: str):
    try:
        template = repositories.get_template_by_key(tenant_id=tenant_id, template_key=template_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message template not found")
    if template.status != "enabled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message template is not enabled")
    return template


def validate_chat_bot_payload(payload: dict[str, Any]) -> None:
    platform = str(payload.get("platform") or "").strip()
    name = str(payload.get("name") or "").strip()
    webhook_url = str(payload.get("webhook_url") or "").strip()
    message_format = str(payload.get("message_format") or "text").strip() or "text"
    if platform not in SUPPORTED_CHAT_BOT_PLATFORMS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="platform must be wps, wecom, feishu, or dingtalk")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    if not webhook_url or not webhook_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="webhook_url must be a valid URL")
    if message_format != "text":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message_format currently only supports text")


def dispatch_chat_bots(*, tenant_id: int, chat_bot_ids: list[int], title: str, content: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for chat_bot_id in chat_bot_ids:
        chat_bot = repositories.get_chat_bot(tenant_id=tenant_id, chat_bot_id=chat_bot_id, mask_secrets=False)
        if not chat_bot or not chat_bot.enabled:
            results.append({"chat_bot_id": chat_bot_id, "ok": False, "message": "群聊机器人不存在或未启用", "status_code": 0})
            continue
        delivery = chat_bot_sender.send(chat_bot=chat_bot, title=title, content=content)
        results.append(
            {
                "chat_bot_id": chat_bot_id,
                "platform": chat_bot.platform,
                "name": chat_bot.name,
                "ok": delivery.ok,
                "message": delivery.message,
                "status_code": delivery.status_code,
            }
        )
    return results


def render_template_values(*, title_template: str, content_template: str, variables: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = lookup_variable(variables, key)
        if value is None:
            if key not in missing:
                missing.append(key)
            return ""
        return str(value)

    return {
        "title": TEMPLATE_VARIABLE_PATTERN.sub(replace, title_template),
        "content": TEMPLATE_VARIABLE_PATTERN.sub(replace, content_template),
        "missing_variables": missing,
    }


def lookup_variable(variables: dict[str, Any], key: str) -> Any:
    current: Any = variables
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def normalize_channels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        channel = str(item or "").strip()
        if channel == "chat_bot":
            continue
        if channel and channel not in normalized:
            normalized.append(channel)
    return normalized


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


def normalize_id_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    normalized: list[int] = []
    for item in value:
        try:
            item_id = int(item)
        except (TypeError, ValueError):
            continue
        if item_id > 0 and item_id not in normalized:
            normalized.append(item_id)
    return normalized
