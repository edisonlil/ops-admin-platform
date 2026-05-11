from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from identity_access.interfaces.http import dependencies as auth
from messaging.application import services
from messaging.interfaces.http.dtos import (
    MessageChannelAccountRequest,
    MessagePreferencesRequest,
    MessageTemplateRequest,
    SendInAppMessageRequest,
)
from system.interfaces.http import ok


router = APIRouter(prefix="/messaging")


@router.get("/messages")
def messages(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:messages:view")),
) -> dict[str, Any]:
    return ok(services.list_messages(page=page, page_size=page_size, current_user=current_user))


@router.post("/messages/send")
def send_message(
    payload: SendInAppMessageRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:messages:send")),
) -> dict[str, Any]:
    return ok(services.send_in_app_message(payload.model_dump(), current_user))


@router.get("/templates")
def templates(
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:view")),
) -> dict[str, Any]:
    return ok(services.list_templates(current_user))


@router.post("/templates")
def save_template(
    payload: MessageTemplateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:manage")),
) -> dict[str, Any]:
    return ok(services.save_template(payload.model_dump(), current_user))


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    payload: MessageTemplateRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:manage")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = template_id
    return ok(services.save_template(data, current_user))


@router.post("/templates/{template_id}/enable")
def enable_template(
    template_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:manage")),
) -> dict[str, Any]:
    return ok(services.set_template_status(template_id, "enabled", current_user))


@router.post("/templates/{template_id}/disable")
def disable_template(
    template_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:templates:manage")),
) -> dict[str, Any]:
    return ok(services.set_template_status(template_id, "disabled", current_user))


@router.get("/channel-accounts")
def channel_accounts(
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:view")),
) -> dict[str, Any]:
    return ok(services.list_channel_accounts(current_user))


@router.post("/channel-accounts")
def save_channel_account(
    payload: MessageChannelAccountRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:manage")),
) -> dict[str, Any]:
    return ok(services.save_channel_account(payload.model_dump(), current_user))


@router.put("/channel-accounts/{account_id}")
def update_channel_account(
    account_id: int,
    payload: MessageChannelAccountRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:manage")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["id"] = account_id
    return ok(services.save_channel_account(data, current_user))


@router.post("/channel-accounts/{account_id}/enable")
def enable_channel_account(
    account_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:manage")),
) -> dict[str, Any]:
    return ok(services.set_channel_account_enabled(account_id, True, current_user))


@router.post("/channel-accounts/{account_id}/disable")
def disable_channel_account(
    account_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:manage")),
) -> dict[str, Any]:
    return ok(services.set_channel_account_enabled(account_id, False, current_user))


@router.post("/channel-accounts/{account_id}/test")
def test_channel_account(
    account_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:channels:manage")),
) -> dict[str, Any]:
    return ok(services.test_channel_account(account_id, current_user))


@router.get("/inbox")
def inbox(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(auth.require_permission("messaging:inbox:view")),
) -> dict[str, Any]:
    return ok(services.list_my_inbox(page=page, page_size=page_size, current_user=current_user))


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
