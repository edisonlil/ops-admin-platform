from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from audit_logging.domain.models import AuditLoggingSettings
from audit_logging.infrastructure.persistence.bootstrap import require_audit_logging_schema
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, apply_data_access
from system.application.database import connect, resolve_database_url, resolve_db_path
from system.application.sorting import build_order_by, parse_sort_params


TABLE_BY_CATEGORY = {
    "system": "audit_system_logs",
    "operation": "audit_operation_logs",
    "api": "audit_api_logs",
    "sql": "audit_sql_logs",
    "visitor": "audit_visitor_logs",
}
RESOURCE_BY_CATEGORY = {
    "system": ResourceDescriptor(resource_key="audit.system-log"),
    "operation": ResourceDescriptor(resource_key="audit.operation-log"),
    "api": ResourceDescriptor(resource_key="audit.api-log"),
    "sql": ResourceDescriptor(resource_key="audit.sql-log"),
    "visitor": ResourceDescriptor(resource_key="audit.visitor-log"),
}
COMMON_COLUMNS = (
    "tenant_id",
    "event_time",
    "request_id",
    "correlation_id",
    "event_action",
    "event_outcome",
    "severity",
    "source_module",
    "actor_user_id",
    "actor_name",
    "actor_type",
    "owner_user_id",
    "owner_department_id",
    "owner_department_path",
    "client_ip",
    "user_agent",
    "summary",
    "detail_json",
    "creator",
    "creator_id",
    "editor",
    "editor_id",
)
EXTRA_COLUMNS = {
    "operation": (
        "target_owner_user_id",
        "target_owner_department_id",
        "operation_type",
        "resource_type",
        "resource_id",
        "resource_name",
        "risk_level",
        "before_json",
        "after_json",
        "diff_json",
        "error_code",
        "error_message",
    ),
    "api": (
        "request_method",
        "request_path",
        "route_name",
        "query_summary_json",
        "status_code",
        "business_code",
        "success",
        "duration_ms",
        "request_size_bytes",
        "response_size_bytes",
        "referer",
        "error_message",
    ),
    "sql": (
        "database_backend",
        "statement_type",
        "table_names_json",
        "sql_fingerprint",
        "sql_template",
        "duration_ms",
        "row_count",
        "success",
        "error_code",
        "error_message",
    ),
    "visitor": (
        "visitor_id",
        "session_id_hash",
        "ip_hash",
        "device_type",
        "browser",
        "os",
        "referer",
        "entry_path",
        "failure_reason",
        "geo_country",
        "geo_region",
        "geo_city",
    ),
}
COMMON_SORT_COLUMNS = {
    "id": "id",
    "tenant_id": "tenant_id",
    "event_time": "event_time",
    "request_id": "request_id",
    "correlation_id": "correlation_id",
    "event_action": "event_action",
    "event_outcome": "event_outcome",
    "severity": "severity",
    "source_module": "source_module",
    "actor_user_id": "actor_user_id",
    "actor_name": "actor_name",
    "actor_type": "actor_type",
    "client_ip": "client_ip",
    "summary": "summary",
    "create_time": "create_time",
    "update_time": "update_time",
}
EXTRA_SORT_COLUMNS = {
    category: {column: column for column in columns}
    for category, columns in EXTRA_COLUMNS.items()
}


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def insert_many(records: list[dict[str, Any]]) -> None:
    if not records:
        return
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        category = str(record.get("category") or "")
        if category in TABLE_BY_CATEGORY:
            grouped.setdefault(category, []).append(record)
    if not grouped:
        return
    with connect(database_target(), readonly=False) as conn:
        require_audit_logging_schema(conn)
        for category, items in grouped.items():
            table_name = TABLE_BY_CATEGORY[category]
            columns = (*COMMON_COLUMNS, *EXTRA_COLUMNS.get(category, ()))
            placeholders = ", ".join("?" for _ in columns)
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            for item in items:
                conn.execute(sql, tuple(value_for_column(item, column) for column in columns))


def list_logs(
    *,
    category: str,
    tenant_id: int | None,
    page: int,
    page_size: int,
    keyword: str,
    outcome: str,
    severity: str,
    data_scope: DataAccessPredicate | None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    table_name = TABLE_BY_CATEGORY[category]
    offset = (page - 1) * page_size
    where = ["deleted = 0"]
    params: list[Any] = []
    if tenant_id is not None:
        where.append("tenant_id = ?")
        params.append(tenant_id)
    if outcome:
        where.append("event_outcome = ?")
        params.append(outcome)
    if severity:
        where.append("severity = ?")
        params.append(severity)
    if keyword:
        where.append("(summary LIKE ? OR request_id LIKE ? OR actor_name LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
    apply_data_access(
        where,
        params,
        resource=RESOURCE_BY_CATEGORY[category],
        data_scope=data_scope,
    )
    where_sql = " AND ".join(where)
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed={**COMMON_SORT_COLUMNS, **EXTRA_SORT_COLUMNS.get(category, {})},
        default="event_time DESC, id DESC",
        tie_breaker="id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_audit_logging_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM {table_name} WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT *
            FROM {table_name}
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            tuple([*params, page_size, offset]),
        ).fetchall()
    return [row_to_log(category, dict(row)) for row in rows], total


def list_settings() -> list[AuditLoggingSettings]:
    with connect(database_target(), readonly=True) as conn:
        require_audit_logging_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM audit_logging_settings
            WHERE deleted = 0
            ORDER BY tenant_id ASC, id ASC
            """
        ).fetchall()
    if not rows:
        return [default_settings()]
    return [row_to_settings(dict(row)) for row in rows]


def get_effective_settings(tenant_id: int) -> AuditLoggingSettings:
    with connect(database_target(), readonly=True) as conn:
        require_audit_logging_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM audit_logging_settings
            WHERE tenant_id = ? AND deleted = 0
            """,
            (tenant_id,),
        ).fetchone()
        if not row and tenant_id != 0:
            row = conn.execute(
                "SELECT * FROM audit_logging_settings WHERE tenant_id = 0 AND deleted = 0",
            ).fetchone()
    if row:
        return row_to_settings(dict(row))
    return default_settings()


def save_settings(tenant_id: int, payload: dict[str, Any], *, actor: str, actor_id: int | None) -> AuditLoggingSettings:
    current = get_effective_settings(tenant_id)
    timestamp = now_iso()
    values = {
        "api_log_enabled": bool(payload.get("api_log_enabled", current.api_log_enabled)),
        "operation_log_enabled": bool(payload.get("operation_log_enabled", current.operation_log_enabled)),
        "sql_log_enabled": bool(payload.get("sql_log_enabled", current.sql_log_enabled)),
        "visitor_log_enabled": bool(payload.get("visitor_log_enabled", current.visitor_log_enabled)),
        "system_log_enabled": bool(payload.get("system_log_enabled", current.system_log_enabled)),
        "slow_sql_threshold_ms": bounded_int(payload.get("slow_sql_threshold_ms", current.slow_sql_threshold_ms), 50, 60000),
        "queue_max_size": bounded_int(payload.get("queue_max_size", current.queue_max_size), 1000, 1000000),
        "batch_size": bounded_int(payload.get("batch_size", current.batch_size), 1, 10000),
        "flush_interval_ms": bounded_int(payload.get("flush_interval_ms", current.flush_interval_ms), 100, 60000),
        "plaintext_ip_retention_days": bounded_int(
            payload.get("plaintext_ip_retention_days", current.plaintext_ip_retention_days),
            0,
            3650,
        ),
        "log_retention_days": bounded_int(payload.get("log_retention_days", current.log_retention_days), 1, 3650),
        "include_request_headers": bool(payload.get("include_request_headers", current.include_request_headers)),
        "include_response_body": bool(payload.get("include_response_body", current.include_response_body)),
        "external_sink_enabled": bool(payload.get("external_sink_enabled", current.external_sink_enabled)),
        "external_sink_type": str(payload.get("external_sink_type", current.external_sink_type) or "")[:60],
        "config_json": encode_json(payload.get("config") if isinstance(payload.get("config"), dict) else current.config_json),
    }
    with connect(database_target(), readonly=False) as conn:
        require_audit_logging_schema(conn)
        row = conn.execute(
            "SELECT id FROM audit_logging_settings WHERE tenant_id = ? AND deleted = 0",
            (tenant_id,),
        ).fetchone()
        if row:
            setting_id = int(row["id"])
            assignments = ", ".join(f"{key} = ?" for key in values)
            conn.execute(
                f"""
                UPDATE audit_logging_settings
                SET {assignments}, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                tuple([*values.values(), actor, actor_id, timestamp, setting_id, tenant_id]),
            )
        else:
            columns = (
                "tenant_id",
                *values.keys(),
                "creator",
                "creator_id",
                "editor",
                "editor_id",
                "create_time",
                "update_time",
            )
            conn.execute(
                f"INSERT INTO audit_logging_settings ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                tuple([tenant_id, *values.values(), actor, actor_id, actor, actor_id, timestamp, timestamp]),
            )
        saved = conn.execute(
            "SELECT * FROM audit_logging_settings WHERE tenant_id = ? AND deleted = 0",
            (tenant_id,),
        ).fetchone()
    return row_to_settings(dict(saved))


def prune_plaintext_ips() -> None:
    settings = get_effective_settings(0)
    cutoff = (datetime.now() - timedelta(days=settings.plaintext_ip_retention_days)).isoformat(timespec="seconds")
    with connect(database_target(), readonly=False) as conn:
        require_audit_logging_schema(conn)
        conn.execute(
            "UPDATE audit_visitor_logs SET client_ip = '', update_time = ? WHERE event_time < ? AND client_ip <> ''",
            (now_iso(), cutoff),
        )


def value_for_column(payload: dict[str, Any], column: str) -> Any:
    if column.endswith("_json"):
        source_key = column.removesuffix("_json")
        return encode_json(payload.get(column, payload.get(source_key, {} if column != "table_names_json" else [])))
    if column in {"creator", "editor"}:
        return str(payload.get(column) or "audit-worker")
    if column in {"creator_id", "editor_id"}:
        return payload.get(column)
    value = payload.get(column)
    if isinstance(value, bool):
        return int(value)
    if value is None:
        if column in {"actor_user_id", "owner_user_id", "owner_department_id", "target_owner_user_id", "target_owner_department_id", "row_count"}:
            return None
        if column in {"tenant_id", "duration_ms", "status_code", "request_size_bytes", "response_size_bytes"}:
            return 0
        if column == "success":
            return 1
        return ""
    return value


def row_to_log(category: str, row: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    data["category"] = category
    data["detail"] = decode_json(row.get("detail_json"))
    data.pop("detail_json", None)
    for key in ("before_json", "after_json", "diff_json", "query_summary_json", "table_names_json"):
        if key in data:
            value_key = key.removesuffix("_json")
            data[value_key] = decode_json(data.pop(key))
    data["success"] = bool(data.get("success")) if "success" in data else data.get("event_outcome") == "success"
    return data


def row_to_settings(row: dict[str, Any]) -> AuditLoggingSettings:
    return AuditLoggingSettings(
        id=int(row["id"]),
        tenant_id=int(row.get("tenant_id") or 0),
        api_log_enabled=bool(row.get("api_log_enabled")),
        operation_log_enabled=bool(row.get("operation_log_enabled")),
        sql_log_enabled=bool(row.get("sql_log_enabled")),
        visitor_log_enabled=bool(row.get("visitor_log_enabled")),
        system_log_enabled=bool(row.get("system_log_enabled")),
        slow_sql_threshold_ms=int(row.get("slow_sql_threshold_ms") or 500),
        queue_max_size=int(row.get("queue_max_size") or 10000),
        batch_size=int(row.get("batch_size") or 100),
        flush_interval_ms=int(row.get("flush_interval_ms") or 1000),
        plaintext_ip_retention_days=int(row.get("plaintext_ip_retention_days") or 30),
        log_retention_days=int(row.get("log_retention_days") or 180),
        include_request_headers=bool(row.get("include_request_headers")),
        include_response_body=bool(row.get("include_response_body")),
        external_sink_enabled=bool(row.get("external_sink_enabled")),
        external_sink_type=str(row.get("external_sink_type") or ""),
        config_json=decode_json(row.get("config_json")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def default_settings() -> AuditLoggingSettings:
    timestamp = now_iso()
    return AuditLoggingSettings(
        id=0,
        tenant_id=0,
        api_log_enabled=True,
        operation_log_enabled=True,
        sql_log_enabled=True,
        visitor_log_enabled=True,
        system_log_enabled=True,
        slow_sql_threshold_ms=500,
        queue_max_size=10000,
        batch_size=100,
        flush_interval_ms=1000,
        plaintext_ip_retention_days=30,
        log_retention_days=180,
        include_request_headers=False,
        include_response_body=False,
        external_sink_enabled=False,
        external_sink_type="",
        config_json={},
        create_time=timestamp,
        update_time=timestamp,
    )


def encode_json(payload: Any) -> str:
    return json.dumps(payload if payload is not None else {}, ensure_ascii=False, separators=(",", ":"))


def decode_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return {}
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return {}


def bounded_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = minimum
    return max(minimum, min(maximum, number))


def count_row(cursor: Any) -> int:
    row = cursor.fetchone()
    return int(row["total"] if row else 0)
