from __future__ import annotations

from dataclasses import dataclass


DATA_SCOPE_SELF = "self"
DATA_SCOPE_DEPARTMENT = "department"
DATA_SCOPE_DEPARTMENT_AND_CHILDREN = "department_and_children"
DATA_SCOPE_CUSTOM_DEPARTMENTS = "custom_departments"
DATA_SCOPE_TENANT = "tenant"

POLICY_SUBJECT_USER = "user"
POLICY_SUBJECT_DEPARTMENT = "department"

VALID_DATA_SCOPES = {
    DATA_SCOPE_SELF,
    DATA_SCOPE_DEPARTMENT,
    DATA_SCOPE_DEPARTMENT_AND_CHILDREN,
    DATA_SCOPE_CUSTOM_DEPARTMENTS,
    DATA_SCOPE_TENANT,
}

VALID_POLICY_SUBJECT_TYPES = {
    POLICY_SUBJECT_USER,
    POLICY_SUBJECT_DEPARTMENT,
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
class DataAccessPolicy:
    id: int
    tenant_id: int
    subject_type: str
    subject_id: int
    resource_key: str
    action: str
    scope: str
    department_ids: tuple[int, ...]
    priority: int
    create_time: str
    update_time: str
