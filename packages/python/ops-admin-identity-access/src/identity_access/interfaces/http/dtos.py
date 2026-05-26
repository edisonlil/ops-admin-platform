from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


def normalize_email_value(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        return ""
    if any(char.isspace() for char in normalized):
        raise ValueError("Email must not contain whitespace")
    if normalized.count("@") != 1:
        raise ValueError("Email format is invalid")
    local_part, domain = normalized.split("@", 1)
    if not local_part or not domain or "." not in domain:
        raise ValueError("Email format is invalid")
    return normalized


class RbacUserListResponse(BaseModel):
    items: list[dict[str, Any]]


class RbacUserCreateRequest(BaseModel):
    tenant_id: int | None = Field(default=None, ge=1)
    username: str = Field(min_length=1, max_length=120)
    full_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=254)
    password: str = Field(min_length=1, max_length=200)
    role_keys: list[str] = Field(default_factory=list)
    department_ids: list[int] | None = None
    primary_department_id: int | None = Field(default=None, ge=1)
    manager_user_id: int | None = Field(default=None, ge=1)
    is_active: bool = True
    is_superuser: bool = False

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username must not be blank")
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_value(value)

    @field_validator("password")
    @classmethod
    def password_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Password must not be blank")
        return value


class RbacUserUpdateRequest(BaseModel):
    tenant_id: int | None = Field(default=None, ge=1)
    username: str = Field(min_length=1, max_length=120)
    full_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=254)
    password: str = Field(default="", max_length=200)
    role_keys: list[str] = Field(default_factory=list)
    department_ids: list[int] | None = None
    primary_department_id: int | None = Field(default=None, ge=1)
    manager_user_id: int | None = Field(default=None, ge=1)
    is_active: bool = True
    is_superuser: bool = False

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username must not be blank")
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_value(value)


class CurrentProfileUpdateRequest(BaseModel):
    full_name: str = Field(default="", max_length=120)
    email: str | None = Field(default=None, max_length=254)
    current_password: str = Field(default="", max_length=200)
    new_password: str = Field(default="", max_length=200)

    @field_validator("full_name", "current_password", "new_password")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_email_value(value)


class RbacRoleListResponse(BaseModel):
    items: list[dict[str, Any]]


class RbacRoleCreateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    role_scope: str = Field(default="platform", max_length=20)
    menu_keys: list[str] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def key_must_be_valid(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role key must not be blank")
        if not all(char.isascii() and (char.isalnum() or char in "-_") for char in value):
            raise ValueError("Role key may only contain ASCII letters, numbers, hyphens, and underscores")
        return value

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role name must not be blank")
        return value

    @field_validator("role_scope")
    @classmethod
    def role_scope_must_be_known(cls, value: str) -> str:
        value = value.strip() or "platform"
        if value not in {"platform", "tenant"}:
            raise ValueError("Role scope must be platform or tenant")
        return value


class RbacRoleUpdateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    menu_keys: list[str] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def key_must_be_valid(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role key must not be blank")
        if not all(char.isascii() and (char.isalnum() or char in "-_") for char in value):
            raise ValueError("Role key may only contain ASCII letters, numbers, hyphens, and underscores")
        return value

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role name must not be blank")
        return value


class RbacMenuCreateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=120)
    menu_scope: str = Field(default="platform", max_length=20)
    menu_type: str = Field(min_length=1, max_length=20)
    path: str = Field(default="", max_length=240)
    route_name: str = Field(default="", max_length=120)
    component: str = Field(default="", max_length=240)
    icon: str = Field(default="", max_length=120)
    parent_key: str = Field(default="", max_length=120)
    permission_code: str = Field(default="", max_length=120)
    sort_order: int = Field(default=0, ge=0, le=9999)
    is_visible: bool = True

    @field_validator("key", "route_name", "parent_key", "permission_code")
    @classmethod
    def normalize_key_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("label", "path", "component", "icon")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("menu_type")
    @classmethod
    def validate_menu_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"directory", "page", "action"}:
            raise ValueError("menu_type must be directory, page or action")
        return normalized

    @field_validator("menu_scope")
    @classmethod
    def validate_menu_scope(cls, value: str) -> str:
        normalized = value.strip().lower() or "platform"
        if normalized not in {"platform", "tenant"}:
            raise ValueError("menu_scope must be platform or tenant")
        return normalized


class RbacMenuUpdateRequest(RbacMenuCreateRequest):
    pass


class RbacPermissionListResponse(BaseModel):
    items: list[dict[str, Any]]


class RbacMenuListResponse(BaseModel):
    items: list[dict[str, Any]]


class RbacRoleMenusUpdateRequest(BaseModel):
    menu_keys: list[str] = Field(default_factory=list)


class RbacMenuTenantAssignmentsUpdateRequest(BaseModel):
    tenant_ids: list[int] = Field(default_factory=list)


class RbacTenantMenuAssignmentsUpdateRequest(BaseModel):
    menu_keys: list[str] = Field(default_factory=list)


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value


class ApiKeyUpdateRequest(ApiKeyCreateRequest):
    pass


class TenantCreateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    remark: str = Field(default="", max_length=500)
    status: str = Field(default="active", max_length=20)
    admin_username: str = Field(default="", max_length=120)
    admin_password: str = Field(default="", max_length=200)

    @field_validator("key")
    @classmethod
    def tenant_key_must_be_valid(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tenant key must not be blank")
        if not all(char.isascii() and (char.isalnum() or char in "-_") for char in value):
            raise ValueError("Tenant key may only contain ASCII letters, numbers, hyphens, and underscores")
        return value

    @field_validator("name", "remark", "status", "admin_username", "admin_password")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class TenantUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    remark: str = Field(default="", max_length=500)
    status: str = Field(default="active", max_length=20)

    @field_validator("name", "remark", "status")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class TenantSwitchRequest(BaseModel):
    tenant_id: int = Field(ge=1)


class TenantUserCreateRequest(RbacUserCreateRequest):
    is_tenant_admin: bool = False


class TenantUserUpdateRequest(RbacUserUpdateRequest):
    is_tenant_admin: bool = False
