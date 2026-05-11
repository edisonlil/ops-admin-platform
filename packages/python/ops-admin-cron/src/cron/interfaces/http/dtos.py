from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CronScheduleRequest(BaseModel):
    trigger_type: str = Field(default="cron", max_length=40)
    trigger_expression: str = Field(min_length=1, max_length=300)
    timezone: str = Field(default="UTC", max_length=80)
    start_time: str | None = Field(default=None, max_length=80)
    end_time: str | None = Field(default=None, max_length=80)
    next_fire_time: str | None = Field(default=None, max_length=80)


class CronTaskRequest(BaseModel):
    id: int | None = None
    task_key: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    status: str = Field(default="draft", max_length=40)
    execution_target: str = Field(min_length=1, max_length=200)
    payload_schema_version: int = Field(default=1, ge=1)
    default_payload: dict[str, Any] = Field(default_factory=dict)
    concurrency_policy: str = Field(default="forbid", max_length=40)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    max_attempts: int = Field(default=1, ge=1, le=100)
    retry_delay_seconds: int = Field(default=0, ge=0, le=86400)
    retry_backoff_multiplier: float = Field(default=1, ge=1, le=100)
    misfire_policy: str = Field(default="skip", max_length=40)
    schedule: CronScheduleRequest | None = None


class CronTriggerRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=200)
