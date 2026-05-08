from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from fastapi_login.exceptions import InvalidCredentialsException

from identity_access.application.api_key_service import validate_api_key
from identity_access.application.auth_service import load_user
from identity_access.infrastructure.persistence.common import DEFAULT_TENANT_KEY
from identity_access.infrastructure.security import COOKIE_NAME, login_manager
from identity_access.application import tenant_service
from system.application.tenancy import set_tenant_scope
from system.domain.tenancy import TenantScope


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_header = HTTPBearer(auto_error=False)

# Importing load_user registers the LoginManager user loader for the legacy
# OAuth dependency path. Tenant-aware routes decode the token explicitly below.
_ = load_user


def _token_from_request(request: Request) -> str:
    authorization = request.headers.get("Authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token

    token_header = request.headers.get("token", "").strip()
    if token_header:
        return token_header

    cookie_token = request.cookies.get(COOKIE_NAME) or request.cookies.get(login_manager.cookie_name)
    if cookie_token:
        return cookie_token

    raise InvalidCredentialsException


def _user_and_payload_from_request(request: Request) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = login_manager._get_payload(_token_from_request(request))
    username = str(payload.get("sub", "")).strip()
    if not username:
        raise InvalidCredentialsException
    raw_tenant_id = payload.get("tenant_id")
    try:
        tenant_id = int(raw_tenant_id) if raw_tenant_id else None
    except (TypeError, ValueError):
        raise InvalidCredentialsException from None
    auth_scope = str(payload.get("auth_scope") or "tenant")
    current_user = tenant_service.load_user_for_tenant(username, tenant_id, auth_scope=auth_scope)
    if not current_user or not bool(current_user.get("is_active", True)):
        raise InvalidCredentialsException
    if not payload.get("auth_scope") and bool(current_user.get("is_superuser", False)):
        auth_scope = "platform"
        current_user = tenant_service.load_user_for_tenant(username, tenant_id, auth_scope=auth_scope)
        if not current_user or not bool(current_user.get("is_active", True)):
            raise InvalidCredentialsException
        payload["auth_scope"] = auth_scope
    return current_user, payload


def _attach_user_tenant_scope(current_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    raw_tenant_id = payload.get("tenant_id")
    try:
        tenant_id = int(raw_tenant_id) if raw_tenant_id else None
    except (TypeError, ValueError):
        raise InvalidCredentialsException from None

    tenant_payload = tenant_service.tenant_access_payload(current_user, tenant_id)
    current = tenant_payload["current_tenant"]
    if current:
        set_tenant_scope(
            TenantScope(
                tenant_id=int(current["id"]),
                tenant_key=str(current["tenant_key"]),
                tenant_name=str(current["name"]),
                is_platform_admin=bool(tenant_payload["is_platform_admin"]),
                source="user",
                principal_id=int(current_user.get("id", 0) or 0),
            )
        )
    current_user.update(tenant_payload)
    current_user["tenant_id"] = int(current["id"]) if current else None
    return current_user


async def require_user(request: Request) -> dict[str, Any]:
    current_user, payload = _user_and_payload_from_request(request)
    if not bool(current_user.get("is_active", True)):
        raise InvalidCredentialsException
    return _attach_user_tenant_scope(current_user, payload)


def require_permission(permission_code: str) -> Any:
    async def dependency(current_user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        if bool(current_user.get("is_platform_admin", False)):
            return current_user
        if permission_code in set(current_user.get("permissions", [])):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")

    return dependency


def require_business_api_key_or_permission(permission_code: str) -> Any:
    async def dependency(
        request: Request,
        api_key: str | None = Security(api_key_header),
        _: HTTPAuthorizationCredentials | None = Security(bearer_header),
    ) -> dict[str, Any]:
        if api_key:
            principal = validate_api_key(api_key)
            if principal:
                tenant = principal.get("current_tenant") or {}
                set_tenant_scope(
                    TenantScope(
                        tenant_id=int(principal.get("tenant_id", tenant.get("id", 0)) or 0),
                        tenant_key=str(tenant.get("tenant_key") or tenant.get("key") or DEFAULT_TENANT_KEY),
                        tenant_name=str(tenant.get("name") or "Default Tenant"),
                        source="api_key",
                        principal_id=int((principal.get("api_key") or {}).get("id", 0) or 0),
                    )
                )
                return principal
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
        return await require_permission(permission_code)(await require_user(request))

    return dependency


async def require_auth(
    request: Request,
    api_key: str | None = Security(api_key_header),
    _: HTTPAuthorizationCredentials | None = Security(bearer_header),
) -> dict[str, Any]:
    if api_key:
        principal = validate_api_key(api_key)
        if principal:
            tenant = principal.get("current_tenant") or {}
            set_tenant_scope(
                TenantScope(
                    tenant_id=int(principal.get("tenant_id", tenant.get("id", 0)) or 0),
                    tenant_key=str(tenant.get("tenant_key") or tenant.get("key") or DEFAULT_TENANT_KEY),
                    tenant_name=str(tenant.get("name") or "Default Tenant"),
                    source="api_key",
                    principal_id=int((principal.get("api_key") or {}).get("id", 0) or 0),
                )
            )
            return principal
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
    user, payload = _user_and_payload_from_request(request)
    user = _attach_user_tenant_scope(user, payload)
    tenant_payload = {
        "current_tenant": user["current_tenant"],
        "tenant_memberships": user["tenant_memberships"],
        "is_platform_admin": user["is_platform_admin"],
    }
    return {"auth_type": "user", "user": user, **tenant_payload}


async def require_platform_admin(current_user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if bool(current_user.get("is_platform_admin", False)):
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="platform admin required")


def require_tenant_admin_for_path(param_name: str = "tenant_id") -> Any:
    async def dependency(request: Request, current_user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        tenant_id = int(request.path_params.get(param_name, 0) or 0)
        tenant_service.ensure_tenant_admin_access(current_user, tenant_id)
        return current_user

    return dependency


async def require_current_tenant_admin(current_user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    current = current_user.get("current_tenant") or {}
    tenant_id = int(current.get("id", 0) or 0)
    tenant_service.ensure_tenant_admin_access(current_user, tenant_id)
    return current_user
