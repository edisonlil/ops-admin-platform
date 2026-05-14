from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptAssetRequest(BaseModel):
    prompt_key: str = Field(default="", max_length=200)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    tags: list[str] = Field(default_factory=list)
    status: str = Field(default="draft", max_length=40)


class PromptVersionRequest(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    system_prompt: str = ""
    developer_prompt: str = ""
    user_prompt_template: str = ""
    variables_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    example_inputs: list[dict[str, Any]] = Field(default_factory=list)
    example_outputs: list[dict[str, Any]] = Field(default_factory=list)
    model_preferences: dict[str, Any] = Field(default_factory=dict)
    render_engine: str = Field(default="simple", max_length=40)
    status: str = Field(default="draft", max_length=40)


class PromptContractRequest(BaseModel):
    contract_key: str = Field(min_length=1, max_length=200)
    owner_context: str = Field(default="general", max_length=120)
    task_kind: str = Field(default="single_call", max_length=60)
    display_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)
    llm_task_key: str = Field(default="", max_length=200)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)
    allowed_prompt_scopes: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PromptBindingRequest(BaseModel):
    contract_id: int = Field(gt=0)
    prompt_id: int = Field(gt=0)
    prompt_version_id: int = Field(gt=0)
    binding_name: str = Field(default="", max_length=160)
    priority: int = Field(default=100, ge=1)
    environment: str = Field(default="dev", max_length=40)
    enabled: bool = True
    effective_from: str | None = None
    effective_to: str | None = None


class PromptTestRequest(BaseModel):
    contract_key: str = Field(min_length=1, max_length=200)
    prompt_version_id: int | None = None
    environment: str = Field(default="prod", max_length=40)
    variables: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
