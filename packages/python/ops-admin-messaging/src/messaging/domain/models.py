from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MESSAGE_STATUS_QUEUED = "queued"
MESSAGE_STATUS_DISPATCHED = "dispatched"
RECIPIENT_STATUS_UNREAD = "unread"
RECIPIENT_STATUS_READ = "read"
DELIVERY_STATUS_PENDING = "pending"
DELIVERY_STATUS_SENT = "sent"


@dataclass(frozen=True)
class MessageIntent:
    id: int
    tenant_id: int
    message_type: str
    priority: str
    title: str
    content: str
    payload: dict[str, Any]
    sender_user_id: int | None
    sender_name: str
    target_scope: str
    target: dict[str, Any]
    status: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "message_type": self.message_type,
            "priority": self.priority,
            "title": self.title,
            "content": self.content,
            "payload": self.payload,
            "sender_user_id": self.sender_user_id,
            "sender_name": self.sender_name,
            "target_scope": self.target_scope,
            "target": self.target,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class MessageRecipient:
    id: int
    tenant_id: int
    message_id: int
    recipient_user_id: int
    recipient_name: str
    read_status: str
    read_time: str | None
    archive_status: str
    pin_status: str
    delivery_summary: dict[str, Any]
    title: str
    content: str
    message_type: str
    priority: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "message_id": self.message_id,
            "recipient_user_id": self.recipient_user_id,
            "recipient_name": self.recipient_name,
            "read_status": self.read_status,
            "read_time": self.read_time,
            "archive_status": self.archive_status,
            "pin_status": self.pin_status,
            "delivery_summary": self.delivery_summary,
            "title": self.title,
            "content": self.content,
            "message_type": self.message_type,
            "priority": self.priority,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class MessageTemplate:
    id: int
    tenant_id: int
    template_key: str
    name: str
    description: str
    channels: list[str]
    title_template: str
    content_template: str
    variables_schema: dict[str, Any]
    status: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "template_key": self.template_key,
            "name": self.name,
            "description": self.description,
            "channels": self.channels,
            "title_template": self.title_template,
            "content_template": self.content_template,
            "variables_schema": self.variables_schema,
            "status": self.status,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class MessageChannelAccount:
    id: int
    tenant_id: int
    channel: str
    name: str
    config: dict[str, Any]
    secret_ref: str
    enabled: bool
    is_default: bool
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "channel": self.channel,
            "name": self.name,
            "config": self.config,
            "secret_ref": self.secret_ref,
            "enabled": self.enabled,
            "is_default": self.is_default,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class MessageChatBot:
    id: int
    tenant_id: int
    platform: str
    name: str
    description: str
    webhook_url: str
    signing_secret: str
    message_format: str
    enabled: bool
    is_default: bool
    last_test_status: str
    last_test_message: str
    last_test_time: str | None
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "platform": self.platform,
            "name": self.name,
            "description": self.description,
            "webhook_url": self.webhook_url,
            "signing_secret": self.signing_secret,
            "message_format": self.message_format,
            "enabled": self.enabled,
            "is_default": self.is_default,
            "last_test_status": self.last_test_status,
            "last_test_message": self.last_test_message,
            "last_test_time": self.last_test_time,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class MessageUserPreference:
    id: int
    tenant_id: int
    user_id: int
    message_type: str
    channels: list[str]
    quiet_hours: dict[str, Any]
    enabled: bool
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "message_type": self.message_type,
            "channels": self.channels,
            "quiet_hours": self.quiet_hours,
            "enabled": self.enabled,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
