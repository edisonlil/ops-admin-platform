from __future__ import annotations

import contextvars
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from system.application.tenancy import clear_tenant_scope, reset_tenant_scope


request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def current_request_id() -> str:
    return request_id_var.get() or f"req_{uuid4().hex}"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def ok(data: Any = None, *, code: str = "OK", message: str = "success") -> dict[str, Any]:
    return {
        "success": True,
        "code": code,
        "message": message,
        "data": {} if data is None else data,
        "request_id": current_request_id(),
        "timestamp": now_iso(),
    }


def page(items: list[dict[str, Any]], *, page: int, page_size: int, total: int) -> dict[str, Any]:
    return ok({"items": items, "pagination": {"page": page, "page_size": page_size, "total": total}})


def error_response(
    *,
    message: str,
    code: str = "INTERNAL_ERROR",
    status_code: int = 500,
    errors: list[dict[str, Any]] | None = None,
    data: Any = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "success": False,
        "code": code,
        "message": message,
        "data": data,
        "detail": message,
        "request_id": current_request_id(),
        "timestamp": now_iso(),
    }
    if errors:
        payload["errors"] = errors
    return JSONResponse(status_code=status_code, content=payload)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        token = request_id_var.set(request_id)
        tenant_token = clear_tenant_scope()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            reset_tenant_scope(tenant_token)
            request_id_var.reset(token)
