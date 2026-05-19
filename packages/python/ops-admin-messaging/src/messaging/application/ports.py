from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RecipientProfile:
    user_id: int
    username: str
    tenant_id: int


class RecipientDirectoryPort(Protocol):
    def resolve_users(self, tenant_id: int, target: dict[str, Any]) -> list[RecipientProfile]:
        ...


@dataclass(frozen=True)
class ChatBotDeliveryResult:
    ok: bool
    status_code: int
    message: str
    request: dict[str, Any]
    response: dict[str, Any]


class ChatBotSenderPort(Protocol):
    def send(self, *, chat_bot: Any, title: str, content: str) -> ChatBotDeliveryResult:
        ...


class UnavailableChatBotSender:
    def send(self, *, chat_bot: Any, title: str, content: str) -> ChatBotDeliveryResult:
        return ChatBotDeliveryResult(
            ok=False,
            status_code=0,
            message="群聊机器人发送适配器尚未接入",
            request={"chat_bot_id": getattr(chat_bot, "id", None), "title": title, "content": content},
            response={},
        )
