from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SendInAppMessageRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=8000)
    recipient_user_ids: list[int] = Field(default_factory=list)
    message_type: str = Field(default="system", max_length=60)
    priority: str = Field(default="normal", max_length=40)
    payload: dict[str, Any] = Field(default_factory=dict)
