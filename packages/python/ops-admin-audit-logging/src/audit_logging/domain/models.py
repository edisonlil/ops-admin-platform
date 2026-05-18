from __future__ import annotations

from dataclasses import dataclass
from typing import Any


LOG_CATEGORY_SYSTEM = "system"
LOG_CATEGORY_OPERATION = "operation"
LOG_CATEGORY_API = "api"
LOG_CATEGORY_SQL = "sql"
LOG_CATEGORY_VISITOR = "visitor"
LOG_CATEGORIES = {
    LOG_CATEGORY_SYSTEM,
    LOG_CATEGORY_OPERATION,
    LOG_CATEGORY_API,
    LOG_CATEGORY_SQL,
    LOG_CATEGORY_VISITOR,
}


@dataclass(frozen=True)
class AuditLogRecord:
    id: int
    tenant_id: int
    event_time: str
    request_id: str
    event_action: str
    event_outcome: str
    severity: str
    source_module: str
    actor_user_id: int | None
    actor_name: str
    owner_user_id: int | None
    owner_department_id: int | None
    client_ip: str
    summary: str
    detail: dict[str, Any]
    create_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "event_time": self.event_time,
            "request_id": self.request_id,
            "event_action": self.event_action,
            "event_outcome": self.event_outcome,
            "severity": self.severity,
            "source_module": self.source_module,
            "actor_user_id": self.actor_user_id,
            "actor_name": self.actor_name,
            "owner_user_id": self.owner_user_id,
            "owner_department_id": self.owner_department_id,
            "client_ip": self.client_ip,
            "summary": self.summary,
            "detail": self.detail,
            "create_time": self.create_time,
        }


@dataclass(frozen=True)
class AuditLoggingSettings:
    id: int
    tenant_id: int
    api_log_enabled: bool
    operation_log_enabled: bool
    sql_log_enabled: bool
    visitor_log_enabled: bool
    system_log_enabled: bool
    slow_sql_threshold_ms: int
    queue_max_size: int
    batch_size: int
    flush_interval_ms: int
    plaintext_ip_retention_days: int
    log_retention_days: int
    include_request_headers: bool
    include_response_body: bool
    external_sink_enabled: bool
    external_sink_type: str
    config_json: dict[str, Any]
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "api_log_enabled": self.api_log_enabled,
            "operation_log_enabled": self.operation_log_enabled,
            "sql_log_enabled": self.sql_log_enabled,
            "visitor_log_enabled": self.visitor_log_enabled,
            "system_log_enabled": self.system_log_enabled,
            "slow_sql_threshold_ms": self.slow_sql_threshold_ms,
            "queue_max_size": self.queue_max_size,
            "batch_size": self.batch_size,
            "flush_interval_ms": self.flush_interval_ms,
            "plaintext_ip_retention_days": self.plaintext_ip_retention_days,
            "log_retention_days": self.log_retention_days,
            "include_request_headers": self.include_request_headers,
            "include_response_body": self.include_response_body,
            "external_sink_enabled": self.external_sink_enabled,
            "external_sink_type": self.external_sink_type,
            "config": self.config_json,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
