from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from identity_access.application.ports import IdentityAccessRepository, IdentityAccessSecurityPort


repository: IdentityAccessRepository | None = None
security: IdentityAccessSecurityPort | None = None


def configure_repository(identity_repository: IdentityAccessRepository) -> None:
    global repository
    repository = identity_repository


def configure_security(identity_security: IdentityAccessSecurityPort) -> None:
    global security
    security = identity_security


def repo() -> IdentityAccessRepository:
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identity_access repository is not configured",
        )
    return repository


def secure() -> IdentityAccessSecurityPort:
    if security is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identity_access security is not configured",
        )
    return security


class DisabledUserException(Exception):
    pass


PASSWORD_IDENTIFIER_METHOD = "password_identifier"


def load_user(username: str) -> dict[str, Any] | None:
    row = repo().user_by_username(username)
    if not row or not bool(row.get("is_active", True)):
        return None
    public = repo().public_user(row)
    public["id"] = int(row.get("id", 0) or 0)
    public["is_superuser"] = bool(row.get("is_superuser", False))
    return public


def authenticate_user(username: str, password: str, tenant_id: int | None = None) -> dict[str, Any] | None:
    """Authenticate the password_identifier method: tenant + username/email + password.

    Future methods such as phone OTP or OAuth providers should get separate
    application handlers instead of adding provider-specific logic here.
    """
    return repo().authenticate_user(username, password, tenant_id=tenant_id)


def authenticate_platform_admin(username: str, password: str) -> dict[str, Any] | None:
    """Authenticate platform password_identifier credentials."""
    return repo().authenticate_platform_admin(username, password)


def user_by_username(username: str, tenant_id: int | None = None) -> dict[str, Any] | None:
    return repo().user_by_username(username, tenant_id=tenant_id)


def platform_user_by_username(username: str) -> dict[str, Any] | None:
    return repo().platform_user_by_username(username)


def get_user(user_id: int) -> dict[str, Any] | None:
    return repo().get_user(user_id)


def update_own_profile(
    user_id: int,
    *,
    full_name: str,
    email: str | None = None,
    current_password: str = "",
    new_password: str = "",
) -> dict[str, Any]:
    return repo().update_own_profile(
        user_id,
        full_name=full_name,
        email=email,
        current_password=current_password,
        new_password=new_password,
    )


def public_user(
    row: dict[str, Any],
    *,
    tenant_id: int | None = None,
    auth_scope: str | None = None,
    is_tenant_admin: bool = False,
) -> dict[str, Any]:
    return repo().public_user(
        row,
        tenant_id=tenant_id,
        auth_scope=auth_scope,
        is_tenant_admin=is_tenant_admin,
    )


def create_access_token(
    username: str,
    *,
    tenant_id: int | None = None,
    auth_scope: str = "tenant",
    user_id: int | None = None,
) -> str:
    return secure().create_access_token(
        username,
        tenant_id=tenant_id,
        auth_scope=auth_scope,
        user_id=user_id,
    )


def set_login_cookie(response: Any, token: str) -> None:
    secure().set_login_cookie(response, token)


def clear_login_cookie(response: Any) -> None:
    secure().clear_login_cookie(response)


def access_token_expire_seconds() -> int:
    return int(secure().ACCESS_TOKEN_EXPIRE_SECONDS)
