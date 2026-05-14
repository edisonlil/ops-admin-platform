from __future__ import annotations

from typing import Any

from authorization.application.ports import AuthorizationRepository
from authorization.domain.exceptions import AuthorizationDomainError, AuthorizationNotFoundError, AuthorizationStorageNotReadyError
from authorization.domain.models import (
    DATA_SCOPE_CUSTOM_DEPARTMENTS,
    DATA_SCOPE_DEPARTMENT,
    DATA_SCOPE_DEPARTMENT_AND_CHILDREN,
    DATA_SCOPE_SELF,
    DATA_SCOPE_TENANT,
    POLICY_SUBJECT_DEPARTMENT,
    POLICY_SUBJECT_USER,
    DataAccessPolicy,
    ResourceDescriptorRecord,
    VALID_POLICY_SUBJECT_TYPES,
)
from organization.application import services as organization_services
from system.application.data_access import (
    DataAccessPredicate,
    ResourceDescriptor,
    SCOPE_CUSTOM_DEPARTMENTS,
    SCOPE_DEPARTMENT,
    SCOPE_DEPARTMENT_AND_CHILDREN,
    SCOPE_SELF,
    SCOPE_TENANT,
)


repository: AuthorizationRepository | None = None

SCOPE_RANK = {
    DATA_SCOPE_SELF: 10,
    DATA_SCOPE_DEPARTMENT: 20,
    DATA_SCOPE_CUSTOM_DEPARTMENTS: 25,
    DATA_SCOPE_DEPARTMENT_AND_CHILDREN: 30,
    DATA_SCOPE_TENANT: 40,
}


def configure_repository(authorization_repository: AuthorizationRepository) -> None:
    global repository
    repository = authorization_repository


def repo() -> AuthorizationRepository:
    if repository is None:
        raise AuthorizationStorageNotReadyError("authorization repository is not configured")
    return repository


def list_resource_descriptors() -> dict[str, Any]:
    return {"items": [resource_descriptor_to_dict(item) for item in repo().list_resource_descriptors()]}


def save_resource_descriptor(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    item = repo().upsert_resource_descriptor(
        payload,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    return {"item": resource_descriptor_to_dict(item)}


def list_data_access_policies(
    current_user: dict[str, Any] | None = None,
    *,
    subject_type: str | None = None,
    subject_id: int | None = None,
    resource_key: str | None = None,
    tenant_id: int | None = None,
) -> dict[str, Any]:
    resolved_tenant_id = resolve_managed_tenant_id(current_user or {}, tenant_id)
    return {
        "items": [
            data_access_policy_to_dict(item)
            for item in repo().list_data_access_policies(
                tenant_id=resolved_tenant_id,
                subject_type=subject_type,
                subject_id=subject_id,
                resource_key=resource_key,
            )
        ]
    }


def save_data_access_policy(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = resolve_managed_tenant_id(current_user, payload.get("tenant_id"))
    subject_type = str(payload.get("subject_type") or "").strip()
    if subject_type not in VALID_POLICY_SUBJECT_TYPES:
        raise AuthorizationDomainError("数据权限主体只能是用户或部门")
    item = repo().save_data_access_policy(
        tenant_id=tenant_id,
        subject_type=subject_type,
        subject_id=int(payload.get("subject_id") or 0),
        resource_key=str(payload.get("resource_key") or ""),
        action=str(payload.get("action") or "read"),
        scope=str(payload.get("scope") or DATA_SCOPE_SELF),
        department_ids=[int(value) for value in payload.get("department_ids") or []],
        priority=int(payload.get("priority") or 100),
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    return {"item": data_access_policy_to_dict(item)}


def delete_data_access_policy(policy_id: int, current_user: dict[str, Any], *, tenant_id: int | None = None) -> dict[str, Any]:
    resolved_tenant_id = resolve_managed_tenant_id(current_user, tenant_id)
    item = repo().delete_data_access_policy(tenant_id=resolved_tenant_id, policy_id=policy_id)
    if item is None:
        raise AuthorizationNotFoundError("data access policy not found")
    return {"id": policy_id, "deleted": True}


class BuiltinDataAccessFilterProvider:
    def resolve_filter(
        self,
        *,
        current_user: dict[str, Any],
        resource: ResourceDescriptor,
        action: str,
    ) -> DataAccessPredicate:
        tenant_id = current_tenant_id(current_user)
        user_id = int(current_user.get("id", 0) or 0)
        if bool(current_user.get("is_platform_admin", False)) or bool(current_user.get("is_tenant_admin", False)):
            return DataAccessPredicate(tenant_id=tenant_id, scope=SCOPE_TENANT, user_id=user_id)
        try:
            departments = organization_services.user_departments(tenant_id=tenant_id, user_id=user_id)
        except Exception:
            departments = []
        department_ids = tuple(int(item.get("department_id") or item.get("id") or 0) for item in departments if int(item.get("department_id") or item.get("id") or 0))
        try:
            all_policies = repo().list_data_access_policies(tenant_id=tenant_id, resource_key=resource.resource_key)
            policies = [
                item
                for item in all_policies
                if item.action == action
                and (
                    (item.subject_type == POLICY_SUBJECT_USER and item.subject_id == user_id)
                    or (item.subject_type == POLICY_SUBJECT_DEPARTMENT and item.subject_id in department_ids)
                )
            ]
        except Exception:
            policies = []
        if not policies:
            return DataAccessPredicate(tenant_id=tenant_id, scope=SCOPE_SELF, user_id=user_id)
        policy = max(policies, key=lambda item: (int(item.priority), SCOPE_RANK.get(item.scope, 0)))
        primary = next((item for item in departments if bool(item.get("is_primary"))), departments[0] if departments else None)
        if policy.scope == DATA_SCOPE_TENANT:
            return DataAccessPredicate(tenant_id=tenant_id, scope=SCOPE_TENANT, user_id=user_id)
        if policy.scope == DATA_SCOPE_SELF:
            return DataAccessPredicate(tenant_id=tenant_id, scope=SCOPE_SELF, user_id=user_id)
        if policy.scope == DATA_SCOPE_DEPARTMENT:
            department_id = int((primary or {}).get("department_id") or (primary or {}).get("id") or 0)
            return DataAccessPredicate(
                tenant_id=tenant_id,
                scope=SCOPE_DEPARTMENT,
                user_id=user_id,
                department_ids=(department_id,) if department_id else (),
            )
        if policy.scope == DATA_SCOPE_DEPARTMENT_AND_CHILDREN:
            department_id = int((primary or {}).get("department_id") or (primary or {}).get("id") or 0)
            department_ids = organization_services.department_descendant_ids(tenant_id=tenant_id, department_id=department_id) if department_id else []
            return DataAccessPredicate(
                tenant_id=tenant_id,
                scope=SCOPE_DEPARTMENT_AND_CHILDREN,
                user_id=user_id,
                department_ids=tuple(department_ids),
            )
        if policy.scope == DATA_SCOPE_CUSTOM_DEPARTMENTS:
            return DataAccessPredicate(
                tenant_id=tenant_id,
                scope=SCOPE_CUSTOM_DEPARTMENTS,
                user_id=user_id,
                department_ids=policy.department_ids,
            )
        return DataAccessPredicate(tenant_id=tenant_id, scope=SCOPE_SELF, user_id=user_id)


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current = current_user.get("current_tenant") or {}
    return int(current.get("id") or current_user.get("tenant_id") or 0)


def resolve_managed_tenant_id(current_user: dict[str, Any], tenant_id: Any = None) -> int:
    requested = int(tenant_id or 0)
    if requested and bool(current_user.get("is_platform_admin", False)):
        return requested
    resolved = current_tenant_id(current_user)
    if not resolved:
        raise AuthorizationDomainError("需要先进入租户上下文后再配置数据权限")
    if requested and requested != resolved:
        raise AuthorizationDomainError("不能配置其他租户的数据权限")
    return resolved


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None


def resource_descriptor_to_dict(item: ResourceDescriptorRecord) -> dict[str, Any]:
    return {
        "id": item.id,
        "resource_key": item.resource_key,
        "name": item.name,
        "description": item.description,
        "tenant_column": item.tenant_column,
        "creator_column": item.creator_column,
        "owner_user_column": item.owner_user_column,
        "owner_department_column": item.owner_department_column,
        "supported_scopes": list(item.supported_scopes),
        "requires_data_scope": item.requires_data_scope,
        "create_time": item.create_time,
        "update_time": item.update_time,
    }


def data_access_policy_to_dict(item: DataAccessPolicy) -> dict[str, Any]:
    return {
        "id": item.id,
        "tenant_id": item.tenant_id,
        "subject_type": item.subject_type,
        "subject_id": item.subject_id,
        "resource_key": item.resource_key,
        "action": item.action,
        "scope": item.scope,
        "department_ids": list(item.department_ids),
        "priority": item.priority,
        "create_time": item.create_time,
        "update_time": item.update_time,
    }
