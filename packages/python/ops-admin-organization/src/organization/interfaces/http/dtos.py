from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DepartmentRequest(BaseModel):
    tenant_id: int | None = Field(default=None, ge=1)
    parent_id: int | None = Field(default=None, ge=1)
    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    manager_user_id: int | None = Field(default=None, ge=1)
    base_location: str = Field(default="", max_length=120)
    region: str = Field(default="", max_length=120)
    status: str = Field(default="active", max_length=40)
    sort_order: int = Field(default=0, ge=0, le=99999)

    @field_validator("code", "name", "base_location", "region", "status")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("status")
    @classmethod
    def status_must_be_known(cls, value: str) -> str:
        normalized = value.strip() or "active"
        if normalized not in {"active", "disabled"}:
            raise ValueError("status must be active or disabled")
        return normalized


class UserDepartmentsRequest(BaseModel):
    department_ids: list[int] = Field(default_factory=list)
    primary_department_id: int | None = Field(default=None, ge=1)
