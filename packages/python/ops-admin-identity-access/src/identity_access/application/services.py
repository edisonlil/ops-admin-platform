from __future__ import annotations

from typing import Any

from fastapi import Response

from identity_access.application import api_key_service, auth_service, import_jobs, rbac_service, tenant_service, user_import_export
from identity_access.application.access_context_cache import clear_access_context_cache
from identity_access.domain import events
from system.application.event_bus import publish_event
from system.application.sorting import sort_dict_items
from system.interfaces.http import current_request_id


TENANT_SORT_COLUMNS = {
    "id": "id",
    "key": "key",
    "tenant_key": "tenant_key",
    "name": "name",
    "status": "status",
    "user_count": "user_count",
    "api_key_count": "api_key_count",
    "create_time": "create_time",
    "update_time": "update_time",
}
USER_SORT_COLUMNS = {
    "id": "id",
    "tenant_id": "tenant_id",
    "username": "username",
    "full_name": "full_name",
    "email": "email",
    "is_active": "is_active",
    "is_superuser": "is_superuser",
    "is_tenant_admin": "is_tenant_admin",
    "create_time": "create_time",
    "update_time": "update_time",
}
ROLE_SORT_COLUMNS = {
    "id": "id",
    "key": "key",
    "role_key": "key",
    "name": "name",
    "role_scope": "role_scope",
}
MENU_SORT_COLUMNS = {
    "id": "id",
    "key": "key",
    "label": "label",
    "menu_scope": "menu_scope",
    "menu_type": "menu_type",
    "sort_order": "sort_order",
    "is_visible": "is_visible",
}
API_KEY_SORT_COLUMNS = {
    "id": "id",
    "tenant_id": "tenant_id",
    "name": "name",
    "prefix": "prefix",
    "is_active": "is_active",
    "create_time": "create_time",
    "update_time": "update_time",
}
_MANAGER_USER_UNSET = object()


def _after_access_context_change(payload: dict[str, Any]) -> dict[str, Any]:
    clear_access_context_cache()
    return payload


def page_items(items: list[dict[str, Any]], *, page: int, page_size: int) -> dict[str, Any]:
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, int(page_size or 20))
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    return {
        "items": items[start:start + safe_page_size],
        "pagination": {"page": safe_page, "page_size": safe_page_size, "total": total},
    }


def authenticate(
    username: str,
    password: str,
    response: Response | None = None,
    *,
    tenant_key: str = "default",
) -> dict[str, Any] | None:
    normalized_tenant_key = (tenant_key or "default").strip()
    if normalized_tenant_key == tenant_service.PLATFORM_TENANT_KEY:
        user = auth_service.authenticate_platform_admin(username, password)
        if not user:
            return None
        user["auth_scope"] = "platform"
        tenant_payload = tenant_service.tenant_access_payload(user)
        token = auth_service.create_access_token(
            user["username"],
            auth_scope="platform",
            user_id=int(user.get("id", 0) or 0),
        )
        if response is not None:
            auth_service.set_login_cookie(response, token)
        publish_event(events.user_logged_in(str(user["username"]), correlation_id=current_request_id()))
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user["username"],
            "full_name": user.get("full_name", ""),
            "expires_in": auth_service.access_token_expire_seconds(),
            "roles": user.get("roles", []),
            "permissions": user.get("permissions", []),
            "menus": user.get("menus", []),
            **tenant_payload,
        }
    tenant = tenant_service.get_tenant_by_key(tenant_key)
    if not tenant:
        return None
    user = auth_service.authenticate_user(username, password, tenant_id=int(tenant["id"]))
    if not user:
        return None
    membership = tenant_service.membership_for_user_in_tenant(int(user.get("id", 0) or 0), int(tenant["id"]))
    if membership:
        user = auth_service.public_user(
            user,
            tenant_id=int(tenant["id"]),
            auth_scope="tenant",
            is_tenant_admin=bool(membership.get("is_tenant_admin", False)),
        )
        user["auth_scope"] = "tenant"
    tenant_payload = tenant_service.tenant_access_payload(user)
    token = auth_service.create_access_token(
        user["username"],
        tenant_id=int(tenant_payload["current_tenant"]["id"]),
        auth_scope="tenant",
        user_id=int(user.get("id", 0) or 0),
    )
    if response is not None:
        auth_service.set_login_cookie(response, token)
    publish_event(events.user_logged_in(str(user["username"]), correlation_id=current_request_id()))
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "full_name": user.get("full_name", ""),
        "expires_in": auth_service.access_token_expire_seconds(),
        "roles": user.get("roles", []),
        "permissions": user.get("permissions", []),
        "menus": user.get("menus", []),
        **tenant_payload,
    }


def login_for_admin(username: str, password: str, response: Response, *, tenant_key: str = "default") -> dict[str, Any] | None:
    normalized_tenant_key = (tenant_key or "default").strip()
    if normalized_tenant_key == tenant_service.PLATFORM_TENANT_KEY:
        user = auth_service.authenticate_platform_admin(username, password)
        if not user:
            return None
        user["auth_scope"] = "platform"
        tenant_payload = tenant_service.tenant_access_payload(user)
        token = auth_service.create_access_token(
            user["username"],
            auth_scope="platform",
            user_id=int(user.get("id", 0) or 0),
        )
        auth_service.set_login_cookie(response, token)
        publish_event(events.user_logged_in(str(user["username"]), correlation_id=current_request_id()))
        return {
            "token": token,
            "username": user["username"],
            "full_name": user.get("full_name", ""),
            "avatar": "",
            "permissions": scaffold_permissions(list(user.get("permissions", []))),
            "roles": user.get("roles", []),
            "menus": user.get("menus", []),
            **tenant_payload,
        }
    tenant = tenant_service.get_tenant_by_key(tenant_key)
    if not tenant:
        return None
    user = auth_service.authenticate_user(username, password, tenant_id=int(tenant["id"]))
    if not user:
        return None
    membership = tenant_service.membership_for_user_in_tenant(int(user.get("id", 0) or 0), int(tenant["id"]))
    if membership:
        user = auth_service.public_user(
            user,
            tenant_id=int(tenant["id"]),
            auth_scope="tenant",
            is_tenant_admin=bool(membership.get("is_tenant_admin", False)),
        )
        user["auth_scope"] = "tenant"
    tenant_payload = tenant_service.tenant_access_payload(user)
    token = auth_service.create_access_token(
        user["username"],
        tenant_id=int(tenant_payload["current_tenant"]["id"]),
        auth_scope="tenant",
        user_id=int(user.get("id", 0) or 0),
    )
    auth_service.set_login_cookie(response, token)
    publish_event(events.user_logged_in(str(user["username"]), correlation_id=current_request_id()))
    return {
        "token": token,
        "username": user["username"],
        "full_name": user.get("full_name", ""),
        "avatar": "",
        "permissions": scaffold_permissions(list(user.get("permissions", []))),
        "roles": user.get("roles", []),
        "menus": user.get("menus", []),
        **tenant_payload,
    }


def logout(response: Response) -> bool:
    auth_service.clear_login_cookie(response)
    return True


def scaffold_permissions(permission_codes: list[str]) -> list[dict[str, str]]:
    catalog = {item["code"]: item for item in rbac_service.list_permissions()}
    return [
        {
            "label": catalog.get(code, {}).get("name", code),
            "value": code,
        }
        for code in permission_codes
    ]


def scaffold_user(current_user: dict[str, Any]) -> dict[str, Any]:
    roles = current_user.get("roles", [])
    current_tenant_id = None if bool(current_user.get("is_platform_admin", False)) else current_user.get("tenant_id")
    tenant_payload = tenant_service.tenant_access_payload(current_user, current_tenant_id)
    departments = tenant_service.user_departments_for_current_tenant({**current_user, **tenant_payload})
    primary_department = next(
        (department for department in departments if bool(department.get("is_primary"))),
        departments[0] if departments else None,
    )
    payload = {
        "username": str(current_user.get("username", "")),
        "full_name": str(current_user.get("full_name", "") or ""),
        "email": str(current_user.get("email", "") or ""),
        "avatar": "",
        "roles": [
            {
                "label": str(role.get("name", role.get("key", ""))),
                "value": str(role.get("key", "")),
            }
            for role in roles
        ],
        "permissions": scaffold_permissions(list(current_user.get("permissions", []))),
        "menus": current_user.get("menus", []),
        "departments": departments,
        "department_ids": [int(department["department_id"]) for department in departments],
        "primary_department_id": int(primary_department["department_id"]) if primary_department else None,
    }
    payload.update(tenant_payload)
    return payload


def update_current_profile(current_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    old_email = str(current_user.get("email", "") or "")
    requested_email = None if payload.get("email") is None else str(payload.get("email") or "")
    updated = auth_service.update_own_profile(
        int(current_user.get("id", 0) or 0),
        full_name=str(payload.get("full_name", "") or ""),
        email=requested_email,
        current_password=str(payload.get("current_password", "") or ""),
        new_password=str(payload.get("new_password", "") or ""),
    )
    result = scaffold_user({**current_user, **updated})
    changed_fields = ["full_name"]
    if requested_email is not None:
        changed_fields.append("email")
    if str(payload.get("new_password", "") or "").strip():
        changed_fields.append("password")
    publish_event(events.user_updated(result, changed_fields=changed_fields, correlation_id=current_request_id()))
    new_email = str(updated.get("email", "") or "")
    if requested_email is not None and old_email != new_email:
        publish_event(events.user_email_changed(result, old_email=old_email, new_email=new_email, correlation_id=current_request_id()))
    return _after_access_context_change(result)


def switch_tenant(
    username: str,
    tenant_id: int,
    response: Response | None = None,
    *,
    auth_scope: str = "tenant",
) -> dict[str, Any]:
    return tenant_service.switch_tenant(username, tenant_id, response=response, auth_scope=auth_scope)


def list_tenants(q: str | None = None, *, sort_by: str | None = None, sort_dir: str | None = None) -> list[dict[str, Any]]:
    return tenant_service.list_tenants(q=q, sort_by=sort_by, sort_dir=sort_dir)


def list_tenants_page(
    q: str | None = None,
    *,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return page_items(list_tenants(q=q, sort_by=sort_by, sort_dir=sort_dir), page=page, page_size=page_size)


def create_tenant(payload: dict[str, Any]) -> dict[str, Any]:
    return _after_access_context_change(tenant_service.create_tenant(payload))


def update_tenant(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return _after_access_context_change(tenant_service.update_tenant(tenant_id, payload))


def activate_tenant(tenant_id: int) -> dict[str, Any]:
    return _after_access_context_change(tenant_service.activate_tenant(tenant_id))


def suspend_tenant(tenant_id: int) -> dict[str, Any]:
    return _after_access_context_change(tenant_service.suspend_tenant(tenant_id))


def list_tenant_users(
    tenant_id: int,
    *,
    username: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
    is_active: bool | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> list[dict[str, Any]]:
    items = filter_tenant_users(
        tenant_service.list_tenant_users(tenant_id),
        username=username,
        email=email,
        full_name=full_name,
        is_active=is_active,
    )
    return sort_dict_items(items, sort_by, sort_dir, allowed=USER_SORT_COLUMNS)


def list_tenant_users_page(
    tenant_id: int,
    *,
    page: int,
    page_size: int,
    username: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
    is_active: bool | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return page_items(
        list_tenant_users(
            tenant_id,
            username=username,
            email=email,
            full_name=full_name,
            is_active=is_active,
            sort_by=sort_by,
            sort_dir=sort_dir,
        ),
        page=page,
        page_size=page_size,
    )


def filter_tenant_users(
    items: list[dict[str, Any]],
    *,
    username: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
    is_active: bool | None = None,
) -> list[dict[str, Any]]:
    username_text = (username or "").strip().lower()
    email_text = (email or "").strip().lower()
    full_name_text = (full_name or "").strip().lower()

    def matches(item: dict[str, Any]) -> bool:
        if username_text and username_text not in str(item.get("username", "") or "").lower():
            return False
        if email_text and email_text not in str(item.get("email", "") or "").lower():
            return False
        if full_name_text and full_name_text not in str(item.get("full_name", "") or "").lower():
            return False
        if is_active is not None and bool(item.get("is_active", False)) != bool(is_active):
            return False
        return True

    return [item for item in items if matches(item)]


def export_tenant_users(tenant_id: int) -> Any:
    return user_import_export.build_tenant_user_export_workbook(list_tenant_users(tenant_id))


def export_tenant_user_import_template(tenant_id: int) -> Any:
    return user_import_export.build_tenant_user_import_template(tenant_id)


def import_tenant_users(tenant_id: int, content: bytes, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    return import_jobs.start_import_job(
        "tenant_users",
        lambda progress: perform_tenant_user_import(tenant_id, content, current_user=current_user, progress=progress),
        scope_id=tenant_id,
    )


def perform_tenant_user_import(
    tenant_id: int,
    content: bytes,
    current_user: dict[str, Any] | None = None,
    progress: Any | None = None,
) -> dict[str, Any]:
    if progress:
        progress(15, "正在解析导入文件")
    rows, assignments = user_import_export.parse_tenant_user_import_workbook(content, tenant_id=tenant_id)
    if progress:
        progress(35, "正在批量创建成员")
    imported = rbac_service.import_users_batch(rows)
    membership_rows: list[dict[str, Any]] = []
    for user, assignment in zip(imported, assignments, strict=False):
        user_id = int(user["id"])
        assignment["user_id"] = user_id
        membership_rows.append({"user_id": user_id, "is_tenant_admin": bool(assignment.get("is_tenant_admin", False))})
    if progress:
        progress(70, "正在绑定租户成员关系")
    tenant_service.ensure_memberships_batch(tenant_id, membership_rows)
    if progress:
        progress(85, "正在同步部门关系")
    sync_users_departments_batch_if_available(assignments, current_user=current_user)
    sync_users_reporting_managers_batch_if_available(assignments, current_user=current_user)
    result = list_tenant_users(tenant_id)
    imported_ids = {int(user["id"]) for user in imported}
    items = [item for item in result if int(item["id"]) in imported_ids]
    publish_event(events.users_imported(items, correlation_id=current_request_id()))
    return _after_access_context_change({"items": items, "count": len(items)})


def current_import_job(kind: str | None = None, *, scope_id: int | None = None) -> dict[str, Any] | None:
    return import_jobs.current_import_job(kind, scope_id=scope_id)


def create_tenant_user(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    result = tenant_service.create_tenant_user(tenant_id, payload)
    publish_event(events.user_created(result, correlation_id=current_request_id()))
    return _after_access_context_change(result)


def update_tenant_user(tenant_id: int, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    existing = tenant_service.get_tenant_user(tenant_id, user_id) or {}
    old_email = str(existing.get("email", "") or "")
    result = tenant_service.update_tenant_user(tenant_id, user_id, payload)
    changed_fields = ["username", "full_name", "email", "roles", "is_active"]
    if str(payload.get("password", "") or "").strip():
        changed_fields.append("password")
    if payload.get("department_ids") is not None or payload.get("primary_department_id") is not None:
        changed_fields.extend(["department_ids", "primary_department_id"])
    publish_event(events.user_updated(result, changed_fields=changed_fields, correlation_id=current_request_id()))
    new_email = str(result.get("email", "") or "")
    if old_email != new_email:
        publish_event(events.user_email_changed(result, old_email=old_email, new_email=new_email, correlation_id=current_request_id()))
    return _after_access_context_change(result)


def set_tenant_user_active(tenant_id: int, user_id: int, is_active: bool) -> dict[str, Any]:
    return _after_access_context_change(tenant_service.set_tenant_user_active(tenant_id, user_id, is_active))


def list_users() -> list[dict[str, Any]]:
    return [enrich_user_with_reporting_manager(enrich_user_with_departments(item)) for item in rbac_service.list_users()]


def list_platform_users(*, sort_by: str | None = None, sort_dir: str | None = None) -> list[dict[str, Any]]:
    items = [enrich_user_with_reporting_manager(enrich_user_with_departments(item)) for item in rbac_service.list_platform_users()]
    return sort_dict_items(items, sort_by, sort_dir, allowed=USER_SORT_COLUMNS)


def list_platform_users_page(
    *,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return page_items(list_platform_users(sort_by=sort_by, sort_dir=sort_dir), page=page, page_size=page_size)


def export_platform_users() -> Any:
    return user_import_export.build_user_export_workbook(list_platform_users())


def export_user_import_template() -> Any:
    return user_import_export.build_user_import_template()


def import_platform_users(content: bytes, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    return import_jobs.start_import_job(
        "platform_users",
        lambda progress: perform_platform_user_import(content, current_user=current_user, progress=progress),
    )


def perform_platform_user_import(
    content: bytes,
    current_user: dict[str, Any] | None = None,
    progress: Any | None = None,
) -> dict[str, Any]:
    if progress:
        progress(15, "正在解析导入文件")
    rows, assignments = user_import_export.parse_user_import_workbook(content)
    if progress:
        progress(40, "正在批量创建用户")
    imported = rbac_service.import_users_batch(rows)
    for user, assignment in zip(imported, assignments, strict=False):
        assignment["user_id"] = int(user["id"])
    if progress:
        progress(80, "正在同步部门关系")
    sync_users_departments_batch_if_available(assignments, current_user=current_user)
    sync_users_reporting_managers_batch_if_available(assignments, current_user=current_user)
    result = [enrich_user_with_reporting_manager(enrich_user_with_departments(item)) for item in imported]
    publish_event(events.users_imported(result, correlation_id=current_request_id()))
    return _after_access_context_change({"items": result, "count": len(result)})


def create_user(
    *,
    username: str,
    password: str,
    full_name: str = "",
    email: str = "",
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    department_ids: list[int] | None = None,
    primary_department_id: int | None = None,
    manager_user_id: Any = _MANAGER_USER_UNSET,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    user = rbac_service.create_user(
        username=username,
        password=password,
        full_name=full_name,
        email=email,
        tenant_id=tenant_id,
        role_keys=role_keys,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    if department_ids is not None or primary_department_id is not None:
        sync_user_departments_if_available(user, department_ids or [], primary_department_id)
    if manager_user_id is not _MANAGER_USER_UNSET:
        sync_user_reporting_manager_if_available(user, manager_user_id)
    result = enrich_user_with_departments(user)
    result = enrich_user_with_reporting_manager(result)
    publish_event(events.user_created(result, correlation_id=current_request_id()))
    return _after_access_context_change(result)


def update_user(
    user_id: int,
    *,
    username: str,
    full_name: str = "",
    email: str = "",
    password: str = "",
    tenant_id: int | None = None,
    role_keys: list[str] | None = None,
    department_ids: list[int] | None = None,
    primary_department_id: int | None = None,
    manager_user_id: Any = _MANAGER_USER_UNSET,
    is_active: bool = True,
    is_superuser: bool = False,
) -> dict[str, Any]:
    existing = rbac_service.get_user(user_id) or {}
    old_email = str(existing.get("email", "") or "")
    user = rbac_service.update_user(
        user_id,
        username=username,
        full_name=full_name,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role_keys=role_keys,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    if department_ids is not None or primary_department_id is not None:
        sync_user_departments_if_available(user, department_ids or [], primary_department_id)
    if manager_user_id is not _MANAGER_USER_UNSET:
        sync_user_reporting_manager_if_available(user, manager_user_id)
    result = enrich_user_with_departments(user)
    result = enrich_user_with_reporting_manager(result)
    changed_fields = ["username", "full_name", "email", "roles", "is_active", "is_superuser", "tenant_id"]
    if password.strip():
        changed_fields.append("password")
    if department_ids is not None or primary_department_id is not None:
        changed_fields.extend(["department_ids", "primary_department_id"])
    if manager_user_id is not _MANAGER_USER_UNSET:
        changed_fields.append("manager_user_id")
    publish_event(events.user_updated(result, changed_fields=changed_fields, correlation_id=current_request_id()))
    new_email = str(result.get("email", "") or "")
    if old_email != new_email:
        publish_event(events.user_email_changed(result, old_email=old_email, new_email=new_email, correlation_id=current_request_id()))
    return _after_access_context_change(result)


def set_user_active(user_id: int, is_active: bool) -> dict[str, Any]:
    return _after_access_context_change(rbac_service.set_user_active(user_id, is_active))


def list_roles(*, sort_by: str | None = None, sort_dir: str | None = None) -> list[dict[str, Any]]:
    return sort_dict_items(rbac_service.list_roles(), sort_by, sort_dir, allowed=ROLE_SORT_COLUMNS)


def list_roles_page(
    *,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return page_items(list_roles(sort_by=sort_by, sort_dir=sort_dir), page=page, page_size=page_size)


def create_role(
    *,
    role_key: str,
    name: str,
    description: str = "",
    role_scope: str = "platform",
    menu_keys: list[str] | None = None,
) -> dict[str, Any]:
    role = rbac_service.create_role(
        role_key=role_key,
        name=name,
        description=description,
        role_scope=role_scope,
        menu_keys=menu_keys,
    )
    publish_event(events.role_permissions_changed(int(role["id"]), correlation_id=current_request_id()))
    return _after_access_context_change(role)


def update_role(
    role_id: int,
    *,
    role_key: str,
    name: str,
    description: str = "",
    menu_keys: list[str] | None = None,
) -> dict[str, Any]:
    role = rbac_service.update_role(
        role_id,
        role_key=role_key,
        name=name,
        description=description,
        menu_keys=menu_keys,
    )
    publish_event(events.role_permissions_changed(role_id, correlation_id=current_request_id()))
    return _after_access_context_change(role)


def update_role_menus(role_id: int, menu_keys: list[str]) -> dict[str, Any]:
    role = rbac_service.update_role_menus(role_id, menu_keys)
    publish_event(events.role_permissions_changed(role_id, correlation_id=current_request_id()))
    return _after_access_context_change(role)


def delete_role(role_id: int) -> dict[str, Any]:
    role = rbac_service.delete_role(role_id)
    publish_event(events.role_deleted(role_id, correlation_id=current_request_id()))
    return _after_access_context_change(role)


def list_permissions() -> list[dict[str, str]]:
    return rbac_service.list_permissions()


def list_menus(menu_scope: str | None = None, *, sort_by: str | None = None, sort_dir: str | None = None) -> list[dict[str, Any]]:
    return sort_dict_items(rbac_service.list_menus(menu_scope=menu_scope), sort_by, sort_dir, allowed=MENU_SORT_COLUMNS)


def list_menu_tenant_assignments(
    menu_key: str,
    *,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return rbac_service.list_menu_tenant_assignments(
        menu_key,
        q=q,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def set_menu_tenant_assignments(menu_key: str, tenant_ids: list[int]) -> dict[str, Any]:
    return rbac_service.set_menu_tenant_assignments(menu_key, tenant_ids)


def get_tenant_menu_assignments(tenant_id: int) -> dict[str, Any]:
    return rbac_service.get_tenant_menu_assignments(tenant_id)


def set_tenant_menu_assignments(tenant_id: int, menu_keys: list[str]) -> dict[str, Any]:
    return rbac_service.set_tenant_menu_assignments(tenant_id, menu_keys)


def sync_user_departments_if_available(user: dict[str, Any], department_ids: list[int], primary_department_id: int | None) -> None:
    try:
        from organization.application import services as organization_services
    except Exception:
        return
    tenant_id = int(user.get("tenant_id", 0) or 0)
    user_id = int(user.get("id", 0) or 0)
    if not tenant_id or not user_id:
        return
    organization_services.set_user_departments(
        tenant_id=tenant_id,
        user_id=user_id,
        department_ids=department_ids,
        primary_department_id=primary_department_id,
        current_user={"username": "system", "id": None},
    )


def sync_user_reporting_manager_if_available(user: dict[str, Any], manager_user_id: int | None) -> None:
    try:
        from organization.application import services as organization_services
    except Exception:
        return
    tenant_id = int(user.get("tenant_id", 0) or 0)
    user_id = int(user.get("id", 0) or 0)
    if not tenant_id or not user_id:
        return
    organization_services.set_user_reporting_manager(
        tenant_id=tenant_id,
        user_id=user_id,
        manager_user_id=int(manager_user_id or 0) or None,
        current_user={"username": "system", "id": None},
    )


def sync_users_departments_batch_if_available(rows: list[dict[str, Any]], current_user: dict[str, Any] | None = None) -> None:
    assignments = [row for row in rows if row.get("department_ids") or row.get("primary_department_id")]
    if not assignments:
        return
    try:
        from organization.application import services as organization_services
    except Exception:
        return
    organization_services.set_users_departments_batch(assignments, current_user=current_user or {"username": "system", "id": None})


def sync_users_reporting_managers_batch_if_available(rows: list[dict[str, Any]], current_user: dict[str, Any] | None = None) -> None:
    assignments = [row for row in rows if row.get("manager_user_id") is not None]
    if not assignments:
        return
    try:
        from organization.application import services as organization_services
    except Exception:
        return
    organization_services.set_users_reporting_managers_batch(assignments, current_user=current_user or {"username": "system", "id": None})


def enrich_user_with_departments(user: dict[str, Any]) -> dict[str, Any]:
    try:
        from organization.application import services as organization_services
    except Exception:
        return user
    tenant_id = int(user.get("tenant_id", 0) or 0)
    user_id = int(user.get("id", 0) or 0)
    if not tenant_id or not user_id:
        return user
    try:
        departments = organization_services.user_departments(tenant_id=tenant_id, user_id=user_id)
    except Exception:
        return user
    item = dict(user)
    item["departments"] = departments
    primary = next((department for department in departments if bool(department.get("is_primary"))), departments[0] if departments else None)
    item["department_ids"] = [int(department["department_id"]) for department in departments]
    item["primary_department_id"] = int(primary["department_id"]) if primary else None
    return item


def enrich_user_with_reporting_manager(user: dict[str, Any]) -> dict[str, Any]:
    try:
        from organization.application import services as organization_services
    except Exception:
        return user
    tenant_id = int(user.get("tenant_id", 0) or 0)
    user_id = int(user.get("id", 0) or 0)
    if not tenant_id or not user_id:
        return user
    try:
        relationship = organization_services.user_reporting_manager(tenant_id=tenant_id, user_id=user_id)
    except Exception:
        return user
    item = dict(user)
    item["manager_user_id"] = int((relationship or {}).get("manager_user_id") or 0) or None
    return item


def create_menu(
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    menu_scope: str = "platform",
    path: str = "",
    route_name: str = "",
    component: str = "",
    icon: str = "",
    parent_key: str = "",
    permission_code: str = "",
    sort_order: int = 0,
    is_visible: bool = True,
) -> dict[str, Any]:
    return _after_access_context_change(rbac_service.create_menu(
        menu_key=menu_key,
        label=label,
        menu_scope=menu_scope,
        menu_type=menu_type,
        path=path,
        route_name=route_name,
        component=component,
        icon=icon,
        parent_key=parent_key,
        permission_code=permission_code,
        sort_order=sort_order,
        is_visible=is_visible,
    ))


def update_menu(
    menu_id: int,
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    menu_scope: str = "platform",
    path: str = "",
    route_name: str = "",
    component: str = "",
    icon: str = "",
    parent_key: str = "",
    permission_code: str = "",
    sort_order: int = 0,
    is_visible: bool = True,
) -> dict[str, Any]:
    return _after_access_context_change(rbac_service.update_menu(
        menu_id,
        menu_key=menu_key,
        label=label,
        menu_scope=menu_scope,
        menu_type=menu_type,
        path=path,
        route_name=route_name,
        component=component,
        icon=icon,
        parent_key=parent_key,
        permission_code=permission_code,
        sort_order=sort_order,
        is_visible=is_visible,
    ))


def delete_menu(menu_id: int) -> dict[str, Any]:
    return _after_access_context_change(rbac_service.delete_menu(menu_id))


def create_api_key(
    *, name: str, creator: str, tenant_id: int | None = None, current_user: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload = api_key_service.create_api_key(name=name, creator=creator, tenant_id=tenant_id, current_user=current_user)
    publish_event(events.api_key_created(payload["item"], correlation_id=current_request_id()))
    return payload


def list_api_keys(
    tenant_id: int | None = None,
    current_user: dict[str, Any] | None = None,
    *,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> list[dict[str, Any]]:
    return api_key_service.list_api_keys(tenant_id=tenant_id, current_user=current_user, sort_by=sort_by, sort_dir=sort_dir)


def list_api_keys_page(
    tenant_id: int | None = None,
    current_user: dict[str, Any] | None = None,
    *,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return page_items(
        list_api_keys(tenant_id=tenant_id, current_user=current_user, sort_by=sort_by, sort_dir=sort_dir),
        page=page,
        page_size=page_size,
    )


def get_api_key(key_id: int) -> dict[str, Any] | None:
    return api_key_service.get_api_key(key_id)


def update_api_key(key_id: int, *, name: str, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    return api_key_service.update_api_key(key_id, name=name, current_user=current_user)


def revoke_api_key(key_id: int) -> dict[str, Any]:
    return api_key_service.revoke_api_key(key_id)
