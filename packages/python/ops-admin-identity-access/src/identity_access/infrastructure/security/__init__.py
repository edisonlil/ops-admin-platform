from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from fastapi import Response
from fastapi_login import LoginManager
from pwdlib import PasswordHash

from identity_access.infrastructure.config import auth_secret


ACCESS_TOKEN_EXPIRE_SECONDS = 8 * 60 * 60
API_KEY_PREFIX = "fgak_"
COOKIE_NAME = "fg_agent_access_token"

password_hash = PasswordHash.recommended()
login_manager = LoginManager(auth_secret(), token_url="/api/auth/token", use_cookie=True)
login_manager.cookie_name = COOKIE_NAME


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(
    username: str,
    *,
    tenant_id: int | None = None,
    auth_scope: str = "tenant",
    user_id: int | None = None,
) -> str:
    payload = {"sub": username}
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if auth_scope:
        payload["auth_scope"] = auth_scope
    if user_id is not None:
        payload["user_id"] = user_id
    return login_manager.create_access_token(
        data=payload,
        expires=timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS),
    )


def set_login_cookie(response: Response, token: str) -> None:
    login_manager.set_cookie(response, token)


def clear_login_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, httponly=True, samesite="lax")


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
