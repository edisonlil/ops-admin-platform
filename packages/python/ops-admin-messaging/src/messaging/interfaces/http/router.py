from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from identity_access.interfaces.http import dependencies as auth
from messaging.application import services
from messaging.interfaces.http.dtos import (
    MessageChatBotRequest,
    MessageChannelAccountRequest,
    MessagePreferencesRequest,
    MessageTemplateRequest,
    RenderMessageTemplateRequest,
    SendInAppMessageRequest,
    SendTemplateMessageRequest,
)
from system.interfaces.http import ok


router = APIRouter(prefix="/messaging")


@router.get("/messages")
def messages(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:messages:view")),
) -> dict[str, Any]:
    return ok(services.list_messages(page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir, current_user=current_user))


@router.post("/messages/send")
def send_message(
    payload: SendInAppMessageRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:messages:send")),
) -> dict[str, Any]:
    return ok(services.send_in_app_message(payload.model_dump(), current_user))


@router.post("/messages/send-template")
def send_template_message(
    payload: SendTemplateMessageRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:messages:send")),
) -> dict[str, Any]:
    return ok(services.send_template_message(payload.model_dump(), current_user))


@router.get("/templates")
def templates(
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:view")),
) -> dict[str, Any]:
    return ok(services.list_templates(current_user, sort_by=sort_by, sort_dir=sort_dir))


@router.post("/templates/render")
def render_template(
    payload: RenderMessageTemplateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:view")),
) -> dict[str, Any]:
    return ok(services.render_template(payload.model_dump(), current_user))


@router.post("/templates")
def save_template(
    payload: MessageTemplateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:create")),
) -> dict[str, Any]:
    return ok(services.save_template(payload.model_dump(), current_user))


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    payload: MessageTemplateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:update")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = template_id
    return ok(services.save_template(data, current_user))


@router.post("/templates/{template_id}/enable")
def enable_template(
    template_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:enable")),
) -> dict[str, Any]:
    return ok(services.set_template_status(template_id, "enabled", current_user))


@router.post("/templates/{template_id}/disable")
def disable_template(
    template_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:disable")),
) -> dict[str, Any]:
    return ok(services.set_template_status(template_id, "disabled", current_user))


@router.get("/channel-accounts")
def channel_accounts(
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:view")),
) -> dict[str, Any]:
    return ok(services.list_channel_accounts(current_user, sort_by=sort_by, sort_dir=sort_dir))


@router.post("/channel-accounts")
def save_channel_account(
    payload: MessageChannelAccountRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:create")),
) -> dict[str, Any]:
    return ok(services.save_channel_account(payload.model_dump(), current_user))


@router.put("/channel-accounts/{account_id}")
def update_channel_account(
    account_id: int,
    payload: MessageChannelAccountRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:update")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = account_id
    return ok(services.save_channel_account(data, current_user))


@router.post("/channel-accounts/{account_id}/enable")
def enable_channel_account(
    account_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:enable")),
) -> dict[str, Any]:
    return ok(services.set_channel_account_enabled(account_id, True, current_user))


@router.post("/channel-accounts/{account_id}/disable")
def disable_channel_account(
    account_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:disable")),
) -> dict[str, Any]:
    return ok(services.set_channel_account_enabled(account_id, False, current_user))


@router.post("/channel-accounts/{account_id}/test")
def test_channel_account(
    account_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:test")),
) -> dict[str, Any]:
    return ok(services.test_channel_account(account_id, current_user))


@router.get("/chat-bots")
def chat_bots(
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:chat_bots:view")),
) -> dict[str, Any]:
    return ok(services.list_chat_bots(current_user, sort_by=sort_by, sort_dir=sort_dir))


@router.post("/chat-bots")
def save_chat_bot(
    payload: MessageChatBotRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:chat_bots:create")),
) -> dict[str, Any]:
    return ok(services.save_chat_bot(payload.model_dump(), current_user))


@router.put("/chat-bots/{chat_bot_id}")
def update_chat_bot(
    chat_bot_id: int,
    payload: MessageChatBotRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:chat_bots:update")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = chat_bot_id
    return ok(services.save_chat_bot(data, current_user))


@router.post("/chat-bots/{chat_bot_id}/enable")
def enable_chat_bot(
    chat_bot_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:chat_bots:enable")),
) -> dict[str, Any]:
    return ok(services.set_chat_bot_enabled(chat_bot_id, True, current_user))


@router.post("/chat-bots/{chat_bot_id}/disable")
def disable_chat_bot(
    chat_bot_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:chat_bots:disable")),
) -> dict[str, Any]:
    return ok(services.set_chat_bot_enabled(chat_bot_id, False, current_user))


@router.post("/chat-bots/{chat_bot_id}/test")
def test_chat_bot(
    chat_bot_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:chat_bots:test")),
) -> dict[str, Any]:
    return ok(services.test_chat_bot(chat_bot_id, current_user))


@router.get("/inbox")
def inbox(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:inbox:view")),
) -> dict[str, Any]:
    return ok(services.list_my_inbox(page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir, current_user=current_user))


@router.get("/inbox/unread-count")
def inbox_unread_count(
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:inbox:view")),
) -> dict[str, Any]:
    return ok(services.unread_count(current_user))


@router.post("/inbox/{recipient_id}/read")
def mark_inbox_read(
    recipient_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:inbox:manage_self")),
) -> dict[str, Any]:
    return ok(services.mark_read(recipient_id, current_user))


@router.post("/inbox/read-all")
def mark_all_inbox_read(
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:inbox:manage_self")),
) -> dict[str, Any]:
    return ok(services.mark_all_read(current_user))


@router.get("/preferences")
def preferences(
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:inbox:manage_self")),
) -> dict[str, Any]:
    return ok(services.list_preferences(current_user))


@router.put("/preferences")
def save_preferences(
    payload: MessagePreferencesRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:inbox:manage_self")),
) -> dict[str, Any]:
    return ok(services.save_preferences(payload.model_dump(), current_user))
