from __future__ import annotations

from fastapi_login.exceptions import InvalidCredentialsException

from identity_access.application.api_key_service import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
    validate_api_key,
)
from identity_access.application.auth_service import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    authenticate_user,
    clear_login_cookie,
    create_access_token,
    public_user,
    set_login_cookie,
    user_by_username,
)
from identity_access.infrastructure.persistence.repositories import DisabledUserException
from identity_access.application.rbac_service import (
    create_menu,
    create_role,
    create_user,
    delete_menu,
    delete_role,
    list_menus,
    list_permissions,
    list_roles,
    list_users,
    update_menu,
    update_role,
    update_role_menus,
    update_user,
)
from identity_access.infrastructure.security import COOKIE_NAME, login_manager
from identity_access.interfaces.http.dependencies import (
    require_auth,
    require_permission,
    require_user,
)
