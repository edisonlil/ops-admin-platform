from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import re
from typing import Any, Protocol


SCOPE_TENANT = "tenant"
SCOPE_SELF = "self"
SCOPE_SELF_AND_SUBORDINATES = "self_and_subordinates"
SCOPE_DEPARTMENT = "department"
SCOPE_DEPARTMENT_AND_CHILDREN = "department_and_children"
SCOPE_CUSTOM_DEPARTMENTS = "custom_departments"

ACCESS_MODE_OWNER_COLUMNS = "owner_columns"
ACCESS_MODE_RELATION_TABLE = "relation_table"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RELATION_ALIAS = "data_access_rel"


@dataclass(frozen=True)
class ResourceDescriptor:
    resource_key: str
    tenant_column: str = "tenant_id"
    resource_id_column: str = "id"
    creator_column: str = "creator_id"
    owner_user_column: str = "owner_user_id"
    owner_department_column: str = "owner_department_id"
    access_mode: str = ACCESS_MODE_OWNER_COLUMNS
    relation_table: str = ""
    relation_resource_id_column: str = ""
    relation_user_column: str = ""
    relation_department_column: str = ""
    relation_tenant_column: str = "tenant_id"
    relation_deleted_column: str = "deleted"
    relation_resource_key_column: str = ""
    relation_resource_key_value: str = ""
    relation_subject_type_column: str = ""
    relation_subject_type_user_value: str = ""
    relation_subject_type_department_value: str = ""
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
        clauses, params = self.to_sql_clauses(descriptor, alias=alias)
        return " AND ".join(clauses), params

    def to_sql_clauses(self, descriptor: ResourceDescriptor, *, alias: str = "") -> tuple[list[str], tuple[Any, ...]]:
        mode = normalized_access_mode(descriptor)
        if mode == ACCESS_MODE_RELATION_TABLE:
            return self._relation_table_clauses(descriptor, alias=alias)
        if mode == ACCESS_MODE_OWNER_COLUMNS:
            return self._owner_column_clauses(descriptor, alias=alias)
        return ["1 = 0"], ()

    def _owner_column_clauses(self, descriptor: ResourceDescriptor, *, alias: str = "") -> tuple[list[str], tuple[Any, ...]]:
        prefix = sql_prefix(alias)
        if prefix is None:
            return ["1 = 0"], ()
        if has_invalid_identifier(descriptor.tenant_column):
            return ["1 = 0"], ()
        tenant_column = normalized_identifier(descriptor.tenant_column)
        clauses: list[str] = []
        params: list[Any] = []
        if tenant_column:
            clauses.append(f"{prefix}{tenant_column} = ?")
            params.append(self.tenant_id)
        if self.scope == SCOPE_TENANT:
            return clauses, tuple(params)
        if self.scope == SCOPE_SELF:
            owner_value = descriptor.owner_user_column or descriptor.creator_column
            if has_invalid_identifier(owner_value):
                clauses.append("1 = 0")
                return clauses, tuple(params)
            owner_column = normalized_identifier(owner_value)
            if not owner_column:
                return clauses, tuple(params)
            clauses.append(f"{prefix}{owner_column} = ?")
            params.append(int(self.user_id or 0))
            return clauses, tuple(params)
        if self.scope == SCOPE_SELF_AND_SUBORDINATES:
            owner_value = descriptor.owner_user_column or descriptor.creator_column
            if has_invalid_identifier(owner_value):
                clauses.append("1 = 0")
                return clauses, tuple(params)
            owner_column = normalized_identifier(owner_value)
            if not owner_column:
                return clauses, tuple(params)
            user_ids = self.user_ids or ((int(self.user_id or 0),) if self.user_id else ())
            if not user_ids:
                clauses.append("1 = 0")
                return clauses, tuple(params)
            placeholders = ", ".join("?" for _ in user_ids)
            clauses.append(f"{prefix}{owner_column} IN ({placeholders})")
            params.extend(user_ids)
            return clauses, tuple(params)
        if self.scope in {SCOPE_DEPARTMENT, SCOPE_DEPARTMENT_AND_CHILDREN, SCOPE_CUSTOM_DEPARTMENTS}:
            if has_invalid_identifier(descriptor.owner_department_column):
                clauses.append("1 = 0")
                return clauses, tuple(params)
            department_column = normalized_identifier(descriptor.owner_department_column)
            if not department_column:
                clauses.append("1 = 0")
                return clauses, tuple(params)
            if not self.department_ids:
                clauses.append("1 = 0")
                return clauses, tuple(params)
            placeholders = ", ".join("?" for _ in self.department_ids)
            clauses.append(f"{prefix}{department_column} IN ({placeholders})")
            params.extend(self.department_ids)
            return clauses, tuple(params)
        clauses.append("1 = 0")
        return clauses, tuple(params)

    def _relation_table_clauses(self, descriptor: ResourceDescriptor, *, alias: str = "") -> tuple[list[str], tuple[Any, ...]]:
        prefix = sql_prefix(alias)
        if prefix is None:
            return ["1 = 0"], ()
        clauses: list[str] = []
        params: list[Any] = []
        if has_invalid_identifier(descriptor.tenant_column):
            return ["1 = 0"], ()
        tenant_column = normalized_identifier(descriptor.tenant_column)
        if tenant_column:
            clauses.append(f"{prefix}{tenant_column} = ?")
            params.append(self.tenant_id)
        if self.scope == SCOPE_TENANT:
            return clauses, tuple(params)
        relation = relation_config(descriptor)
        if relation is None:
            clauses.append("1 = 0")
            return clauses, tuple(params)
        subject_clause, subject_params = self._relation_subject_clause(descriptor)
        if not subject_clause:
            clauses.append("1 = 0")
            return clauses, tuple(params)
        relation_clauses = [
            f"{_RELATION_ALIAS}.{relation.relation_tenant_column} = ?",
            f"{_RELATION_ALIAS}.{relation.relation_resource_id_column} = {prefix}{relation.resource_id_column}",
        ]
        relation_params: list[Any] = [self.tenant_id]
        if relation.relation_deleted_column:
            relation_clauses.append(f"{_RELATION_ALIAS}.{relation.relation_deleted_column} = 0")
        if relation.relation_resource_key_column:
            relation_clauses.append(f"{_RELATION_ALIAS}.{relation.relation_resource_key_column} = ?")
            relation_params.append(str(descriptor.relation_resource_key_value or descriptor.resource_key))
        relation_clauses.append(subject_clause)
        relation_params.extend(subject_params)
        subject_type = relation_subject_type_value(descriptor, self.scope)
        if relation.relation_subject_type_column and subject_type is None:
            clauses.append("1 = 0")
            return clauses, tuple(params)
        if relation.relation_subject_type_column and subject_type is not None:
            relation_clauses.append(f"{_RELATION_ALIAS}.{relation.relation_subject_type_column} = ?")
            relation_params.append(subject_type)
        clauses.append(
            "EXISTS ("
            f"SELECT 1 FROM {relation.relation_table} {_RELATION_ALIAS} "
            f"WHERE {' AND '.join(relation_clauses)}"
            ")"
        )
        params.extend(relation_params)
        return clauses, tuple(params)

    def _relation_subject_clause(self, descriptor: ResourceDescriptor) -> tuple[str, tuple[Any, ...]]:
        if self.scope == SCOPE_SELF:
            if has_invalid_identifier(descriptor.relation_user_column):
                return "", ()
            user_column = normalized_identifier(descriptor.relation_user_column)
            if not user_column:
                return "", ()
            return f"{_RELATION_ALIAS}.{user_column} = ?", (int(self.user_id or 0),)
        if self.scope == SCOPE_SELF_AND_SUBORDINATES:
            if has_invalid_identifier(descriptor.relation_user_column):
                return "", ()
            user_column = normalized_identifier(descriptor.relation_user_column)
            user_ids = self.user_ids or ((int(self.user_id or 0),) if self.user_id else ())
            if not user_column or not user_ids:
                return "", ()
            placeholders = ", ".join("?" for _ in user_ids)
            return f"{_RELATION_ALIAS}.{user_column} IN ({placeholders})", tuple(user_ids)
        if self.scope in {SCOPE_DEPARTMENT, SCOPE_DEPARTMENT_AND_CHILDREN, SCOPE_CUSTOM_DEPARTMENTS}:
            if has_invalid_identifier(descriptor.relation_department_column):
                return "", ()
            department_column = normalized_identifier(descriptor.relation_department_column)
            if not department_column or not self.department_ids:
                return "", ()
            placeholders = ", ".join("?" for _ in self.department_ids)
            return f"{_RELATION_ALIAS}.{department_column} IN ({placeholders})", tuple(self.department_ids)
        return "", ()

    def allows_record(self, record: Any, descriptor: ResourceDescriptor) -> bool:
        tenant_column = str(descriptor.tenant_column or "").strip()
        if tenant_column and int(read_record_value(record, tenant_column) or 0) != int(self.tenant_id):
            return False
        if self.scope == SCOPE_TENANT:
            return True
        if normalized_access_mode(descriptor) == ACCESS_MODE_RELATION_TABLE:
            return False
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
    clauses, scope_params = data_scope.to_sql_clauses(descriptor, alias=alias)
    if not clauses:
        return
    prefix = f"{alias}." if alias else ""
    tenant_column = str(descriptor.tenant_column or "").strip()
    tenant_clause = f"{prefix}{tenant_column} = ?" if tenant_column else ""
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


@dataclass(frozen=True)
class RelationTableConfig:
    relation_table: str
    resource_id_column: str
    relation_resource_id_column: str
    relation_tenant_column: str
    relation_deleted_column: str
    relation_resource_key_column: str
    relation_subject_type_column: str


def normalized_access_mode(descriptor: ResourceDescriptor) -> str:
    mode = str(descriptor.access_mode or ACCESS_MODE_OWNER_COLUMNS).strip()
    return mode if mode in {ACCESS_MODE_OWNER_COLUMNS, ACCESS_MODE_RELATION_TABLE} else "deny"


def normalized_identifier(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if _IDENTIFIER_RE.fullmatch(text) else ""


def valid_identifier(value: Any) -> bool:
    return bool(normalized_identifier(value))


def has_invalid_identifier(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and not bool(_IDENTIFIER_RE.fullmatch(text))


def sql_prefix(alias: str) -> str | None:
    if not alias:
        return ""
    normalized = normalized_identifier(alias)
    return f"{normalized}." if normalized else None


def relation_config(descriptor: ResourceDescriptor) -> RelationTableConfig | None:
    identifier_values = (
        descriptor.relation_table,
        descriptor.resource_id_column or "id",
        descriptor.relation_resource_id_column,
        descriptor.relation_tenant_column,
        descriptor.relation_deleted_column,
        descriptor.relation_resource_key_column,
        descriptor.relation_subject_type_column,
    )
    if any(has_invalid_identifier(value) for value in identifier_values):
        return None
    relation_table = normalized_identifier(descriptor.relation_table)
    resource_id_column = normalized_identifier(descriptor.resource_id_column or "id")
    relation_resource_id_column = normalized_identifier(descriptor.relation_resource_id_column)
    relation_tenant_column = normalized_identifier(descriptor.relation_tenant_column)
    relation_deleted_column = normalized_identifier(descriptor.relation_deleted_column)
    relation_resource_key_column = normalized_identifier(descriptor.relation_resource_key_column)
    relation_subject_type_column = normalized_identifier(descriptor.relation_subject_type_column)
    if not (relation_table and resource_id_column and relation_resource_id_column and relation_tenant_column):
        return None
    return RelationTableConfig(
        relation_table=relation_table,
        resource_id_column=resource_id_column,
        relation_resource_id_column=relation_resource_id_column,
        relation_tenant_column=relation_tenant_column,
        relation_deleted_column=relation_deleted_column,
        relation_resource_key_column=relation_resource_key_column,
        relation_subject_type_column=relation_subject_type_column,
    )


def relation_subject_type_value(descriptor: ResourceDescriptor, scope: str) -> str | None:
    if scope in {SCOPE_SELF, SCOPE_SELF_AND_SUBORDINATES}:
        return str(descriptor.relation_subject_type_user_value or "").strip() or None
    if scope in {SCOPE_DEPARTMENT, SCOPE_DEPARTMENT_AND_CHILDREN, SCOPE_CUSTOM_DEPARTMENTS}:
        return str(descriptor.relation_subject_type_department_value or "").strip() or None
    return None


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
