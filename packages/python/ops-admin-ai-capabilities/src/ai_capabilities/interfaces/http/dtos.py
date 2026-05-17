from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AICapabilityRequest(BaseModel):
    capability_key: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    scope: str = Field(default="tenant", max_length=40)
    binding_type: str = Field(default="prompt_runtime", max_length=80)
    binding_key: str = Field(default="", max_length=160)
    call_method: str = Field(default="aiService.execute", max_length=200)
    system_prompt: str = Field(default="", max_length=20000)
    developer_prompt: str = Field(default="", max_length=20000)
    user_prompt_template: str = Field(default="", max_length=20000)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    model_preferences: dict[str, Any] = Field(default_factory=dict)
    runtime_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class AICapabilityRunRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    variables: dict[str, Any] = Field(default_factory=dict)
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    response_format: dict[str, Any] | None = None
    extra_body: dict[str, Any] | None = None
    enable_think_output: bool | None = None


class PlatformAICapabilityPreviewRequest(AICapabilityRunRequest):
    tenant_id: int = Field(ge=1)
