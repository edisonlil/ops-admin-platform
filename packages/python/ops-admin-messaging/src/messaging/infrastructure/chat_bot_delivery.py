from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from messaging.application.ports import ChatBotDeliveryResult
from messaging.domain.models import MessageChatBot


CHAT_BOT_PLATFORM_LABELS = {
    "wps": "WPS协作",
    "wecom": "企业微信",
    "feishu": "飞书",
    "dingtalk": "钉钉",
}

SUPPORTED_CHAT_BOT_PLATFORMS = tuple(CHAT_BOT_PLATFORM_LABELS)


class WebhookChatBotSender:
    def __init__(self, *, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def send(self, *, chat_bot: MessageChatBot, title: str, content: str) -> ChatBotDeliveryResult:
        return send_chat_bot_message(
            chat_bot=chat_bot,
            title=title,
            content=content,
            timeout_seconds=self.timeout_seconds,
        )


def send_chat_bot_message(*, chat_bot: MessageChatBot, title: str, content: str, timeout_seconds: int = 10) -> ChatBotDeliveryResult:
    payload = build_platform_payload(chat_bot=chat_bot, title=title, content=content)
    url = webhook_url_with_signature(chat_bot)
    request_payload = {
        "platform": chat_bot.platform,
        "chat_bot_id": chat_bot.id,
        "chat_bot_name": chat_bot.name,
        "url": mask_webhook_url(chat_bot.webhook_url),
        "body": payload,
    }
    try:
        response = post_json(url=url, payload=payload, timeout_seconds=timeout_seconds)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        parsed = decode_json(body)
        return ChatBotDeliveryResult(False, int(exc.code), parsed_message(parsed, body), request_payload, parsed or {"raw": body})
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        return ChatBotDeliveryResult(False, 0, reason, request_payload, {"error": reason})

    ok = response_ok(chat_bot.platform, response)
    return ChatBotDeliveryResult(
        ok=ok,
        status_code=200,
        message=parsed_message(response, "发送成功" if ok else "机器人平台返回失败"),
        request=request_payload,
        response=response,
    )


def build_platform_payload(*, chat_bot: MessageChatBot, title: str, content: str) -> dict[str, Any]:
    text = format_message_text(title=title, content=content)
    if chat_bot.platform == "feishu":
        payload = {"msg_type": "text", "content": {"text": text}}
        if chat_bot.signing_secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = feishu_sign(timestamp, chat_bot.signing_secret)
        return payload
    if chat_bot.platform == "dingtalk":
        return {"msgtype": "text", "text": {"content": text}}
    if chat_bot.platform == "wecom":
        return {"msgtype": "text", "text": {"content": text}}
    if chat_bot.platform == "wps":
        return {"msgtype": "text", "text": {"content": text}}
    return {"msgtype": "text", "text": {"content": text}}


def webhook_url_with_signature(chat_bot: MessageChatBot) -> str:
    if chat_bot.platform != "dingtalk" or not chat_bot.signing_secret:
        return chat_bot.webhook_url
    timestamp = str(int(time.time() * 1000))
    secret = chat_bot.signing_secret
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    sign = urllib.parse.quote_plus(base64.b64encode(hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).digest()))
    separator = "&" if "?" in chat_bot.webhook_url else "?"
    return f"{chat_bot.webhook_url}{separator}timestamp={timestamp}&sign={sign}"


def feishu_sign(timestamp: str, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    return base64.b64encode(hmac.new(string_to_sign, b"", digestmod=hashlib.sha256).digest()).decode("utf-8")


def post_json(*, url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="replace")
    return decode_json(body) or {"raw": body}


def response_ok(platform: str, response: dict[str, Any]) -> bool:
    if not response:
        return True
    if platform == "feishu":
        return response.get("StatusCode") in (None, 0) and response.get("code", 0) in (0, None)
    if platform in {"dingtalk", "wecom", "wps"}:
        errcode = response.get("errcode")
        code = response.get("code")
        return (errcode in (0, None)) and (code in (0, None))
    return response.get("errcode", 0) in (0, None) and response.get("code", 0) in (0, None)


def parsed_message(response: dict[str, Any], fallback: str) -> str:
    for key in ("errmsg", "msg", "message", "StatusMessage"):
        value = response.get(key)
        if value:
            return str(value)
    return fallback


def decode_json(value: str) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def format_message_text(*, title: str, content: str) -> str:
    title = title.strip()
    content = content.strip()
    if title and content:
        return f"{title}\n{content}"
    return title or content


def mask_webhook_url(webhook_url: str) -> str:
    if not webhook_url:
        return ""
    if len(webhook_url) <= 18:
        return "******"
    return f"{webhook_url[:12]}******{webhook_url[-6:]}"
