from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from system.interfaces.http import error_response


FIELD_LABELS = {
    "description": "description",
    "provider": "provider",
    "model": "model",
    "base_url": "base_url",
    "api_key": "api_key",
    "clear_api_key": "clear_api_key",
    "command": "command",
    "timeout_seconds": "timeout_seconds",
    "temperature": "temperature",
    "extra_body": "extra_body",
    "enabled": "enabled",
    "key": "key",
    "name": "name",
    "menu_keys": "menu_keys",
    "limit": "limit",
    "offset": "offset",
    "page": "page",
    "pageSize": "pageSize",
}

DETAIL_TRANSLATIONS = {
    "Invalid credentials": "Invalid credentials",
    "Not authenticated": "Not authenticated",
    "permission denied": "permission denied",
    "invalid api key": "invalid api key",
    "api key not found": "api key not found",
    "user is disabled": "user is disabled",
    "menu key already exists": "menu key already exists",
    "menu not found": "menu not found",
    "parent menu not found": "parent menu not found",
    "parent menu must be a directory": "parent menu must be a directory",
    "action parent menu must be a page": "action parent menu must be a page",
    "menu cannot be its own parent": "menu cannot be its own parent",
    "menu cannot move under its descendant": "menu cannot move under its descendant",
    "directory menu with children cannot become a page": "directory menu with children cannot become a page",
    "page menu path is required": "page menu path is required",
    "page menu component is required": "page menu component is required",
    "menu type must be directory or page": "menu type must be directory or page",
    "menu type must be directory, page or action": "menu type must be directory, page or action",
    "action menu parent is required": "action menu parent is required",
    "menu with children cannot become a page or action": "menu with children cannot become a page or action",
    "role key already exists": "role key already exists",
    "role not found": "role not found",
    "missing LLM config": "missing LLM config",
    "extra_body must be an object": "extra_body must be an object",
}


def friendly_detail(detail: Any) -> Any:
    if isinstance(detail, str):
        return translate_detail_text(detail)
    if isinstance(detail, list):
        return [friendly_detail(item) for item in detail]
    if isinstance(detail, dict):
        return {key: friendly_detail(value) for key, value in detail.items()}
    return detail


def translate_detail_text(message: str) -> str:
    stripped = message.strip()
    if stripped in DETAIL_TRANSLATIONS:
        return DETAIL_TRANSLATIONS[stripped]
    if stripped.startswith("database not found:"):
        return f"database file does not exist: {stripped.removeprefix('database not found:').strip()}"
    if stripped.startswith("database error:"):
        return f"database error: {stripped.removeprefix('database error:').strip()}"
    if stripped.startswith("unknown menu keys:"):
        return f"unknown menu keys: {stripped.removeprefix('unknown menu keys:').strip()}"
    if stripped.startswith("menu is assigned to roles:"):
        suffix = stripped.removeprefix("menu is assigned to roles:").strip()
        return f"menu is assigned to roles; unbind it before deleting: {suffix}"
    if stripped.startswith("menu structure is assigned to roles:"):
        suffix = stripped.removeprefix("menu structure is assigned to roles:").strip()
        return f"menu is assigned to roles; unbind it before changing structure: {suffix}"
    return stripped or "request failed"


def field_label(loc: tuple[Any, ...] | list[Any]) -> str:
    for part in reversed(loc):
        if isinstance(part, str) and part not in {"body", "query", "path"}:
            return FIELD_LABELS.get(part, part)
    return "payload"


def validation_error_message(error: dict[str, Any]) -> str:
    label = field_label(error.get("loc", ()))
    error_type = str(error.get("type", ""))
    ctx = error.get("ctx") if isinstance(error.get("ctx"), dict) else {}

    if error_type == "missing":
        return f"{label} is required"
    if error_type in {"string_too_short", "value_error.any_str.min_length"}:
        min_length = ctx.get("min_length") or ctx.get("limit_value")
        return f"{label} is required" if min_length == 1 else f"{label} must have at least {min_length} characters"
    if error_type in {"string_too_long", "value_error.any_str.max_length"}:
        return f"{label} must have at most {ctx.get('max_length') or ctx.get('limit_value')} characters"
    if error_type in {"greater_than_equal", "value_error.number.not_ge"}:
        return f"{label} must be greater than or equal to {ctx.get('ge') or ctx.get('limit_value')}"
    if error_type in {"less_than_equal", "value_error.number.not_le"}:
        return f"{label} must be less than or equal to {ctx.get('le') or ctx.get('limit_value')}"
    if error_type in {"greater_than", "value_error.number.not_gt"}:
        return f"{label} must be greater than {ctx.get('gt') or ctx.get('limit_value')}"
    if error_type in {"less_than", "value_error.number.not_lt"}:
        return f"{label} must be less than {ctx.get('lt') or ctx.get('limit_value')}"

    message = str(error.get("msg", "")).strip()
    if message.startswith("Value error,"):
        message = message.removeprefix("Value error,").strip()
    return translate_detail_text(message) if message else f"{label} is invalid"


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(part) for part in error.get("loc", []) if part != "body"),
            "message": validation_error_message(error),
        }
        for error in exc.errors()
    ]
    message = errors[0]["message"] if errors else "Validation error"
    return error_response(status_code=422, code="VALIDATION_ERROR", message=message, errors=errors)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_by_status = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    return error_response(
        status_code=exc.status_code,
        code=code_by_status.get(exc.status_code, "HTTP_ERROR"),
        message=str(friendly_detail(exc.detail)),
    )
