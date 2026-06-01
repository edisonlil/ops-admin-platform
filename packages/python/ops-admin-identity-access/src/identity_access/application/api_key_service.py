from __future__ import annotations

from typing import Any

from identity_access.application import auth_service, tenant_service
from fastapi import HTTPException, status

from identity_access.application.ports import IdentityAccessRepository
from system.application.data_access import (
    ResourceDescriptor,
    SCOPE_CUSTOM_DEPARTMENTS,
    SCOPE_DEPARTMENT,
    SCOPE_DEPARTMENT_AND_CHILDREN,
    SCOPE_SELF,
    SCOPE_SELF_AND_SUBORDINATES,
    SCOPE_TENANT,
    current_user_primary_department_id,
    resolve_data_access_filter,
)


API_KEY_RESOURCE = ResourceDescriptor(resource_key="identity.api-key")
repository: IdentityAccessRepository | None = None


def configure_repository(identity_repository: IdentityAccessRepository) -> None:
    global repository
    repository = identity_repository


def repo() -> IdentityAccessRepository:
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identity_access repository is not configured",
        )
    return repository


def create_api_key(
    *,
    name: str,
    creator: str,
    tenant_id: int | None = None,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return repo().create_api_key(
        name=name,
        creator=creator,
        tenant_id=tenant_id,
        owner_user_id=current_user_id_or_none(current_user or {}),
        owner_department_id=current_user_primary_department_id(current_user or {}),
    )


def list_api_keys(
    tenant_id: int | None = None,
    current_user: dict[str, Any] | None = None,
    *,
    owner_user_id: int | None = None,
    keyword: str | None = None,
    is_active: bool | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> list[dict[str, Any]]:
    data_scope = api_key_data_scope(current_user)
    return repo().list_api_keys(
        tenant_id=tenant_id,
        data_scope=data_scope,
        owner_user_id=owner_user_id,
        keyword=keyword,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def list_api_keys_page(
    tenant_id: int | None = None,
    current_user: dict[str, Any] | None = None,
    *,
    owner_user_id: int | None = None,
    keyword: str | None = None,
    is_active: bool | None = None,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    data_scope = api_key_data_scope(current_user)
    return repo().list_api_keys_page(
        tenant_id=tenant_id,
        data_scope=data_scope,
        owner_user_id=owner_user_id,
        keyword=keyword,
        is_active=is_active,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def api_key_data_scope(current_user: dict[str, Any] | None) -> Any:
    return (
        resolve_data_access_filter(current_user=current_user, resource=API_KEY_RESOURCE, action="read")
        if current_user is not None
        else None
    )


def api_key_filter_capabilities(
    *,
    tenant_id: int,
    current_user: dict[str, Any],
    q: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    data_scope = api_key_data_scope(current_user)
    owner_options = api_key_owner_options_for_scope(
        tenant_id=tenant_id,
        current_user=current_user,
        data_scope=data_scope,
        q=q,
        page=page,
        page_size=page_size,
    )
    owner_total = int(owner_options["pagination"]["total"])
    if q:
        unfiltered_owner_options = api_key_owner_options_for_scope(
            tenant_id=tenant_id,
            current_user=current_user,
            data_scope=data_scope,
            page=1,
            page_size=1,
        )
        owner_total = int(unfiltered_owner_options["pagination"]["total"])
    return {
        "access_mode": "owner_columns",
        "owner_filter_label": "所属人员",
        "scope": getattr(data_scope, "scope", "tenant") if data_scope is not None else "tenant",
        "can_filter_owner": owner_total > 1,
        "owner_options": owner_options["items"],
        "owner_options_pagination": owner_options["pagination"],
    }


def api_key_owner_options_for_scope(
    *,
    tenant_id: int,
    current_user: dict[str, Any],
    data_scope: Any,
    q: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    users = tenant_service.list_tenant_users(tenant_id)
    visible_users = visible_owner_users(current_user=current_user, users=users, data_scope=data_scope)
    keyword = (q or "").strip().lower()
    if keyword:
        visible_users = [
            user
            for user in visible_users
            if keyword in str(user.get("username", "")).lower()
            or keyword in str(user.get("full_name", "")).lower()
            or keyword in str(user.get("email", "")).lower()
        ]
    visible_users = sorted(visible_users, key=lambda item: (str(item.get("username", "")), int(item.get("id", 0) or 0)))
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, min(100, int(page_size or 100)))
    start = (safe_page - 1) * safe_page_size
    page_users = visible_users[start:start + safe_page_size]
    return {
        "items": [owner_option(user) for user in page_users],
        "pagination": {"page": safe_page, "page_size": safe_page_size, "total": len(visible_users)},
    }


def visible_owner_users(*, current_user: dict[str, Any], users: list[dict[str, Any]], data_scope: Any) -> list[dict[str, Any]]:
    scope = str(getattr(data_scope, "scope", SCOPE_TENANT) or SCOPE_TENANT)
    if scope == "deny":
        return []
    if scope == SCOPE_TENANT:
        return users
    if scope == SCOPE_SELF:
        user_id = int(getattr(data_scope, "user_id", 0) or current_user_id_or_none(current_user) or 0)
        return [user for user in users if int(user.get("id", 0) or 0) == user_id]
    if scope == SCOPE_SELF_AND_SUBORDINATES:
        user_ids = {int(value) for value in getattr(data_scope, "user_ids", ()) if int(value)}
        if not user_ids:
            user_id = int(getattr(data_scope, "user_id", 0) or current_user_id_or_none(current_user) or 0)
            user_ids = {user_id} if user_id else set()
        return [user for user in users if int(user.get("id", 0) or 0) in user_ids]
    if scope in {SCOPE_DEPARTMENT, SCOPE_DEPARTMENT_AND_CHILDREN, SCOPE_CUSTOM_DEPARTMENTS}:
        department_ids = {int(value) for value in getattr(data_scope, "department_ids", ()) if int(value)}
        if not department_ids:
            return []
        return [user for user in users if user_in_departments(user, department_ids)]
    return []


def user_in_departments(user: dict[str, Any], department_ids: set[int]) -> bool:
    for department in user.get("departments") or []:
        if int(department.get("department_id") or department.get("id") or 0) in department_ids:
            return True
    return False


def owner_option(user: dict[str, Any]) -> dict[str, Any]:
    username = str(user.get("username", "") or "")
    full_name = str(user.get("full_name", "") or "")
    label = f"{full_name}（{username}）" if full_name and username else full_name or username or f"用户 #{user.get('id')}"
    return {
        "id": int(user.get("id", 0) or 0),
        "username": username,
        "full_name": full_name,
        "email": str(user.get("email", "") or ""),
        "label": label,
        "value": int(user.get("id", 0) or 0),
    }


def get_api_key(key_id: int) -> dict[str, Any] | None:
    return repo().get_api_key(key_id)


def update_api_key(key_id: int, *, name: str, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    user = current_user or {}
    return repo().update_api_key(
        key_id,
        name=name,
        editor=str(user.get("username", "") or ""),
        editor_id=current_user_id_or_none(user),
    )


def revoke_api_key(key_id: int) -> dict[str, Any]:
    return repo().revoke_api_key(key_id)


def validate_api_key(api_key: str) -> dict[str, Any] | None:
    return repo().validate_api_key(api_key)


def validate_user_bound_api_key(api_key: str) -> dict[str, Any] | None:
    principal = validate_api_key(api_key)
    if not principal:
        return None

    item = principal.get("api_key") or {}
    owner_user_id = int(item.get("owner_user_id") or item.get("creator_id") or 0)
    tenant_id = int(principal.get("tenant_id", 0) or 0)
    if not owner_user_id or not tenant_id:
        return None

    owner = auth_service.get_user(owner_user_id)
    if not owner or not bool(owner.get("is_active", True)):
        return None

    current_user = tenant_service.load_user_for_tenant(
        str(owner.get("username", "") or ""),
        tenant_id,
        auth_scope="tenant",
    )
    if not current_user or not bool(current_user.get("is_active", True)):
        return None

    tenant_payload = tenant_service.tenant_access_payload(current_user, tenant_id)
    current = tenant_payload.get("current_tenant")
    if not current:
        return None

    current_user.update(tenant_payload)
    current_user["tenant_id"] = int(current["id"])
    current_user["departments"] = tenant_service.user_departments_for_current_tenant(current_user)

    return {
        **principal,
        **tenant_payload,
        "auth_type": "api_key",
        "user": current_user,
        "tenant_id": int(current["id"]),
        "roles": current_user.get("roles", []),
        "permissions": current_user.get("permissions", []),
        "menus": current_user.get("menus", []),
        "departments": current_user.get("departments", []),
        "username": current_user.get("username"),
        "full_name": current_user.get("full_name", ""),
        "is_platform_admin": False,
        "is_tenant_admin": bool(current_user.get("is_tenant_admin", False)),
    }


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None
