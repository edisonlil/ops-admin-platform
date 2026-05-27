from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from authorization.domain.models import ACCESS_MODE_OWNER_COLUMNS, ACCESS_MODE_RELATION_TABLE, VALID_ACCESS_MODES, VALID_DATA_SCOPES


class ResourceDescriptorRequest(BaseModel):
    resource_key: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    tenant_column: str = Field(default="tenant_id", max_length=120)
    resource_id_column: str = Field(default="id", max_length=120)
    creator_column: str = Field(default="creator_id", max_length=120)
    owner_user_column: str = Field(default="owner_user_id", max_length=120)
    owner_department_column: str = Field(default="owner_department_id", max_length=120)
    access_mode: str = Field(default=ACCESS_MODE_OWNER_COLUMNS, max_length=40)
    relation_table: str = Field(default="", max_length=160)
    relation_resource_id_column: str = Field(default="", max_length=120)
    relation_user_column: str = Field(default="", max_length=120)
    relation_department_column: str = Field(default="", max_length=120)
    relation_tenant_column: str = Field(default="tenant_id", max_length=120)
    relation_deleted_column: str = Field(default="deleted", max_length=120)
    relation_resource_key_column: str = Field(default="", max_length=120)
    relation_resource_key_value: str = Field(default="", max_length=160)
    relation_subject_type_column: str = Field(default="", max_length=120)
    relation_subject_type_user_value: str = Field(default="", max_length=80)
    relation_subject_type_department_value: str = Field(default="", max_length=80)
    supported_scopes: list[str] = Field(default_factory=list)
    requires_data_scope: bool = False

    @field_validator(
        "resource_key",
        "name",
        "description",
        "tenant_column",
        "resource_id_column",
        "creator_column",
        "owner_user_column",
        "owner_department_column",
        "access_mode",
        "relation_table",
        "relation_resource_id_column",
        "relation_user_column",
        "relation_department_column",
        "relation_tenant_column",
        "relation_deleted_column",
        "relation_resource_key_column",
        "relation_resource_key_value",
        "relation_subject_type_column",
        "relation_subject_type_user_value",
        "relation_subject_type_department_value",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_relation_table_config(self) -> "ResourceDescriptorRequest":
        if self.access_mode not in VALID_ACCESS_MODES:
            raise ValueError("归属模式必须是 owner_columns 或 relation_table")
        if self.access_mode != ACCESS_MODE_RELATION_TABLE:
            return self
        required: dict[str, Any] = {
            "relation_table": self.relation_table,
            "resource_id_column": self.resource_id_column,
            "relation_resource_id_column": self.relation_resource_id_column,
            "relation_tenant_column": self.relation_tenant_column,
        }
        effective_scopes = self.supported_scopes or list(VALID_DATA_SCOPES)
        if any(scope in effective_scopes for scope in ("self", "self_and_subordinates")):
            required["relation_user_column"] = self.relation_user_column
            if self.relation_subject_type_column:
                required["relation_subject_type_user_value"] = self.relation_subject_type_user_value
        if any(scope in effective_scopes for scope in ("department", "department_and_children", "custom_departments")):
            required["relation_department_column"] = self.relation_department_column
            if self.relation_subject_type_column:
                required["relation_subject_type_department_value"] = self.relation_subject_type_department_value
        missing = [name for name, value in required.items() if not str(value or "").strip()]
        if missing:
            raise ValueError("关系表归属模式缺少必要配置: " + ", ".join(missing))
        return self


class DataAccessPolicyRequest(BaseModel):
    tenant_id: int | None = Field(default=None, ge=1)
    subject_type: str = Field(min_length=1, max_length=40)
    subject_id: int = Field(ge=1)
    resource_key: str = Field(min_length=1, max_length=160)
    action: str = Field(default="read", max_length=80)
    scope: str = Field(min_length=1, max_length=80)
    department_ids: list[int] = Field(default_factory=list)
    priority: int = Field(default=100, ge=0, le=10000)

    @field_validator("subject_type", "resource_key", "action", "scope")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()
