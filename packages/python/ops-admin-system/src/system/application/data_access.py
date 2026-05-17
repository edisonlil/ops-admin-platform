from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


SCOPE_TENANT = "tenant"
SCOPE_SELF = "self"
SCOPE_DEPARTMENT = "department"
SCOPE_DEPARTMENT_AND_CHILDREN = "department_and_children"
SCOPE_CUSTOM_DEPARTMENTS = "custom_departments"


@dataclass(frozen=True)
class ResourceDescriptor:
    resource_key: str
    tenant_column: str = "tenant_id"
    creator_column: str = "creator_id"
    owner_user_column: str = "owner_user_id"
    owner_department_column: str = "owner_department_id"
    requires_data_scope: bool = False
    supported_scopes: tuple[str, ...] = (
        SCOPE_SELF,
        SCOPE_DEPARTMENT,
        SCOPE_DEPARTMENT_AND_CHILDREN,
        SCOPE_CUSTOM_DEPARTMENTS,
        SCOPE_TENANT,
    )


@dataclass(frozen=True)
class DataAccessPredicate:
    tenant_id: int
    scope: str = SCOPE_TENANT
    user_id: int | None = None
    department_ids: tuple[int, ...] = field(default_factory=tuple)

    def to_sql(self, descriptor: ResourceDescriptor, *, alias: str = "") -> tuple[str, tuple[Any, ...]]:
        prefix = f"{alias}." if alias else ""
        clauses = [f"{prefix}{descriptor.tenant_column} = ?"]
        params: list[Any] = [self.tenant_id]
        if self.scope == SCOPE_TENANT:
            return " AND ".join(clauses), tuple(params)
        if self.scope == SCOPE_SELF:
            owner_column = descriptor.owner_user_column or descriptor.creator_column
            clauses.append(f"{prefix}{owner_column} = ?")
            params.append(int(self.user_id or 0))
            return " AND ".join(clauses), tuple(params)
        if self.scope in {SCOPE_DEPARTMENT, SCOPE_DEPARTMENT_AND_CHILDREN, SCOPE_CUSTOM_DEPARTMENTS}:
            if not self.department_ids:
                clauses.append("1 = 0")
                return " AND ".join(clauses), tuple(params)
            placeholders = ", ".join("?" for _ in self.department_ids)
            clauses.append(f"{prefix}{descriptor.owner_department_column} IN ({placeholders})")
            params.extend(self.department_ids)
            return " AND ".join(clauses), tuple(params)
        clauses.append("1 = 0")
        return " AND ".join(clauses), tuple(params)


def append_data_scope_sql(
    where: list[str],
    params: list[Any],
    data_scope: DataAccessPredicate | None,
    descriptor: ResourceDescriptor,
    *,
    alias: str = "",
) -> None:
    if data_scope is None:
        return
    sql, scope_params = data_scope.to_sql(descriptor, alias=alias)
    if not sql:
        return
    prefix = f"{alias}." if alias else ""
    tenant_clause = f"{prefix}{descriptor.tenant_column} = ?"
    clauses = [clause.strip() for clause in sql.split(" AND ") if clause.strip()]
    params_to_add = list(scope_params)
    for clause in clauses:
        if clause == tenant_clause:
            if params_to_add:
                params_to_add.pop(0)
            continue
        where.append(clause)
    params.extend(params_to_add)


def current_user_primary_department_id(current_user: dict[str, Any]) -> int | None:
    departments = current_user.get("departments") or []
    primary = next((item for item in departments if bool(item.get("is_primary"))), departments[0] if departments else None)
    if not primary:
        return None
    department_id = int(primary.get("department_id") or primary.get("id") or 0)
    return department_id or None


class DataAccessFilterProvider(Protocol):
    def resolve_filter(
        self,
        *,
        current_user: dict[str, Any],
        resource: ResourceDescriptor,
        action: str,
    ) -> DataAccessPredicate: ...


class TenantOnlyDataAccessFilterProvider:
    def resolve_filter(
        self,
        *,
        current_user: dict[str, Any],
        resource: ResourceDescriptor,
        action: str,
    ) -> DataAccessPredicate:
        current = current_user.get("current_tenant") or {}
        tenant_id = int(current.get("id") or current_user.get("tenant_id") or 0)
        if resource.requires_data_scope:
            return DataAccessPredicate(tenant_id=tenant_id, scope="deny")
        return DataAccessPredicate(tenant_id=tenant_id, scope=SCOPE_TENANT, user_id=int(current_user.get("id", 0) or 0))


_provider: DataAccessFilterProvider = TenantOnlyDataAccessFilterProvider()


def configure_data_access_filter_provider(provider: DataAccessFilterProvider | None) -> None:
    global _provider
    _provider = provider or TenantOnlyDataAccessFilterProvider()


def resolve_data_access_filter(
    *,
    current_user: dict[str, Any],
    resource: ResourceDescriptor,
    action: str,
) -> DataAccessPredicate:
    return _provider.resolve_filter(current_user=current_user, resource=resource, action=action)
