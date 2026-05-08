from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMConfigRequest(BaseModel):
    provider: str = Field(default="minimax", min_length=1)
    model: str = Field(default="", max_length=200)
    base_url: str = Field(default="", max_length=500)
    api_key: str = Field(default="", max_length=4000)
    clear_api_key: bool = False
    command: str = Field(default="", max_length=4000)
    timeout_seconds: float = Field(default=120, gt=0, le=600)
    temperature: float = Field(default=0.1, ge=0, le=2)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    enable_think_output: bool = False
    enabled: bool = True

    @field_validator("provider")
    @classmethod
    def provider_must_not_be_blank(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Provider must not be blank")
        return value


class LLMProviderRequest(BaseModel):
    provider_key: str = Field(min_length=1, max_length=100)
    display_name: str = Field(default="", max_length=200)
    base_url: str = Field(default="", max_length=500)
    api_key: str = Field(default="", max_length=4000)
    clear_api_key: bool = False
    auth_type: str = Field(default="bearer", max_length=50)
    extra_headers: dict[str, Any] = Field(default_factory=dict)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True

    @field_validator("provider_key")
    @classmethod
    def provider_key_must_be_normalized(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("provider_key must not be blank")
        return value


class LLMModelRequest(BaseModel):
    model_key: str = Field(min_length=1, max_length=160)
    provider_key: str = Field(min_length=1, max_length=100)
    model_name: str = Field(min_length=1, max_length=200)
    display_name: str = Field(default="", max_length=200)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    context_window: int | None = Field(default=None, ge=1)
    enabled: bool = True


class LLMTaskRequest(BaseModel):
    task_key: str = Field(min_length=1, max_length=200)
    context_key: str = Field(default="", max_length=100)
    scene_key: str = Field(default="", max_length=100)
    task_name: str = Field(default="", max_length=100)
    display_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=1000)
    owner_context: str = Field(default="", max_length=100)
    enabled: bool = True


class LLMRoutingEntryRequest(BaseModel):
    model_key: str = Field(min_length=1, max_length=160)
    priority: int = Field(default=100, ge=1)
    temperature: float = Field(default=0.1, ge=0, le=2)
    timeout_seconds: float = Field(default=120, gt=0, le=600)
    max_retries: int = Field(default=0, ge=0, le=5)
    response_format: str = Field(default="text", max_length=20)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class LLMRoutingPolicyRequest(BaseModel):
    route_key: str = Field(min_length=1, max_length=200)
    display_name: str = Field(default="", max_length=200)
    strategy: str = Field(default="priority", max_length=50)
    enabled: bool = True
    entries: list[LLMRoutingEntryRequest] = Field(default_factory=list)


class OpenAIChatMessageRequest(BaseModel):
    role: str = Field(default="user", max_length=40)
    content: Any = ""


class OpenAIChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(min_length=1, max_length=200)
    messages: list[OpenAIChatMessageRequest] = Field(default_factory=list)
    temperature: float | None = Field(default=None, ge=0, le=2)
    response_format: dict[str, Any] | None = None
    enable_think_output: bool | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, ge=0, le=1)
    stream: bool = False
