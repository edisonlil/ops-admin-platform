from __future__ import annotations

from dataclasses import dataclass


DATA_SCOPE_SELF = "self"
DATA_SCOPE_SELF_AND_SUBORDINATES = "self_and_subordinates"
DATA_SCOPE_DEPARTMENT = "department"
DATA_SCOPE_DEPARTMENT_AND_CHILDREN = "department_and_children"
DATA_SCOPE_CUSTOM_DEPARTMENTS = "custom_departments"
DATA_SCOPE_TENANT = "tenant"

POLICY_SUBJECT_USER = "user"
POLICY_SUBJECT_DEPARTMENT = "department"
POLICY_SUBJECT_ALL_USERS_ID = 0

VALID_DATA_SCOPES = {
    DATA_SCOPE_SELF,
    DATA_SCOPE_SELF_AND_SUBORDINATES,
    DATA_SCOPE_DEPARTMENT,
    DATA_SCOPE_DEPARTMENT_AND_CHILDREN,
    DATA_SCOPE_CUSTOM_DEPARTMENTS,
    DATA_SCOPE_TENANT,
}

VALID_POLICY_SUBJECT_TYPES = {
    POLICY_SUBJECT_USER,
    POLICY_SUBJECT_DEPARTMENT,
}

ACCESS_MODE_OWNER_COLUMNS = "owner_columns"
ACCESS_MODE_RELATION_TABLE = "relation_table"

VALID_ACCESS_MODES = {
    ACCESS_MODE_OWNER_COLUMNS,
    ACCESS_MODE_RELATION_TABLE,
}


@dataclass(frozen=True)
class ResourceDescriptorRecord:
    id: int
    resource_key: str
    name: str
    description: str
    tenant_column: str
    resource_id_column: str
    creator_column: str
    owner_user_column: str
    owner_department_column: str
    access_mode: str
    relation_table: str
    relation_resource_id_column: str
    relation_user_column: str
    relation_department_column: str
    relation_tenant_column: str
    relation_deleted_column: str
    relation_resource_key_column: str
    relation_resource_key_value: str
    relation_subject_type_column: str
    relation_subject_type_user_value: str
    relation_subject_type_department_value: str
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
