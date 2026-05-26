from __future__ import annotations

import base64
import re
from typing import Any


VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
MEDIA_VARIABLE_TYPES = {"image", "file", "audio", "video"}
BINARY_MEDIA_VARIABLE_TYPES = {"image", "audio", "video"}
SUPPORTED_IMAGE_DATA_URL_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


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
    if isinstance(value, list):
        return not value
    return value in (None, "")


def variable_text(value: Any) -> str:
    if isinstance(value, list) and all(is_media_variable(item) for item in value):
        return "\n".join(variable_text(item) for item in value)
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
        if is_media_variable_list(value):
            for index, item in enumerate(value, start=1):
                part = media_content_part(f"{key}_{index}", item)
                if part:
                    parts.append(part)
            continue
        if is_media_variable(value):
            part = media_content_part(str(key), value)
            if part:
                parts.append(part)
    return parts


def media_content_part(key: str, value: dict[str, Any]) -> dict[str, Any] | None:
    media_type = str(value.get("type") or "file").strip().lower()
    media_url = str(value.get("data_url") or value.get("preview_url") or value.get("url") or "").strip()
    name = str(value.get("name") or key)
    mime_type = str(value.get("mime_type") or "")
    text = str(value.get("text") or "")
    if text:
        return {"type": "text", "text": f"\n\n附件 {name} 内容：\n{text}"}
    if not media_url:
        return {"type": "text", "text": variable_text(value)}
    if media_type == "image":
        normalized = normalize_image_data_url(media_url)
        if not normalized:
            return {"type": "text", "text": variable_text(value)}
        return {"type": "image_url", "image_url": {"url": normalized}}
    if media_type == "audio":
        if not media_url.startswith("data:"):
            return {"type": "text", "text": variable_text(value)}
        return {
            "type": "input_audio",
            "input_audio": {
                "data": data_url_payload(media_url),
                "format": media_format(name, mime_type, "mp3"),
            },
        }
    if media_type == "video":
        return {"type": "video_url", "video_url": {"url": media_url}}
    return None


def contains_binary_media(value: Any) -> bool:
    if is_binary_media_variable(value):
        return True
    if isinstance(value, dict):
        return any(contains_binary_media(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_binary_media(item) for item in value)
    return False


def is_media_variable(value: Any) -> bool:
    return isinstance(value, dict) and str(value.get("type") or "").strip().lower() in MEDIA_VARIABLE_TYPES


def is_media_variable_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(is_media_variable(item) for item in value)


def is_binary_media_variable(value: Any) -> bool:
    return isinstance(value, dict) and str(value.get("type") or "").strip().lower() in BINARY_MEDIA_VARIABLE_TYPES


def data_url_payload(data_url: str) -> str:
    return data_url.split(",", 1)[1] if "," in data_url else data_url


def normalize_image_data_url(media_url: str) -> str:
    if not media_url.startswith("data:"):
        return media_url if media_url.startswith(("http://", "https://")) else ""
    if "," not in media_url:
        return ""
    header, payload = media_url.split(",", 1)
    metadata = header[5:].split(";")
    mime_type = metadata[0].strip().lower()
    if mime_type not in SUPPORTED_IMAGE_DATA_URL_MIME_TYPES or "base64" not in {item.strip().lower() for item in metadata[1:]}:
        return ""
    try:
        base64.b64decode(payload, validate=True)
    except Exception:
        return ""
    return media_url


def media_format(name: str, mime_type: str, fallback: str) -> str:
    if "/" in mime_type:
        return mime_type.rsplit("/", 1)[1].split(";", 1)[0] or fallback
    if "." in name:
        return name.rsplit(".", 1)[1].lower() or fallback
    return fallback
