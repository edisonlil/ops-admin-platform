from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuditLoggingSettingsRequest(BaseModel):
    api_log_enabled: bool = True
    operation_log_enabled: bool = True
    sql_log_enabled: bool = True
    visitor_log_enabled: bool = True
    system_log_enabled: bool = True
    slow_sql_threshold_ms: int = Field(default=500, ge=50, le=60000)
    queue_max_size: int = Field(default=10000, ge=1000, le=1000000)
    batch_size: int = Field(default=100, ge=1, le=10000)
    flush_interval_ms: int = Field(default=1000, ge=100, le=60000)
    plaintext_ip_retention_days: int = Field(default=30, ge=0, le=3650)
    log_retention_days: int = Field(default=180, ge=1, le=3650)
    include_request_headers: bool = False
    include_response_body: bool = False
    external_sink_enabled: bool = False
    external_sink_type: str = Field(default="", max_length=60)
    config: dict[str, Any] = Field(default_factory=dict)


class VisitorTrackRequest(BaseModel):
    path: str = Field(default="/", max_length=1000)
    title: str = Field(default="", max_length=200)
    referrer: str = Field(default="", max_length=1000)
    visitor_id: str = Field(default="", max_length=200)
    session_id: str = Field(default="", max_length=200)
    device_type: str = Field(default="", max_length=40)
    browser: str = Field(default="", max_length=80)
    os: str = Field(default="", max_length=80)
