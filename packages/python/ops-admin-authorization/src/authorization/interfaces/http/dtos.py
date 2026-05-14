from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ResourceDescriptorRequest(BaseModel):
    resource_key: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    tenant_column: str = Field(default="tenant_id", max_length=120)
    creator_column: str = Field(default="creator_id", max_length=120)
    owner_user_column: str = Field(default="owner_user_id", max_length=120)
    owner_department_column: str = Field(default="owner_department_id", max_length=120)
    supported_scopes: list[str] = Field(default_factory=list)
    requires_data_scope: bool = False

    @field_validator("resource_key", "name", "description", "tenant_column", "creator_column", "owner_user_column", "owner_department_column")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class RoleDataScopeRequest(BaseModel):
    role_key: str = Field(min_length=1, max_length=120)
    resource_key: str = Field(min_length=1, max_length=160)
    action: str = Field(default="read", max_length=80)
    scope: str = Field(min_length=1, max_length=80)
    department_ids: list[int] = Field(default_factory=list)

    @field_validator("role_key", "resource_key", "action", "scope")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()
