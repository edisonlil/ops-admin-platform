from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIApplicationRequest(BaseModel):
    app_key: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    app_type: str = Field(default="single_turn_generation", max_length=80)
    status: str = Field(default="draft", max_length=40)
    endpoint_slug: str = Field(default="", max_length=160)
    system_prompt: str = Field(default="", max_length=20000)
    developer_prompt: str = Field(default="", max_length=20000)
    user_prompt_template: str = Field(default="", max_length=20000)
    variables_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    model_preferences: dict[str, Any] = Field(default_factory=dict)
    auth_policy: dict[str, Any] = Field(default_factory=dict)
    quota_policy: dict[str, Any] = Field(default_factory=dict)
    trace_policy: dict[str, Any] = Field(default_factory=dict)
    runtime_config: dict[str, Any] = Field(default_factory=dict)


class AIApplicationRunRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    variables: dict[str, Any] = Field(default_factory=dict)
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    response_format: dict[str, Any] | None = None
    extra_body: dict[str, Any] | None = None
    enable_think_output: bool | None = None


class AIAgentConversationRequest(BaseModel):
    title: str = Field(default="", max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIAgentMessageRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    content: str = Field(min_length=1, max_length=20000)
    variables: dict[str, Any] = Field(default_factory=dict)
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    response_format: dict[str, Any] | None = None
    extra_body: dict[str, Any] | None = None
    enable_think_output: bool | None = None


class TenantAIQuotaRequest(BaseModel):
    max_applications: int = Field(default=5, ge=0)
    max_capabilities: int = Field(default=50, ge=0)
    max_assets: int = Field(default=200, ge=0)
    daily_run_limit: int = Field(default=1000, ge=0)
    monthly_token_limit: int = Field(default=1000000, ge=0)
    enabled: bool = True
