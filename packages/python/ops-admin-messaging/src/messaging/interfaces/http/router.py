from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from identity_access.interfaces.http import dependencies as auth
from messaging.application import services
from messaging.interfaces.http.dtos import SendInAppMessageRequest
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
