from __future__ import annotations

import hashlib
import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from audit_logging.application.dispatcher import record_api_log
from system.application.tenancy import current_tenant_scope
from system.interfaces.http import current_request_id


EXCLUDED_PREFIXES = (
    "/api/audit-logs",
    "/api/health",
    "/assets",
    "/app.config.js",
)


class AuditHttpLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        path = request.url.path
        if should_skip_path(path):
            return await call_next(request)

        started = time.perf_counter()
        status_code = 500
        error_message = ""
        try:
            response = await call_next(request)
            status_code = int(getattr(response, "status_code", 0) or 0)
            return response
        except Exception as exc:
            error_message = str(exc)
            raise
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            tenant_id = int(getattr(current_tenant_scope(), "tenant_id", 0) or 0)
            client_ip = request.client.host if request.client else ""
            record_api_log(
                {
                    "tenant_id": tenant_id,
                    "event_action": f"{request.method} {path}",
                    "event_outcome": "success" if status_code < 400 else "failed",
                    "severity": "error" if status_code >= 500 else ("warning" if status_code >= 400 else "info"),
                    "source_module": "http",
                    "request_id": current_request_id(),
                    "client_ip": client_ip,
                    "request_method": request.method,
                    "request_path": path,
                    "query_summary": dict(request.query_params),
                    "status_code": status_code,
                    "success": status_code < 400,
                    "duration_ms": duration_ms,
                    "request_size_bytes": int(request.headers.get("content-length") or 0),
                    "response_size_bytes": 0,
                    "referer": request.headers.get("referer", ""),
                    "user_agent": request.headers.get("user-agent", ""),
                    "summary": f"{request.method} {path} -> {status_code}",
                    "error_message": error_message,
                    "detail": {"ip_hash": ip_hash(client_ip)} if client_ip else {},
                }
            )


def should_skip_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    return any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def ip_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
