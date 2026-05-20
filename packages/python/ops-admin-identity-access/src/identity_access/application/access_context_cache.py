from __future__ import annotations

import copy
import os
import time
from threading import RLock
from typing import Any


AccessContextKey = tuple[str, int | None, str, str]

_DEFAULT_TTL_SECONDS = 300
_MAX_ENTRIES = 1024
_lock = RLock()
_cache: dict[AccessContextKey, tuple[float, dict[str, Any]]] = {}


def _ttl_seconds() -> int:
    raw = os.getenv("OPS_ADMIN_ACCESS_CONTEXT_CACHE_TTL_SECONDS", str(_DEFAULT_TTL_SECONDS))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_TTL_SECONDS
    return max(0, value)


def _key(username: str, tenant_id: int | None, auth_scope: str, namespace: str) -> AccessContextKey:
    normalized_username = username.strip().lower()
    normalized_scope = (auth_scope or "tenant").strip().lower()
    return normalized_username, int(tenant_id) if tenant_id else None, normalized_scope, namespace.strip()


def get_access_context(
    username: str,
    tenant_id: int | None,
    auth_scope: str,
    *,
    namespace: str = "",
) -> dict[str, Any] | None:
    ttl = _ttl_seconds()
    if ttl <= 0:
        return None
    cache_key = _key(username, tenant_id, auth_scope, namespace)
    now = time.monotonic()
    with _lock:
        cached = _cache.get(cache_key)
        if not cached:
            return None
        expires_at, payload = cached
        if expires_at <= now:
            _cache.pop(cache_key, None)
            return None
        return copy.deepcopy(payload)


def set_access_context(
    username: str,
    tenant_id: int | None,
    auth_scope: str,
    payload: dict[str, Any],
    *,
    namespace: str = "",
) -> None:
    ttl = _ttl_seconds()
    if ttl <= 0:
        return
    cache_key = _key(username, tenant_id, auth_scope, namespace)
    with _lock:
        if len(_cache) >= _MAX_ENTRIES:
            oldest_key = min(_cache.items(), key=lambda item: item[1][0])[0]
            _cache.pop(oldest_key, None)
        _cache[cache_key] = (time.monotonic() + ttl, copy.deepcopy(payload))


def clear_access_context_cache() -> None:
    with _lock:
        _cache.clear()
