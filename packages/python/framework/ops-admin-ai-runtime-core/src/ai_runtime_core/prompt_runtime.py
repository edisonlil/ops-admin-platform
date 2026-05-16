from __future__ import annotations

import re
from typing import Any


VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
MEDIA_VARIABLE_TYPES = {"image", "file", "audio", "video"}


def render_template(template: str, variables: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return variable_text(resolve_variable_value(variables, name))

    return VARIABLE_PATTERN.sub(replace, template)


def resolve_variable_value(variables: dict[str, Any], name: str) -> Any:
    if name in variables:
        return variables.get(name)
    current: Any = variables
    for part in name.split("."):
        if not isinstance(current, dict) or part not in current:
            return ""
        current = current.get(part)
    return current


def variable_missing(value: Any) -> bool:
    return value in (None, "")


def variable_text(value: Any) -> str:
    if is_media_variable(value):
        media_type = str(value.get("type") or "file")
        name = str(value.get("name") or "未命名附件")
        mime_type = str(value.get("mime_type") or "")
        size = int(value.get("size") or 0)
        if value.get("text"):
            return str(value["text"])
        return f"[已上传{media_type}：{name}，{mime_type}，{size} bytes]"
    return str(value or "")


def media_content_parts(variables: dict[str, Any]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for key, value in variables.items():
        if is_media_variable(value):
            part = media_content_part(str(key), value)
            if part:
                parts.append(part)
    return parts


def media_content_part(key: str, value: dict[str, Any]) -> dict[str, Any] | None:
    media_type = str(value.get("type") or "file").strip().lower()
    data_url = str(value.get("data_url") or "").strip()
    name = str(value.get("name") or key)
    mime_type = str(value.get("mime_type") or "")
    text = str(value.get("text") or "")
    if text:
        return {"type": "text", "text": f"\n\n附件 {name} 内容：\n{text}"}
    if not data_url:
        return {"type": "text", "text": variable_text(value)}
    if media_type == "image":
        return {"type": "image_url", "image_url": {"url": data_url}}
    if media_type == "audio":
        return {
            "type": "input_audio",
            "input_audio": {
                "data": data_url_payload(data_url),
                "format": media_format(name, mime_type, "mp3"),
            },
        }
    if media_type == "video":
        return {"type": "video_url", "video_url": {"url": data_url}}
    if media_type == "file":
        return {"type": "file", "file": {"filename": name, "file_data": data_url}}
    return None


def is_media_variable(value: Any) -> bool:
    return isinstance(value, dict) and str(value.get("type") or "").strip().lower() in MEDIA_VARIABLE_TYPES


def data_url_payload(data_url: str) -> str:
    return data_url.split(",", 1)[1] if "," in data_url else data_url


def media_format(name: str, mime_type: str, fallback: str) -> str:
    if "/" in mime_type:
        return mime_type.rsplit("/", 1)[1].split(";", 1)[0] or fallback
    if "." in name:
        return name.rsplit(".", 1)[1].lower() or fallback
    return fallback
