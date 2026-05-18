from __future__ import annotations

import hashlib
import time
from typing import Any
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from audit_logging.application.dispatcher import record_api_log, record_visitor_log
from system.application.tenancy import current_tenant_scope_or_none
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
            tenant_id = request_tenant_id(request)
            client_ip = request.client.host if request.client else ""
            user_agent = request.headers.get("user-agent", "")
            referer = request.headers.get("referer", "")
            ip_digest = ip_hash(client_ip) if client_ip else ""
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
                    "referer": referer,
                    "user_agent": user_agent,
                    "summary": f"{request.method} {path} -> {status_code}",
                    "error_message": error_message,
                    "detail": {"ip_hash": ip_digest} if ip_digest else {},
                }
            )
            if should_record_visitor(path):
                record_visitor_log(
                    {
                        "tenant_id": tenant_id,
                        "event_action": f"{request.method} {path}",
                        "event_outcome": "success" if status_code < 400 else "failed",
                        "severity": "warning" if status_code >= 400 else "info",
                        "source_module": "http",
                        "request_id": current_request_id(),
                        "client_ip": client_ip,
                        "user_agent": user_agent,
                        "visitor_id": visitor_id(request, ip_digest),
                        "session_id_hash": session_id_hash(request),
                        "ip_hash": ip_digest,
                        "device_type": device_type(user_agent),
                        "referer": referer,
                        "entry_path": path,
                        "failure_reason": error_message if status_code >= 400 else "",
                        "summary": f"访客访问 {path}",
                        "detail": {"method": request.method, "status_code": status_code},
                    }
                )


def should_skip_path(path: str) -> bool:
    if path == "":
        return True
    return any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def should_record_visitor(path: str) -> bool:
    if path.startswith("/api/audit-logs"):
        return False
    if path.startswith("/api/"):
        return path.startswith("/api/auth/") or path.startswith("/api/tenant-auth/") or path.startswith("/api/login")
    return True


def request_tenant_id(request: Request) -> int:
    scope = getattr(request.state, "tenant_scope", None)
    if scope is None:
        scope = current_tenant_scope_or_none()
    return int(getattr(scope, "tenant_id", 0) or 0)


def ip_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def visitor_id(request: Request, ip_digest: str) -> str:
    explicit = request.cookies.get("visitor_id") or request.headers.get("X-Visitor-Id")
    if explicit:
        return hashlib.sha256(str(explicit).encode("utf-8")).hexdigest()
    basis = f"{ip_digest}:{request.headers.get('user-agent', '')}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest() if basis.strip(":") else str(uuid4())


def session_id_hash(request: Request) -> str:
    raw_session = (
        request.cookies.get("sessionid")
        or request.cookies.get("session")
        or request.cookies.get("access-token")
        or request.headers.get("Authorization", "")
    )
    return hashlib.sha256(str(raw_session).encode("utf-8")).hexdigest() if raw_session else ""


def device_type(user_agent: str) -> str:
    lowered = user_agent.lower()
    if any(token in lowered for token in ("mobile", "android", "iphone")):
        return "mobile"
    if any(token in lowered for token in ("ipad", "tablet")):
        return "tablet"
    if user_agent:
        return "desktop"
    return ""
