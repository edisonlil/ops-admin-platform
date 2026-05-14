from __future__ import annotations

from dataclasses import dataclass


DATA_SCOPE_SELF = "self"
DATA_SCOPE_DEPARTMENT = "department"
DATA_SCOPE_DEPARTMENT_AND_CHILDREN = "department_and_children"
DATA_SCOPE_CUSTOM_DEPARTMENTS = "custom_departments"
DATA_SCOPE_TENANT = "tenant"

VALID_DATA_SCOPES = {
    DATA_SCOPE_SELF,
    DATA_SCOPE_DEPARTMENT,
    DATA_SCOPE_DEPARTMENT_AND_CHILDREN,
    DATA_SCOPE_CUSTOM_DEPARTMENTS,
    DATA_SCOPE_TENANT,
}


@dataclass(frozen=True)
class ResourceDescriptorRecord:
    id: int
    resource_key: str
    name: str
    description: str
    tenant_column: str
    creator_column: str
    owner_user_column: str
    owner_department_column: str
    supported_scopes: tuple[str, ...]
    requires_data_scope: bool
    create_time: str
    update_time: str


@dataclass(frozen=True)
class RoleDataScope:
    id: int
    role_key: str
    resource_key: str
    action: str
    scope: str
    department_ids: tuple[int, ...]
    create_time: str
    update_time: str
