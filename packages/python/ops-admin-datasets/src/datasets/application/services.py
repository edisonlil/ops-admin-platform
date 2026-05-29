from __future__ import annotations

import re
from numbers import Number
from typing import Any

from datasets.application.ports import DatasetRepository, ExternalDatasetExecutorPort, SourceSchemaInspectorPort
from datasets.domain.exceptions import DatasetDomainError, DatasetNotFoundError, DatasetRuntimeUnavailableError, DatasetStorageNotReadyError
from datasets.domain.models import (
    DATASET_TYPE_MANUAL,
    DATASET_TYPE_SOURCE_QUERY,
    DATASET_TYPES,
    FIELD_TYPE_TEXT,
    FIELD_TYPES,
    STATUS_DRAFT,
    DATASET_STATUSES,
    Dataset,
    DatasetField,
)
from system.application.data_access import data_owner_fields
from system.application.sorting import InvalidSortError


repository: DatasetRepository | None = None
external_executor: ExternalDatasetExecutorPort | None = None
source_schema_inspector: SourceSchemaInspectorPort | None = None
PLATFORM_DATASET_TENANT_ID = 1


def configure_repository(dataset_repository: DatasetRepository) -> None:
    global repository
    repository = dataset_repository


def configure_external_executor(executor: ExternalDatasetExecutorPort | None) -> None:
    global external_executor
    external_executor = executor


def configure_source_schema_inspector(inspector: SourceSchemaInspectorPort | None) -> None:
    global source_schema_inspector
    source_schema_inspector = inspector


def repo() -> DatasetRepository:
    if repository is None:
        raise DatasetStorageNotReadyError("dataset repository is not configured")
    return repository


def list_datasets(
    *,
    page: int,
    page_size: int,
    keyword: str = "",
    status: str | None = None,
    dataset_type: str = "",
    current_user: dict[str, Any],
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    try:
        items, total = repo().list_datasets(
            tenant_id=platform_dataset_tenant_id(current_user),
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            dataset_type=dataset_type,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except InvalidSortError as exc:
        raise DatasetDomainError(str(exc)) from exc
    except RuntimeError as exc:
        raise DatasetStorageNotReadyError(str(exc)) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def dataset_detail(dataset_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    dataset = ensure_dataset_access(dataset_id, current_user=current_user, action="read")
    fields = repo().list_fields(tenant_id=platform_dataset_tenant_id(current_user), dataset_id=dataset_id)
    return {"item": dataset.to_dict(), "fields": [field.to_dict() for field in fields]}


def save_dataset(payload: dict[str, Any], current_user: dict[str, Any], dataset_id: int | None = None) -> dict[str, Any]:
    tenant_id = platform_dataset_tenant_id(current_user)
    normalized = normalize_dataset_payload({**payload, "id": dataset_id or payload.get("id")})
    if int(normalized.get("id") or 0):
        ensure_dataset_access(int(normalized["id"]), current_user=current_user, action="write")
    normalized.update(data_owner_fields(current_user))
    item = Dataset(
        id=int(normalized.get("id") or 0),
        tenant_id=tenant_id,
        create_time="",
        update_time="",
        **dataset_model_fields(normalized),
    )
    item.validate()
    try:
        saved = repo().save_dataset(
            tenant_id=tenant_id,
            payload=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise DatasetStorageNotReadyError(str(exc)) from exc
    return {"item": saved.to_dict()}


def delete_dataset(dataset_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    dataset = ensure_dataset_access(dataset_id, current_user=current_user, action="manage")
    try:
        deleted = repo().delete_dataset(
            tenant_id=platform_dataset_tenant_id(current_user),
            dataset_id=dataset.id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise DatasetStorageNotReadyError(str(exc)) from exc
    if not deleted:
        raise DatasetNotFoundError("dataset not found")
    return {"id": dataset_id, "deleted": True}


def save_fields(dataset_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    dataset = ensure_dataset_access(dataset_id, current_user=current_user, action="write")
    raw_fields = payload.get("fields")
    if not isinstance(raw_fields, list):
        raise DatasetDomainError("fields must be an array")
    normalized = normalize_fields(raw_fields)
    try:
        fields = repo().replace_fields(
            tenant_id=platform_dataset_tenant_id(current_user),
            dataset_id=dataset.id,
            fields=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise DatasetStorageNotReadyError(str(exc)) from exc
    return {"items": [field.to_dict() for field in fields]}


def save_manual_rows(dataset_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    dataset = ensure_dataset_access(dataset_id, current_user=current_user, action="write")
    if dataset.dataset_type != DATASET_TYPE_MANUAL:
        raise DatasetDomainError("only manual datasets can store manual rows")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise DatasetDomainError("rows must be an array")
    normalized = normalize_manual_rows(rows)
    try:
        count = repo().replace_manual_rows(
            tenant_id=platform_dataset_tenant_id(current_user),
            dataset_id=dataset.id,
            rows=normalized,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise DatasetStorageNotReadyError(str(exc)) from exc
    return {"count": count}


def publish_dataset(dataset_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    dataset = ensure_dataset_access(dataset_id, current_user=current_user, action="manage")
    preview = preview_dataset(
        dataset_id=dataset.id,
        page=1,
        page_size=20,
        current_user=current_user,
        apply_data_access=False,
    )
    rows = preview.get("items") if isinstance(preview.get("items"), list) else []
    fields = fields_from_dicts(preview.get("fields"))
    schema = {"fields": [field.to_dict() for field in fields]}
    try:
        version = repo().publish_dataset(
            tenant_id=platform_dataset_tenant_id(current_user),
            dataset_id=dataset.id,
            schema=schema,
            query_config=dataset.query_config,
            sample_rows=rows,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise DatasetStorageNotReadyError(str(exc)) from exc
    return {"item": version.to_dict()}


def preview_dataset(
    *,
    dataset_id: int,
    page: int,
    page_size: int,
    variables: dict[str, Any] | None = None,
    query_config: dict[str, Any] | None = None,
    current_user: dict[str, Any],
    apply_data_access: bool = True,
) -> dict[str, Any]:
    dataset = ensure_dataset_access(dataset_id, current_user=current_user, action="read")
    configured_fields = repo().list_fields(tenant_id=platform_dataset_tenant_id(current_user), dataset_id=dataset.id)
    if query_config is not None:
        if dataset.dataset_type != DATASET_TYPE_SOURCE_QUERY:
            raise DatasetDomainError("temporary query_config is only supported for source query datasets")
        dataset = clone_dataset_with_query_config(dataset, normalize_query_config(query_config))
    if dataset.dataset_type == DATASET_TYPE_MANUAL:
        rows, total = repo().list_manual_rows(
            tenant_id=platform_dataset_tenant_id(current_user),
            dataset_id=dataset.id,
            page=page,
            page_size=page_size,
        )
        fields = infer_result_fields(rows, fallback_fields=configured_fields)
        return runtime_payload(dataset, fields, rows, total, page, page_size, {"runtime": "manual"})
    if dataset.dataset_type == DATASET_TYPE_SOURCE_QUERY:
        validate_source_query_ready(dataset)
    if external_executor is None:
        raise DatasetRuntimeUnavailableError("dataset runtime executor is unavailable")
    rows, total, meta = external_executor.execute_preview(
        dataset=dataset,
        fields=configured_fields,
        page=page,
        page_size=page_size,
        variables=variables or {},
        current_user=current_user,
        apply_data_access=apply_data_access,
    )
    fields = infer_result_fields(rows, fallback_fields=configured_fields)
    return runtime_payload(dataset, fields, rows, total, page, page_size, {"runtime": "external", **meta})


def source_schema(dataset_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    dataset = ensure_dataset_access(dataset_id, current_user=current_user, action="read")
    if dataset.dataset_type != DATASET_TYPE_SOURCE_QUERY:
        raise DatasetDomainError("source schema is only supported for source query datasets")
    if source_schema_inspector is None:
        raise DatasetRuntimeUnavailableError("dataset source schema inspector is unavailable")
    return source_schema_inspector.inspect_source_schema()


def clone_dataset_with_query_config(dataset: Dataset, query_config: dict[str, Any]) -> Dataset:
    return Dataset(
        id=dataset.id,
        tenant_id=dataset.tenant_id,
        key=dataset.key,
        name=dataset.name,
        description=dataset.description,
        dataset_type=dataset.dataset_type,
        status=dataset.status,
        visibility=dataset.visibility,
        query_config=query_config,
        owner_user_id=dataset.owner_user_id,
        owner_department_id=dataset.owner_department_id,
        published_version_id=dataset.published_version_id,
        field_count=dataset.field_count,
        row_count=dataset.row_count,
        create_time=dataset.create_time,
        update_time=dataset.update_time,
    )


def runtime_payload(
    dataset: Dataset,
    fields: list[DatasetField],
    rows: list[dict[str, Any]],
    total: int,
    page: int,
    page_size: int,
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dataset": dataset.to_dict(),
        "fields": [field.to_dict() for field in fields],
        "items": rows,
        "pagination": {"page": page, "page_size": page_size, "total": total},
        "meta": {"published_version_id": dataset.published_version_id, **meta},
    }


def ensure_dataset_access(dataset_id: int, *, current_user: dict[str, Any], action: str) -> Dataset:
    _ = action
    tenant_id = platform_dataset_tenant_id(current_user)
    try:
        row = repo().get_dataset_row(tenant_id=tenant_id, dataset_id=dataset_id)
    except RuntimeError as exc:
        raise DatasetStorageNotReadyError(str(exc)) from exc
    if not row:
        raise DatasetNotFoundError("dataset not found")
    dataset = repo().get_dataset(tenant_id=tenant_id, dataset_id=dataset_id)
    if dataset is None:
        raise DatasetNotFoundError("dataset not found")
    return dataset


def normalize_dataset_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "id": int(payload.get("id") or 0),
        "key": str(payload.get("key") or "").strip(),
        "name": str(payload.get("name") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "dataset_type": str(payload.get("dataset_type") or DATASET_TYPE_MANUAL).strip() or DATASET_TYPE_MANUAL,
        "status": str(payload.get("status") or STATUS_DRAFT).strip() or STATUS_DRAFT,
        "visibility": str(payload.get("visibility") or "platform").strip() or "platform",
        "published_version_id": payload.get("published_version_id"),
        "query_config": normalize_query_config(payload.get("query_config")),
    }
    if normalized["dataset_type"] not in DATASET_TYPES:
        raise DatasetDomainError(f"unsupported dataset_type: {normalized['dataset_type']}")
    if normalized["status"] not in DATASET_STATUSES:
        raise DatasetDomainError(f"unsupported dataset status: {normalized['status']}")
    return normalized


def dataset_model_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": str(payload.get("key") or "").strip(),
        "name": str(payload.get("name") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "dataset_type": str(payload.get("dataset_type") or DATASET_TYPE_MANUAL),
        "status": str(payload.get("status") or STATUS_DRAFT),
        "visibility": str(payload.get("visibility") or "platform"),
        "query_config": payload.get("query_config") if isinstance(payload.get("query_config"), dict) else {},
        "owner_user_id": payload.get("owner_user_id"),
        "owner_department_id": payload.get("owner_department_id"),
        "published_version_id": payload.get("published_version_id"),
    }


def normalize_fields(raw_fields: list[Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_fields):
        if not isinstance(raw, dict):
            raise DatasetDomainError("each field must be an object")
        field_key = str(raw.get("field_key") or "").strip()
        if not field_key:
            raise DatasetDomainError("field_key is required")
        if field_key in seen:
            raise DatasetDomainError(f"duplicate field_key: {field_key}")
        seen.add(field_key)
        data_type = str(raw.get("data_type") or FIELD_TYPE_TEXT).strip() or FIELD_TYPE_TEXT
        if data_type not in FIELD_TYPES:
            raise DatasetDomainError(f"unsupported field data_type: {data_type}")
        item = {
            "field_key": field_key,
            "label": str(raw.get("label") or field_key).strip(),
            "data_type": data_type,
            "semantic_type": str(raw.get("semantic_type") or "").strip(),
            "unit": str(raw.get("unit") or "").strip(),
            "precision": raw.get("precision"),
            "nullable": bool(raw.get("nullable", True)),
            "visible": bool(raw.get("visible", True)),
            "sort_order": int(raw.get("sort_order") if raw.get("sort_order") is not None else index),
            "expression": str(raw.get("expression") or "").strip(),
            "config": raw.get("config") if isinstance(raw.get("config"), dict) else {},
        }
        DatasetField(id=0, tenant_id=0, dataset_id=0, create_time="", update_time="", **item).validate()
        fields.append(item)
    return fields


def normalize_manual_rows(rows: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in rows:
        if isinstance(item, dict):
            normalized.append(item)
        elif isinstance(item, (str, int, float, bool)) or item is None:
            normalized.append({"value": item})
        else:
            raise DatasetDomainError("manual data rows must be objects or scalar values")
    return normalized


def infer_result_fields(rows: list[dict[str, Any]], fallback_fields: list[DatasetField] | None = None) -> list[DatasetField]:
    field_keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in field_keys:
                field_keys.append(key)
    if not field_keys and fallback_fields:
        return fallback_fields
    configured = {field.field_key: field for field in fallback_fields or []}
    return [
        inferred_field(key, index, rows, configured.get(key))
        for index, key in enumerate(field_keys)
    ]


def inferred_field(field_key: str, index: int, rows: list[dict[str, Any]], configured: DatasetField | None = None) -> DatasetField:
    values = [row.get(field_key) for row in rows]
    return DatasetField(
        id=configured.id if configured else 0,
        tenant_id=configured.tenant_id if configured else 0,
        dataset_id=configured.dataset_id if configured else 0,
        field_key=field_key,
        label=configured.label if configured else inferred_field_label(field_key),
        data_type=configured.data_type if configured else infer_result_field_type(values),
        semantic_type=configured.semantic_type if configured else "",
        unit=configured.unit if configured else "",
        precision=configured.precision if configured else None,
        nullable=any(value is None for value in values),
        visible=configured.visible if configured else True,
        sort_order=configured.sort_order if configured else index,
        expression=configured.expression if configured else "",
        config=configured.config if configured else {},
        create_time=configured.create_time if configured else "",
        update_time=configured.update_time if configured else "",
    )


def inferred_field_label(field_key: str) -> str:
    return "值" if field_key == "value" else field_key


def infer_result_field_type(values: list[Any]) -> str:
    present = [value for value in values if value is not None]
    if present and all(isinstance(value, bool) for value in present):
        return "boolean"
    if present and all(isinstance(value, Number) and not isinstance(value, bool) for value in present):
        return "number"
    return FIELD_TYPE_TEXT


def fields_from_dicts(value: Any) -> list[DatasetField]:
    if not isinstance(value, list):
        return []
    fields: list[DatasetField] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        field_key = str(item.get("field_key") or "").strip()
        if not field_key:
            continue
        fields.append(
            DatasetField(
                id=int(item.get("id") or 0),
                tenant_id=int(item.get("tenant_id") or 0),
                dataset_id=int(item.get("dataset_id") or 0),
                field_key=field_key,
                label=str(item.get("label") or inferred_field_label(field_key)),
                data_type=str(item.get("data_type") or FIELD_TYPE_TEXT),
                semantic_type=str(item.get("semantic_type") or ""),
                unit=str(item.get("unit") or ""),
                precision=item.get("precision") if isinstance(item.get("precision"), int) else None,
                nullable=bool(item.get("nullable", True)),
                visible=bool(item.get("visible", True)),
                sort_order=int(item.get("sort_order") if item.get("sort_order") is not None else index),
                expression=str(item.get("expression") or ""),
                config=item.get("config") if isinstance(item.get("config"), dict) else {},
                create_time=str(item.get("create_time") or ""),
                update_time=str(item.get("update_time") or ""),
            )
        )
    return fields


def normalize_query_config(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise DatasetDomainError("query_config must be an object")
    config = dict(value)
    sql = str(config.get("sql") or config.get("query") or "").strip()
    if sql:
        ensure_select_sql(sql)
    params = config.get("params")
    if params in (None, ""):
        params = []
    if not isinstance(params, (list, dict)):
        raise DatasetDomainError("query_config.params must be an array or object")
    data_access = config.get("data_access")
    if data_access in (None, ""):
        data_access = {}
    if not isinstance(data_access, dict):
        raise DatasetDomainError("query_config.data_access must be an object")
    max_rows = config.get("max_rows")
    if max_rows in (None, ""):
        max_rows = 1000
    try:
        max_rows = max(1, min(1000, int(max_rows)))
    except (TypeError, ValueError) as exc:
        raise DatasetDomainError("query_config.max_rows must be a number") from exc
    return {
        **config,
        "sql": sql,
        "params": params,
        "data_access": data_access,
        "max_rows": max_rows,
    }


def validate_source_query_ready(dataset: Dataset) -> None:
    config = dataset.query_config if isinstance(dataset.query_config, dict) else {}
    sql = str(config.get("sql") or "").strip()
    if not sql:
        raise DatasetDomainError("source query dataset requires query_config.sql")
    ensure_select_sql(sql)


def ensure_select_sql(sql: str) -> None:
    compact = strip_sql_comments(sql).strip()
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


def platform_dataset_tenant_id(current_user: dict[str, Any]) -> int:
    current = current_user.get("current_tenant")
    if isinstance(current, dict) and str(current.get("tenant_key") or "").strip() == "platform" and current.get("id") is not None:
        return int(current.get("id") or 0)
    return PLATFORM_DATASET_TENANT_ID


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    value = current_user.get("id")
    return int(value) if value not in (None, "") else None
