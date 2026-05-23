from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from messaging.application import services
from messaging.infrastructure.chat_bot_delivery import WebhookChatBotSender
from messaging.infrastructure.persistence.bootstrap import ensure_messaging_schema
from messaging.infrastructure.persistence import repositories
from messaging.interfaces.http.router import router

services.configure_repository(repositories)
services.configure_chat_bot_sender(WebhookChatBotSender())


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {"messaging": ensure_messaging_schema}
