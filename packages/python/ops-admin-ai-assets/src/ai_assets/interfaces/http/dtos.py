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


class PromptPolishRequest(BaseModel):
    title: str = Field(default="", max_length=200)
    prompt: str = Field(min_length=1, max_length=20000)
