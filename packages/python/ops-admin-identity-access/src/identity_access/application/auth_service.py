from __future__ import annotations

from typing import Any

from identity_access.infrastructure.persistence import repositories
from identity_access.infrastructure.security import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    clear_login_cookie,
    create_access_token,
    login_manager,
    set_login_cookie,
)


DisabledUserException = repositories.DisabledUserException


PASSWORD_IDENTIFIER_METHOD = "password_identifier"


@login_manager.user_loader()
def load_user(username: str) -> dict[str, Any] | None:
    row = repositories.user_by_username(username)
    if not row or not bool(row.get("is_active", True)):
        return None
    public = repositories.public_user(row)
    public["id"] = int(row.get("id", 0) or 0)
    public["is_superuser"] = bool(row.get("is_superuser", False))
    return public


def authenticate_user(username: str, password: str, tenant_id: int | None = None) -> dict[str, Any] | None:
    """Authenticate the password_identifier method: tenant + username/email + password.

    Future methods such as phone OTP or OAuth providers should get separate
    application handlers instead of adding provider-specific logic here.
    """
    return repositories.authenticate_user(username, password, tenant_id=tenant_id)


def authenticate_platform_admin(username: str, password: str) -> dict[str, Any] | None:
    """Authenticate platform password_identifier credentials."""
    return repositories.authenticate_platform_admin(username, password)


def user_by_username(username: str, tenant_id: int | None = None) -> dict[str, Any] | None:
    return repositories.user_by_username(username, tenant_id=tenant_id)


def platform_user_by_username(username: str) -> dict[str, Any] | None:
    return repositories.platform_user_by_username(username)


def get_user(user_id: int) -> dict[str, Any] | None:
    return repositories.get_user(user_id)


def update_own_profile(
    user_id: int,
    *,
    full_name: str,
    email: str | None = None,
    current_password: str = "",
    new_password: str = "",
) -> dict[str, Any]:
    return repositories.update_own_profile(
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
    return repositories.public_user(
        row,
        tenant_id=tenant_id,
        auth_scope=auth_scope,
        is_tenant_admin=is_tenant_admin,
    )
