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
SKILL_ASSET_STATUS_DRAFT = "draft"
SKILL_ASSET_STATUS_PUBLISHED = "published"
SKILL_ASSET_STATUS_ARCHIVED = "archived"
SKILL_VERSION_STATUS_DRAFT = "draft"
SKILL_VERSION_STATUS_PUBLISHED = "published"
SKILL_VERSION_STATUS_DEPRECATED = "deprecated"


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


@dataclass(frozen=True)
class SkillAsset:
    id: int
    tenant_id: int
    skill_key: str
    name: str
    description: str
    tags: list[str]
    status: str
    source_type: str
    version_count: int
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "skill_key": self.skill_key,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "status": self.status,
            "source_type": self.source_type,
            "version_count": self.version_count,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


@dataclass(frozen=True)
class SkillVersion:
    id: int
    tenant_id: int
    skill_id: int
    version: str
    manifest: dict[str, Any]
    content: str
    content_sha256: str
    entrypoint: str
    runtime_constraints: dict[str, Any]
    package_sha256: str
    package_size: int
    package_data_base64: str
    package_files: list[dict[str, Any]]
    validation_report: dict[str, Any]
    status: str
    published_time: str | None
    create_time: str
    update_time: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "manifest": self.manifest,
            "content": self.content,
            "content_sha256": self.content_sha256,
            "entrypoint": self.entrypoint,
            "runtime_constraints": self.runtime_constraints,
            "package_sha256": self.package_sha256,
            "package_size": self.package_size,
            "package_files": self.package_files,
            "validation_report": self.validation_report,
            "status": self.status,
            "published_time": self.published_time,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
