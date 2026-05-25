from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any, Protocol


SCOPE_TENANT = "tenant"
SCOPE_SELF = "self"
SCOPE_SELF_AND_SUBORDINATES = "self_and_subordinates"
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
        SCOPE_SELF_AND_SUBORDINATES,
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
    user_ids: tuple[int, ...] = field(default_factory=tuple)
    department_ids: tuple[int, ...] = field(default_factory=tuple)

    def to_sql(self, descriptor: ResourceDescriptor, *, alias: str = "") -> tuple[str, tuple[Any, ...]]:
        prefix = f"{alias}." if alias else ""
        tenant_column = str(descriptor.tenant_column or "").strip()
        clauses: list[str] = []
        params: list[Any] = []
        if tenant_column:
            clauses.append(f"{prefix}{tenant_column} = ?")
            params.append(self.tenant_id)
        if self.scope == SCOPE_TENANT:
            return " AND ".join(clauses), tuple(params)
        if self.scope == SCOPE_SELF:
            owner_column = descriptor.owner_user_column or descriptor.creator_column
            owner_column = str(owner_column or "").strip()
            if not owner_column:
                return " AND ".join(clauses), tuple(params)
            clauses.append(f"{prefix}{owner_column} = ?")
            params.append(int(self.user_id or 0))
            return " AND ".join(clauses), tuple(params)
        if self.scope == SCOPE_SELF_AND_SUBORDINATES:
            owner_column = descriptor.owner_user_column or descriptor.creator_column
            owner_column = str(owner_column or "").strip()
            if not owner_column:
                return " AND ".join(clauses), tuple(params)
            user_ids = self.user_ids or ((int(self.user_id or 0),) if self.user_id else ())
            if not user_ids:
                clauses.append("1 = 0")
                return " AND ".join(clauses), tuple(params)
            placeholders = ", ".join("?" for _ in user_ids)
            clauses.append(f"{prefix}{owner_column} IN ({placeholders})")
            params.extend(user_ids)
            return " AND ".join(clauses), tuple(params)
        if self.scope in {SCOPE_DEPARTMENT, SCOPE_DEPARTMENT_AND_CHILDREN, SCOPE_CUSTOM_DEPARTMENTS}:
            department_column = str(descriptor.owner_department_column or "").strip()
            if not department_column:
                clauses.append("1 = 0")
                return " AND ".join(clauses), tuple(params)
            if not self.department_ids:
                clauses.append("1 = 0")
                return " AND ".join(clauses), tuple(params)
            placeholders = ", ".join("?" for _ in self.department_ids)
            clauses.append(f"{prefix}{department_column} IN ({placeholders})")
            params.extend(self.department_ids)
            return " AND ".join(clauses), tuple(params)
        clauses.append("1 = 0")
        return " AND ".join(clauses), tuple(params)

    def allows_record(self, record: Any, descriptor: ResourceDescriptor) -> bool:
        tenant_column = str(descriptor.tenant_column or "").strip()
        if tenant_column and int(read_record_value(record, tenant_column) or 0) != int(self.tenant_id):
            return False
        if self.scope == SCOPE_TENANT:
            return True
        if self.scope == SCOPE_SELF:
            owner_column = descriptor.owner_user_column or descriptor.creator_column
            owner_column = str(owner_column or "").strip()
            if not owner_column:
                return False
            return int(read_record_value(record, owner_column) or 0) == int(self.user_id or 0)
        if self.scope == SCOPE_SELF_AND_SUBORDINATES:
            owner_column = descriptor.owner_user_column or descriptor.creator_column
            owner_column = str(owner_column or "").strip()
            if not owner_column:
                return False
            user_ids = self.user_ids or ((int(self.user_id or 0),) if self.user_id else ())
            return int(read_record_value(record, owner_column) or 0) in set(user_ids)
        if self.scope in {SCOPE_DEPARTMENT, SCOPE_DEPARTMENT_AND_CHILDREN, SCOPE_CUSTOM_DEPARTMENTS}:
            department_column = str(descriptor.owner_department_column or "").strip()
            if not department_column:
                return False
            if not self.department_ids:
                return False
            return int(read_record_value(record, department_column) or 0) in set(self.department_ids)
        return False


class DataAccessDeniedError(PermissionError):
    pass


@dataclass(frozen=True)
class DataAccessContext:
    current_user: dict[str, Any]
    resource: ResourceDescriptor

    def predicate(self, action: str) -> DataAccessPredicate:
        return resolve_data_access_filter(current_user=self.current_user, resource=self.resource, action=action)

    def read(self) -> DataAccessPredicate:
        return self.predicate("read")

    def write(self) -> DataAccessPredicate:
        return self.predicate("write")

    def manage(self) -> DataAccessPredicate:
        return self.predicate("manage")

    def apply_sql(
        self,
        where: list[str],
        params: list[Any],
        *,
        action: str = "read",
        alias: str = "",
    ) -> None:
        append_data_scope_sql(where, params, self.predicate(action), self.resource, alias=alias)

    def ensure_record(
        self,
        record: Any,
        *,
        action: str,
        denied: Exception | Callable[[], Exception] | None = None,
    ) -> None:
        ensure_data_access_record(
            record,
            current_user=self.current_user,
            resource=self.resource,
            action=action,
            denied=denied,
        )


def data_access_for(current_user: dict[str, Any], resource: ResourceDescriptor) -> DataAccessContext:
    return DataAccessContext(current_user=current_user, resource=resource)


def data_scope(current_user: dict[str, Any], resource: ResourceDescriptor, action: str = "read") -> DataAccessPredicate:
    return data_access_for(current_user, resource).predicate(action)


def apply_data_access(
    where: list[str],
    params: list[Any],
    *,
    current_user: dict[str, Any] | None = None,
    resource: ResourceDescriptor,
    action: str = "read",
    data_scope: DataAccessPredicate | None = None,
    alias: str = "",
) -> None:
    predicate = data_scope or (
        resolve_data_access_filter(current_user=current_user, resource=resource, action=action) if current_user is not None else None
    )
    append_data_scope_sql(where, params, predicate, resource, alias=alias)


def ensure_data_access_record(
    record: Any,
    *,
    current_user: dict[str, Any],
    resource: ResourceDescriptor,
    action: str,
    denied: Exception | Callable[[], Exception] | None = None,
) -> None:
    predicate = resolve_data_access_filter(current_user=current_user, resource=resource, action=action)
    if record is not None and predicate.allows_record(record, resource):
        return
    if denied is None:
        raise DataAccessDeniedError(f"data access denied for resource {resource.resource_key}")
    if callable(denied):
        raise denied()
    raise denied


def data_owner_fields(current_user: dict[str, Any]) -> dict[str, int | None]:
    return {
        "owner_user_id": current_user_id_or_none(current_user),
        "owner_department_id": current_user_primary_department_id(current_user),
    }


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
    tenant_column = str(descriptor.tenant_column or "").strip()
    tenant_clause = f"{prefix}{tenant_column} = ?" if tenant_column else ""
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


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None


def read_record_value(record: Any, key: str) -> Any:
    if not key:
        return None
    if isinstance(record, dict):
        return record.get(key)
    return getattr(record, key, None)


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
