from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from datasets.domain.exceptions import DatasetDomainError
from datasets.domain.models import Dataset, DatasetField
from system.application.data_access import ResourceDescriptor, resolve_data_access_filter
from system.application.database import connect, resolve_database_url, resolve_db_path


class SqlDatasetExecutor:
    def execute_preview(
        self,
        *,
        dataset: Dataset,
        fields: list[DatasetField],
        page: int,
        page_size: int,
        variables: dict[str, Any],
        current_user: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        _ = fields
        config = dataset.query_config if isinstance(dataset.query_config, dict) else {}
        sql = render_sql(str(config.get("sql") or ""), variables).strip()
        ensure_select_sql(sql)
        params = resolve_params(config.get("params"), variables)
        descriptor = resource_descriptor(config)
        predicate = resolve_data_access_filter(current_user=current_user, resource=descriptor, action="read")
        scope_sql, scope_params = predicate.to_sql(descriptor, alias="dataset_sql_source")
        base_sql = f"FROM ({sql}) AS dataset_sql_source"
        where_sql = f" WHERE {scope_sql}" if scope_sql else ""
        offset = (page - 1) * page_size
        max_rows = bounded_max_rows(config.get("max_rows"))
        limit = max(1, min(page_size, max_rows))
        rows_sql = f"SELECT * {base_sql}{where_sql} LIMIT ? OFFSET ?"
        count_sql = f"SELECT COUNT(*) AS total {base_sql}{where_sql}"
        query_params = [*params, *(scope_params if scope_sql else ())]
        try:
            with connect(database_target(), readonly=True) as conn:
                total_row = conn.execute(count_sql, tuple(query_params)).fetchone()
                rows = conn.execute(rows_sql, tuple([*query_params, limit, offset])).fetchall()
        except Exception as exc:
            raise DatasetDomainError(f"dataset source query failed: {exc}") from exc
        total = min(int(read_row_value(total_row, "total") or 0), max_rows)
        return [normalize_row(row) for row in rows], total, {"runtime": "source_query", "data_scope": predicate.scope}


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def ensure_select_sql(sql: str) -> None:
    compact = strip_sql_comments(sql).strip()
    if not compact:
        raise DatasetDomainError("source query SQL is required")
    statements = [item.strip() for item in compact.split(";") if item.strip()]
    if len(statements) > 1 or (compact.endswith(";") and len(statements) != 1):
        raise DatasetDomainError("source query only supports a single SELECT statement")
    if first_sql_token(compact) not in {"select", "with"}:
        raise DatasetDomainError("source query only supports SELECT statements")
    dangerous = re.search(
        r"\b(insert|update|delete|drop|alter|truncate|create|replace|merge|call|execute|grant|revoke)\b",
        compact,
        flags=re.IGNORECASE,
    )
    if dangerous:
        raise DatasetDomainError(f"source query rejected non-read-only keyword: {dangerous.group(1).upper()}")


def strip_sql_comments(sql: str) -> str:
    without_line_comments = re.sub(r"--.*?(?=\r?\n|$)", " ", sql)
    return re.sub(r"/\*.*?\*/", " ", without_line_comments, flags=re.DOTALL)


def first_sql_token(sql: str) -> str:
    match = re.match(r"\s*([a-zA-Z_]+)", sql)
    return match.group(1).lower() if match else ""


def render_sql(sql: str, variables: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = resolve_variable(variables, match.group(1).strip())
        return str(value if value is not None else "")

    return re.sub(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}", replace, sql)


def resolve_params(value: Any, variables: dict[str, Any]) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [resolve_param(item, variables) for item in value]
    if isinstance(value, dict):
        return [resolve_param(value[key], variables) for key in sorted(value)]
    raise DatasetDomainError("source query params must be an array or object")


def resolve_param(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{{") and stripped.endswith("}}"):
            return resolve_variable(variables, stripped[2:-2].strip())
    return value


def resolve_variable(variables: dict[str, Any], path: str) -> Any:
    current: Any = variables
    for part in [item for item in path.split(".") if item]:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def resource_descriptor(config: dict[str, Any]) -> ResourceDescriptor:
    data_access = config.get("data_access") if isinstance(config.get("data_access"), dict) else {}
    return ResourceDescriptor(
        resource_key=str(data_access.get("resource_key") or "dataset.source_query"),
        tenant_column=config_column(data_access, "tenant_column", "tenant_id"),
        creator_column=config_column(data_access, "creator_column", "creator_id"),
        owner_user_column=config_column(data_access, "owner_user_column", "owner_user_id"),
        owner_department_column=config_column(data_access, "owner_department_column", "owner_department_id"),
        requires_data_scope=bool(data_access.get("requires_data_scope", False)),
    )


def config_column(config: dict[str, Any], key: str, default: str) -> str:
    if key not in config:
        return default
    value = config.get(key)
    return "" if value is None else str(value).strip()


def bounded_max_rows(value: Any) -> int:
    try:
        parsed = int(value or 1000)
    except (TypeError, ValueError):
        parsed = 1000
    return max(1, min(1000, parsed))


def normalize_row(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    keys = getattr(row, "keys", None)
    if callable(keys):
        return {str(key): row[key] for key in keys()}
    if hasattr(row, "_asdict"):
        return dict(row._asdict())
    return {}


def read_row_value(row: Any, key: str) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, None)
