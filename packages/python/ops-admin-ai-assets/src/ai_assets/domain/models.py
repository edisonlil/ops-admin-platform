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


@dataclass(frozen=True)
class PromptAsset:
    id: int
    tenant_id: int
    prompt_key: str
    name: str
    description: str
    tags: list[str]
    status: str
    version_count: int
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "prompt_key": self.prompt_key,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "status": self.status,
            "version_count": self.version_count,
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
