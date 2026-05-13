from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROMPT_ASSET_STATUS_DRAFT = "draft"
PROMPT_ASSET_STATUS_REVIEWING = "reviewing"
PROMPT_ASSET_STATUS_PUBLISHED = "published"
PROMPT_ASSET_STATUS_ARCHIVED = "archived"
PROMPT_VERSION_STATUS_DRAFT = "draft"
PROMPT_VERSION_STATUS_PUBLISHED = "published"
PROMPT_VERSION_STATUS_DEPRECATED = "deprecated"
PROMPT_TASK_KIND_SINGLE_CALL = "single_call"
PROMPT_TASK_KIND_WORKFLOW_STEP = "workflow_step"
PROMPT_TASK_KIND_WORKFLOW = "workflow"
PROMPT_VISIBILITY_PRIVATE = "private"
PROMPT_VISIBILITY_TENANT = "tenant"
PROMPT_VISIBILITY_PLATFORM = "platform"
PROMPT_RUN_STATUS_SUCCEEDED = "succeeded"
PROMPT_RUN_STATUS_FAILED = "failed"


@dataclass(frozen=True)
class PromptAsset:
    id: int
    tenant_id: int
    prompt_key: str
    name: str
    description: str
    category: str
    tags: list[str]
    owner_context: str
    visibility: str
    status: str
    version_count: int
    binding_count: int
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "prompt_key": self.prompt_key,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "owner_context": self.owner_context,
            "visibility": self.visibility,
            "status": self.status,
            "version_count": self.version_count,
            "binding_count": self.binding_count,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class PromptVersion:
    id: int
    tenant_id: int
    prompt_id: int
    version: str
    system_prompt: str
    developer_prompt: str
    user_prompt_template: str
    variables_schema: dict[str, Any]
    output_schema: dict[str, Any]
    example_inputs: list[dict[str, Any]]
    example_outputs: list[dict[str, Any]]
    model_preferences: dict[str, Any]
    render_engine: str
    status: str
    published_time: str | None
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "prompt_id": self.prompt_id,
            "version": self.version,
            "system_prompt": self.system_prompt,
            "developer_prompt": self.developer_prompt,
            "user_prompt_template": self.user_prompt_template,
            "variables_schema": self.variables_schema,
            "output_schema": self.output_schema,
            "example_inputs": self.example_inputs,
            "example_outputs": self.example_outputs,
            "model_preferences": self.model_preferences,
            "render_engine": self.render_engine,
            "status": self.status,
            "published_time": self.published_time,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class PromptTaskContract:
    id: int
    tenant_id: int
    contract_key: str
    owner_context: str
    task_kind: str
    display_name: str
    description: str
    llm_task_key: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_capabilities: list[str]
    allowed_prompt_scopes: dict[str, Any]
    enabled: bool
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "contract_key": self.contract_key,
            "owner_context": self.owner_context,
            "task_kind": self.task_kind,
            "display_name": self.display_name,
            "description": self.description,
            "llm_task_key": self.llm_task_key,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "required_capabilities": self.required_capabilities,
            "allowed_prompt_scopes": self.allowed_prompt_scopes,
            "enabled": self.enabled,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class PromptBinding:
    id: int
    tenant_id: int
    contract_id: int
    contract_key: str
    prompt_id: int
    prompt_key: str
    prompt_name: str
    prompt_version_id: int
    prompt_version: str
    binding_name: str
    priority: int
    environment: str
    enabled: bool
    effective_from: str | None
    effective_to: str | None
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "contract_id": self.contract_id,
            "contract_key": self.contract_key,
            "prompt_id": self.prompt_id,
            "prompt_key": self.prompt_key,
            "prompt_name": self.prompt_name,
            "prompt_version_id": self.prompt_version_id,
            "prompt_version": self.prompt_version,
            "binding_name": self.binding_name,
            "priority": self.priority,
            "environment": self.environment,
            "enabled": self.enabled,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class PromptRun:
    id: int
    tenant_id: int
    contract_key: str
    prompt_id: int | None
    prompt_version_id: int | None
    llm_task_key: str
    input: dict[str, Any]
    rendered_messages: list[dict[str, str]]
    output_text: str
    output_json: dict[str, Any] | None
    schema_valid: bool
    validation_errors: list[str]
    status: str
    elapsed_ms: int
    request_id: str
    correlation_id: str
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "contract_key": self.contract_key,
            "prompt_id": self.prompt_id,
            "prompt_version_id": self.prompt_version_id,
            "llm_task_key": self.llm_task_key,
            "input": self.input,
            "rendered_messages": self.rendered_messages,
            "output_text": self.output_text,
            "output_json": self.output_json,
            "schema_valid": self.schema_valid,
            "validation_errors": self.validation_errors,
            "status": self.status,
            "elapsed_ms": self.elapsed_ms,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
