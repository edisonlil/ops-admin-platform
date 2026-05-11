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


class SendTemplateMessageRequest(BaseModel):
    template_key: str = Field(min_length=1, max_length=120)
    variables: dict[str, Any] = Field(default_factory=dict)
    recipient_user_ids: list[int] = Field(default_factory=list)
    message_type: str = Field(default="system", max_length=60)
    priority: str = Field(default="normal", max_length=40)
    channels: list[str] | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RenderMessageTemplateRequest(BaseModel):
    template_key: str = Field(min_length=1, max_length=120)
    variables: dict[str, Any] = Field(default_factory=dict)


class MessageTemplateRequest(BaseModel):
    id: int | None = None
    template_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=800)
    channels: list[str] = Field(default_factory=lambda: ["in_app"])
    title_template: str = Field(min_length=1, max_length=300)
    content_template: str = Field(min_length=1, max_length=8000)
    variables_schema: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="draft", max_length=40)


class MessageChannelAccountRequest(BaseModel):
    id: int | None = None
    channel: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    config: dict[str, Any] = Field(default_factory=dict)
    secret_ref: str = Field(default="", max_length=300)
    enabled: bool = True
    is_default: bool = False


class MessagePreferenceItemRequest(BaseModel):
    message_type: str = Field(default="system", max_length=60)
    channels: list[str] = Field(default_factory=lambda: ["in_app"])
    quiet_hours: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class MessagePreferencesRequest(BaseModel):
    items: list[MessagePreferenceItemRequest] = Field(default_factory=list)
