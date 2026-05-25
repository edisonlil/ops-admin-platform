from __future__ import annotations

from dataclasses import dataclass


STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"


@dataclass(frozen=True)
class Department:
    id: int
    tenant_id: int
    parent_id: int | None
    code: str
    name: str
    manager_user_id: int | None
    base_location: str
    region: str
    status: str
    sort_order: int
    create_time: str
    update_time: str


@dataclass(frozen=True)
class UserDepartmentMembership:
    id: int
    tenant_id: int
    user_id: int
    department_id: int
    is_primary: bool
    create_time: str
    update_time: str


@dataclass(frozen=True)
class UserReportingRelationship:
    id: int
    tenant_id: int
    user_id: int
    manager_user_id: int
    is_primary: bool
    relationship_type: str
    create_time: str
    update_time: str
