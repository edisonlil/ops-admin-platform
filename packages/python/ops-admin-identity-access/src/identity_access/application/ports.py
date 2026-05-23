from __future__ import annotations

from typing import Any, Protocol


class IdentityAccessRepository(Protocol):
    DisabledUserException: type[Exception]

    def user_by_username(self, username: str, tenant_id: int | None = None) -> dict[str, Any] | None:
        ...

    def public_user(
        self,
        row: dict[str, Any],
        *,
        tenant_id: int | None = None,
        auth_scope: str | None = None,
        is_tenant_admin: bool = False,
    ) -> dict[str, Any]:
        ...

    def authenticate_user(self, username: str, password: str, tenant_id: int | None = None) -> dict[str, Any] | None:
        ...

    def authenticate_platform_admin(self, username: str, password: str) -> dict[str, Any] | None:
        ...

    def platform_user_by_username(self, username: str) -> dict[str, Any] | None:
        ...

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        ...

    def update_own_profile(
        self,
        user_id: int,
        *,
        full_name: str,
        email: str | None = None,
        current_password: str = "",
        new_password: str = "",
    ) -> dict[str, Any]:
        ...

    def create_api_key(
        self,
        *,
        name: str,
        creator: str,
        tenant_id: int | None = None,
        owner_user_id: int | None = None,
        owner_department_id: int | None = None,
    ) -> dict[str, Any]:
        ...

    def list_api_keys(
        self,
        *,
        tenant_id: int | None = None,
        data_scope: Any = None,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def get_api_key(self, key_id: int) -> dict[str, Any] | None:
        ...

    def update_api_key(
        self,
        key_id: int,
        *,
        name: str,
        editor: str = "",
        editor_id: int | None = None,
    ) -> dict[str, Any]:
        ...

    def revoke_api_key(self, key_id: int) -> dict[str, Any]:
        ...

    def validate_api_key(self, api_key: str) -> dict[str, Any] | None:
        ...

    def list_users(self) -> list[dict[str, Any]]:
        ...

    def list_platform_users(self) -> list[dict[str, Any]]:
        ...

    def create_user(
        self,
        *,
        username: str,
        password: str,
        full_name: str = "",
        email: str = "",
        tenant_id: int | None = None,
        role_keys: list[str] | None = None,
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> dict[str, Any]:
        ...

    def update_user(
        self,
        user_id: int,
        *,
        username: str,
        full_name: str = "",
        email: str = "",
        password: str = "",
        tenant_id: int | None = None,
        role_keys: list[str] | None = None,
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> dict[str, Any]:
        ...

    def set_user_active(self, user_id: int, is_active: bool) -> dict[str, Any]:
        ...

    def list_roles(self) -> list[dict[str, Any]]:
        ...

    def create_role(
        self,
        *,
        role_key: str,
        name: str,
        description: str = "",
        role_scope: str = "platform",
        menu_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        ...

    def update_role(
        self,
        role_id: int,
        *,
        role_key: str,
        name: str,
        description: str = "",
        menu_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        ...

    def update_role_menus(self, role_id: int, menu_keys: list[str]) -> dict[str, Any]:
        ...

    def delete_role(self, role_id: int) -> dict[str, Any]:
        ...

    def list_permissions(self) -> list[dict[str, str]]:
        ...

    def list_menus(self, menu_scope: str | None = None) -> list[dict[str, Any]]:
        ...

    def create_menu(
        self,
        *,
        menu_key: str,
        label: str,
        menu_type: str,
        menu_scope: str = "platform",
        path: str = "",
        route_name: str = "",
        component: str = "",
        icon: str = "",
        parent_key: str = "",
        permission_code: str = "",
        sort_order: int = 0,
        is_visible: bool = True,
    ) -> dict[str, Any]:
        ...

    def update_menu(
        self,
        menu_id: int,
        *,
        menu_key: str,
        label: str,
        menu_type: str,
        menu_scope: str = "platform",
        path: str = "",
        route_name: str = "",
        component: str = "",
        icon: str = "",
        parent_key: str = "",
        permission_code: str = "",
        sort_order: int = 0,
        is_visible: bool = True,
    ) -> dict[str, Any]:
        ...

    def delete_menu(self, menu_id: int) -> dict[str, Any]:
        ...


class IdentityAccessSecurityPort(Protocol):
    ACCESS_TOKEN_EXPIRE_SECONDS: int

    def create_access_token(
        self,
        username: str,
        *,
        tenant_id: int | None = None,
        auth_scope: str = "tenant",
        user_id: int | None = None,
    ) -> str:
        ...

    def set_login_cookie(self, response: Any, token: str) -> None:
        ...

    def clear_login_cookie(self, response: Any) -> None:
        ...
