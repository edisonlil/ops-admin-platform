from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from identity_access.infrastructure.config import (
    auth_database_target,
    default_admin_password,
    default_admin_username,
)
from identity_access.infrastructure.persistence.bootstrap import ensure_identity_schema, ensure_identity_seed
from identity_access.infrastructure.security import hash_password
from system.infrastructure.persistence.connection import connect


PLATFORM_TENANT_KEY = "platform"
DEFAULT_TENANT_KEY = "default"
DEFAULT_ROLE_KEY = "admin"

_auth_schema_lock = threading.Lock()


AUTH_INIT_COMMAND = "python scripts/init_identity_access.py"


class DisabledUserException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail="user is disabled")


DEFAULT_MENU_METADATA: dict[str, dict[str, str]] = {
    "messaging": {"menu_type": "directory", "component": "", "menu_scope": "tenant"},
    "message-inbox": {"menu_type": "page", "component": "/messaging/inbox/index", "menu_scope": "tenant"},
    "message-outbox": {"menu_type": "page", "component": "/messaging/outbox/index", "menu_scope": "tenant"},
    "message-send": {"menu_type": "page", "component": "/messaging/send/index", "menu_scope": "tenant"},
    "llm": {"menu_type": "directory", "component": "", "menu_scope": "tenant"},
    "llm-config": {"menu_type": "page", "component": "/settings/llm-config/index", "menu_scope": "tenant"},
    "llm-debug": {"menu_type": "page", "component": "/settings/llm-debug/index", "menu_scope": "tenant"},
    "tenant-settings": {"menu_type": "directory", "component": "", "menu_scope": "tenant"},
    "tenant-user-management": {"menu_type": "page", "component": "/tenant/index", "menu_scope": "tenant"},
    "tenant-api-keys": {"menu_type": "page", "component": "/settings/api-keys/index", "menu_scope": "tenant"},
    "platform-management": {"menu_type": "page", "component": "/platform/index", "menu_scope": "platform"},
    "tenant-management": {"menu_type": "page", "component": "/tenant/index", "menu_scope": "platform"},
    "appearance-studio": {"menu_type": "page", "component": "/settings/appearance-studio/index", "menu_scope": "platform"},
    "rbac": {"menu_type": "directory", "component": "", "menu_scope": "platform"},
    "menu-management": {"menu_type": "page", "component": "/rbac/menu/index", "menu_scope": "platform"},
    "role-management": {"menu_type": "page", "component": "/rbac/role/index", "menu_scope": "platform"},
}

TENANT_MESSAGING_MENU_KEYS = ["messaging", "message-inbox", "message-outbox", "message-send"]
TENANT_LLM_MENU_KEYS = ["llm", "llm-config", "llm-debug"]
TENANT_ADMIN_MENU_KEYS = (
    ["tenant-settings", "tenant-user-management", "tenant-api-keys"]
    + TENANT_MESSAGING_MENU_KEYS
    + TENANT_LLM_MENU_KEYS
)
TENANT_MEMBER_MENU_KEYS = ["tenant-settings"]
DEFAULT_TENANT_ENABLED_MENU_KEYS = TENANT_ADMIN_MENU_KEYS
TENANT_ADMIN_EXTRA_PERMISSION_CODES = [
    "llm_config:update",
    "messaging:inbox:view",
    "messaging:inbox:manage_self",
    "messaging:messages:view",
    "messaging:messages:send",
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def audit_insert_values(*, tenant_id: int = 1, actor: str | None = "system", actor_id: int | None = None) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "tenant_id": tenant_id,
        "lock_version": 0,
        "deleted": False,
        "create_time": timestamp,
        "creator": actor,
        "creator_id": actor_id,
        "update_time": timestamp,
        "editor": actor,
        "editor_id": actor_id,
    }


def audit_update_values(*, actor: str | None = "system", actor_id: int | None = None) -> dict[str, Any]:
    return {
        "update_time": now_iso(),
        "editor": actor,
        "editor_id": actor_id,
    }


def audit_insert_columns_sql() -> str:
    return "tenant_id, lock_version, deleted, create_time, creator, creator_id, update_time, editor, editor_id"


def audit_insert_placeholders_sql() -> str:
    return "?, ?, ?, ?, ?, ?, ?, ?, ?"


def audit_insert_params(*, tenant_id: int = 1, actor: str | None = "system", actor_id: int | None = None) -> tuple[Any, ...]:
    values = audit_insert_values(tenant_id=tenant_id, actor=actor, actor_id=actor_id)
    return (
        values["tenant_id"],
        values["lock_version"],
        values["deleted"],
        values["create_time"],
        values["creator"],
        values["creator_id"],
        values["update_time"],
        values["editor"],
        values["editor_id"],
    )


def audit_update_sql() -> str:
    return "update_time = ?, editor = ?, editor_id = ?, lock_version = lock_version + 1"


def audit_update_params(*, actor: str | None = "system", actor_id: int | None = None) -> tuple[Any, ...]:
    values = audit_update_values(actor=actor, actor_id=actor_id)
    return (values["update_time"], values["editor"], values["editor_id"])


def normalize_username(username: str) -> str:
    return username.strip()


def ensure_auth_schema(conn: Any) -> None:
    if getattr(conn, "backend", "sqlite") != "postgres":
        repair_sqlite_identity_tables_before_schema(conn)
    ensure_identity_schema(conn)
    ensure_menu_schema(conn)


def repair_sqlite_identity_tables_before_schema(conn: Any) -> None:
    migrate_sqlite_users_for_tenancy(conn)
    for table_name in (
        "tenants",
        "tenant_memberships",
        "users",
        "api_keys",
        "roles",
        "permissions",
        "menus",
        "user_roles",
        "role_permissions",
        "role_menus",
        "tenant_menu_overrides",
    ):
        columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if not columns:
            continue
        if "tenant_id" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN tenant_id INTEGER DEFAULT 1")
        if "lock_version" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN lock_version INTEGER NOT NULL DEFAULT 0")
        if "deleted" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")
        if "create_time" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN create_time TEXT")
            conn.execute(f"UPDATE {table_name} SET create_time = ? WHERE create_time IS NULL", (now_iso(),))
        if "creator" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN creator TEXT DEFAULT NULL")
        if "creator_id" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN creator_id INTEGER DEFAULT NULL")
        if "update_time" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN update_time TEXT")
            conn.execute(f"UPDATE {table_name} SET update_time = ? WHERE update_time IS NULL", (now_iso(),))
        if "editor" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN editor TEXT DEFAULT NULL")
        if "editor_id" not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN editor_id INTEGER DEFAULT NULL")


def ensure_menu_schema(conn: Any) -> None:
    now = now_iso()
    if getattr(conn, "backend", "sqlite") == "postgres":
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id BIGINT DEFAULT 1")
        conn.execute("ALTER TABLE roles ADD COLUMN IF NOT EXISTS tenant_id BIGINT DEFAULT NULL")
        conn.execute("ALTER TABLE roles ADD COLUMN IF NOT EXISTS role_scope TEXT DEFAULT 'platform'")
        conn.execute("ALTER TABLE menus ADD COLUMN IF NOT EXISTS menu_type TEXT DEFAULT 'page'")
        conn.execute("ALTER TABLE menus ADD COLUMN IF NOT EXISTS menu_scope TEXT DEFAULT 'tenant'")
        conn.execute("ALTER TABLE menus ADD COLUMN IF NOT EXISTS component TEXT DEFAULT ''")
        conn.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS tenant_id BIGINT DEFAULT 1")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tenant_menu_overrides (
                tenant_id BIGINT NOT NULL,
                menu_key TEXT NOT NULL,
                is_enabled BOOLEAN DEFAULT TRUE,
                create_time TEXT NOT NULL,
                update_time TEXT NOT NULL,
                PRIMARY KEY (tenant_id, menu_key)
            )
            """
        )
        conn.execute("UPDATE users SET tenant_id = 1 WHERE tenant_id IS NULL")
        conn.execute("UPDATE roles SET role_scope = 'platform' WHERE role_scope IS NULL OR role_scope = ''")
        conn.execute("UPDATE menus SET menu_scope = 'tenant' WHERE menu_scope IS NULL OR menu_scope = ''")
        conn.execute(
            """
            DO $$
            DECLARE
                constraint_name text;
            BEGIN
                SELECT c.conname INTO constraint_name
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE t.relname = 'users'
                  AND c.contype = 'u'
                  AND (
                      SELECT array_agg(a.attname ORDER BY a.attnum)
                      FROM unnest(c.conkey) AS key(attnum)
                      JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = key.attnum
                  ) = ARRAY['username'];

                IF constraint_name IS NOT NULL THEN
                    EXECUTE format('ALTER TABLE users DROP CONSTRAINT %I', constraint_name);
                END IF;
            END $$;
            """
        )
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_tenant_username_unique ON users(tenant_id, username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_tenant_username ON users(tenant_id, username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_scope ON roles(role_scope)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_menus_scope ON menus(menu_scope)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_menu_overrides_tenant ON tenant_menu_overrides(tenant_id)")
        conn.execute(
            """
            INSERT INTO tenants (id, tenant_key, name, status, remark, create_time, update_time)
            OVERRIDING SYSTEM VALUE
            SELECT 1, ?, ?, 'active', ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE tenant_key = ?)
              AND NOT EXISTS (SELECT 1 FROM tenants WHERE id = 1)
            """,
            (
                PLATFORM_TENANT_KEY,
                "Platform Administration",
                "System realm for platform administrators",
                now,
                now,
                PLATFORM_TENANT_KEY,
            ),
        )
        conn.execute(
            """
            INSERT INTO tenants (id, tenant_key, name, status, remark, create_time, update_time)
            OVERRIDING SYSTEM VALUE
            SELECT 2, ?, ?, 'active', ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE tenant_key = ?)
              AND NOT EXISTS (SELECT 1 FROM tenants WHERE id = 2)
            """,
            (
                DEFAULT_TENANT_KEY,
                "Default Tenant",
                "Migrated single-tenant workspace",
                now,
                now,
                DEFAULT_TENANT_KEY,
            ),
        )
        return

    migrate_sqlite_users_for_tenancy(conn)
    role_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(roles)").fetchall()
    }
    if "tenant_id" not in role_columns:
        conn.execute("ALTER TABLE roles ADD COLUMN tenant_id INTEGER DEFAULT NULL")
    if "role_scope" not in role_columns:
        conn.execute("ALTER TABLE roles ADD COLUMN role_scope TEXT DEFAULT 'platform'")
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(menus)").fetchall()
    }
    if "menu_type" not in columns:
        conn.execute("ALTER TABLE menus ADD COLUMN menu_type TEXT DEFAULT 'page'")
    if "menu_scope" not in columns:
        conn.execute("ALTER TABLE menus ADD COLUMN menu_scope TEXT DEFAULT 'tenant'")
    if "component" not in columns:
        conn.execute("ALTER TABLE menus ADD COLUMN component TEXT DEFAULT ''")
    api_key_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(api_keys)").fetchall()
    }
    if "tenant_id" not in api_key_columns:
        conn.execute("ALTER TABLE api_keys ADD COLUMN tenant_id INTEGER DEFAULT 1")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tenant_menu_overrides (
            tenant_id INTEGER NOT NULL,
            menu_key TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            create_time TEXT NOT NULL,
            update_time TEXT NOT NULL,
            PRIMARY KEY (tenant_id, menu_key)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_tenant_username_unique ON users(tenant_id, username)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_tenant_username ON users(tenant_id, username)")
    conn.execute("UPDATE roles SET role_scope = 'platform' WHERE role_scope IS NULL OR role_scope = ''")
    conn.execute("UPDATE menus SET menu_scope = 'tenant' WHERE menu_scope IS NULL OR menu_scope = ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_scope ON roles(role_scope)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_menus_scope ON menus(menu_scope)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_menu_overrides_tenant ON tenant_menu_overrides(tenant_id)")
    conn.execute(
        """
        INSERT INTO tenants (id, tenant_key, name, status, remark, create_time, update_time)
        SELECT 1, ?, ?, 'active', ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE tenant_key = ?)
          AND NOT EXISTS (SELECT 1 FROM tenants WHERE id = 1)
        """,
        (
            PLATFORM_TENANT_KEY,
            "Platform Administration",
            "System realm for platform administrators",
            now,
            now,
            PLATFORM_TENANT_KEY,
        ),
    )
    conn.execute(
        """
        INSERT INTO tenants (id, tenant_key, name, status, remark, create_time, update_time)
        SELECT 2, ?, ?, 'active', ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE tenant_key = ?)
          AND NOT EXISTS (SELECT 1 FROM tenants WHERE id = 2)
        """,
        (
            DEFAULT_TENANT_KEY,
            "Default Tenant",
            "Migrated single-tenant workspace",
            now,
            now,
            DEFAULT_TENANT_KEY,
        ),
    )


def migrate_sqlite_users_for_tenancy(conn: Any) -> None:
    user_columns = [dict(row) for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    if not user_columns:
        return
    column_names = {str(row["name"]) for row in user_columns}
    required_columns = {
        "tenant_id",
        "lock_version",
        "deleted",
        "create_time",
        "creator",
        "creator_id",
        "update_time",
        "editor",
        "editor_id",
    }
    missing_required_columns = bool(required_columns - column_names)
    index_rows = [dict(row) for row in conn.execute("PRAGMA index_list(users)").fetchall()]
    has_global_username_unique = False
    for index_row in index_rows:
        if not bool(index_row.get("unique")):
            continue
        index_columns = [
            str(row["name"])
            for row in conn.execute(f"PRAGMA index_info({str(index_row['name'])})").fetchall()
        ]
        if index_columns == ["username"]:
            has_global_username_unique = True
            break
    if not missing_required_columns and not has_global_username_unique:
        return

    conn.execute("DROP TABLE IF EXISTS users_tenant_migration")
    conn.execute(
        """
        CREATE TABLE users_tenant_migration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER DEFAULT 1,
            username TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            is_superuser INTEGER DEFAULT 0,
            lock_version INTEGER NOT NULL DEFAULT 0,
            deleted INTEGER NOT NULL DEFAULT 0,
            create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            creator TEXT DEFAULT NULL,
            creator_id INTEGER DEFAULT NULL,
            update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            editor TEXT DEFAULT NULL,
            editor_id INTEGER DEFAULT NULL,
            UNIQUE (tenant_id, username)
        )
        """
    )
    select_tenant = "tenant_id" if "tenant_id" in column_names else "1 AS tenant_id"
    select_lock_version = "lock_version" if "lock_version" in column_names else "0 AS lock_version"
    select_deleted = "deleted" if "deleted" in column_names else "0 AS deleted"
    select_creator = "creator" if "creator" in column_names else "NULL AS creator"
    select_creator_id = "creator_id" if "creator_id" in column_names else "NULL AS creator_id"
    select_editor = "editor" if "editor" in column_names else "NULL AS editor"
    select_editor_id = "editor_id" if "editor_id" in column_names else "NULL AS editor_id"
    conn.execute(
        f"""
        INSERT INTO users_tenant_migration (
            id, tenant_id, username, hashed_password, is_active, is_superuser,
            lock_version, deleted, create_time, creator, creator_id, update_time, editor, editor_id
        )
        SELECT id, {select_tenant}, username, hashed_password, is_active, is_superuser,
            {select_lock_version}, {select_deleted}, create_time, {select_creator}, {select_creator_id},
            update_time, {select_editor}, {select_editor_id}
        FROM users
        """
    )
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_tenant_migration RENAME TO users")


def ensure_platform_tenant(conn: Any) -> dict[str, Any]:
    now = now_iso()
    row = conn.execute("SELECT * FROM tenants WHERE tenant_key = ?", (PLATFORM_TENANT_KEY,)).fetchone()
    if not row:
        conn.execute(
            """
            INSERT INTO tenants (tenant_key, name, status, remark, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                PLATFORM_TENANT_KEY,
                "Platform Administration",
                "active",
                "System realm for platform administrators",
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM tenants WHERE tenant_key = ?", (PLATFORM_TENANT_KEY,)).fetchone()
    return dict(row)


def ensure_default_tenant(conn: Any) -> dict[str, Any]:
    now = now_iso()
    row = conn.execute("SELECT * FROM tenants WHERE tenant_key = ?", (DEFAULT_TENANT_KEY,)).fetchone()
    if not row:
        conn.execute(
            """
            INSERT INTO tenants (tenant_key, name, status, remark, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (DEFAULT_TENANT_KEY, "Default Tenant", "active", "Migrated single-tenant workspace", now, now),
        )
        row = conn.execute("SELECT * FROM tenants WHERE tenant_key = ?", (DEFAULT_TENANT_KEY,)).fetchone()
    return dict(row)


def ensure_default_admin(conn: Any) -> None:
    tenant = ensure_platform_tenant(conn)
    tenant_id = int(tenant["id"])
    username = default_admin_username()
    row = conn.execute(
        "SELECT id FROM users WHERE tenant_id = ? AND username = ?",
        (tenant_id, username),
    ).fetchone()
    now = now_iso()
    if row:
        conn.execute(
            """
            UPDATE users
            SET is_active = TRUE,
                is_superuser = TRUE,
                update_time = ?
            WHERE id = ?
            """,
            (now, int(row["id"])),
        )
        return

    legacy = conn.execute(
        """
        SELECT id
        FROM users
        WHERE username = ? AND is_superuser = TRUE
        ORDER BY id
        LIMIT 1
        """,
        (username,),
    ).fetchone()
    if legacy:
        conn.execute(
            """
            UPDATE users
            SET tenant_id = ?,
                is_active = TRUE,
                is_superuser = TRUE,
                update_time = ?
            WHERE id = ?
            """,
            (tenant_id, now, int(legacy["id"])),
        )
        conn.execute("DELETE FROM tenant_memberships WHERE user_id = ?", (int(legacy["id"]),))
        return

    conn.execute(
        """
        INSERT INTO users (tenant_id, username, hashed_password, is_active, is_superuser, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            username,
            hash_password(default_admin_password()),
            True,
            True,
            now,
            now,
        ),
    )


def ensure_tenant_menu_defaults(conn: Any, tenant_id: int) -> None:
    tenant = conn.execute("SELECT tenant_key FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    if not tenant or str(tenant["tenant_key"]) == PLATFORM_TENANT_KEY:
        return
    now = now_iso()
    for menu_key in DEFAULT_TENANT_ENABLED_MENU_KEYS:
        conn.execute(
            """
            INSERT INTO tenant_menu_overrides (tenant_id, menu_key, is_enabled, create_time, update_time)
            SELECT ?, ?, TRUE, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM tenant_menu_overrides WHERE tenant_id = ? AND menu_key = ?
            )
            """,
            (tenant_id, menu_key, now, now, tenant_id, menu_key),
        )


def ensure_all_tenant_menu_defaults(conn: Any) -> None:
    rows = conn.execute("SELECT id FROM tenants WHERE tenant_key <> ?", (PLATFORM_TENANT_KEY,)).fetchall()
    for row in rows:
        ensure_tenant_menu_defaults(conn, int(row["id"]))


def ensure_default_admin_membership(conn: Any) -> None:
    tenant = ensure_default_tenant(conn)
    platform_tenant = ensure_platform_tenant(conn)
    conn.execute("UPDATE api_keys SET tenant_id = ? WHERE tenant_id IS NULL", (int(tenant["id"]),))
    conn.execute(
        "UPDATE api_keys SET tenant_id = ? WHERE tenant_id = ?",
        (int(tenant["id"]), int(platform_tenant["id"])),
    )


def ensure_default_rbac(conn: Any) -> None:
    admin_role = conn.execute("SELECT id FROM roles WHERE role_key = ?", (DEFAULT_ROLE_KEY,)).fetchone()
    ensure_identity_seed(conn)
    ensure_platform_default_menus(conn)
    backfill_default_menu_metadata(conn)
    admin_role = conn.execute("SELECT id FROM roles WHERE role_key = ?", (DEFAULT_ROLE_KEY,)).fetchone()
    if not admin_role:
        return
    role_id = int(admin_role["id"])
    conn.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT id, ? FROM users
        WHERE is_superuser = ? AND NOT EXISTS (
            SELECT 1 FROM user_roles WHERE user_id = users.id AND role_id = ?
        )
        """,
        (role_id, True, role_id),
    )
    ensure_default_admin_membership(conn)
    ensure_tenant_default_menus(conn)
    ensure_tenant_default_roles(conn)
    repair_tenant_rbac_boundaries(conn)
    ensure_all_tenant_menu_defaults(conn)


def backfill_default_menu_metadata(conn: Any) -> None:
    retire_platform_menu_keys(conn, ["settings", "api-keys", "user-management"])
    default_tenant_scoped_platform_keys = {
        "rbac",
        "menu-management",
        "role-management",
        "platform-management",
        "tenant-management",
        "appearance-studio",
    }
    for menu_key, metadata in DEFAULT_MENU_METADATA.items():
        existing = conn.execute("SELECT id, menu_scope FROM menus WHERE menu_key = ?", (menu_key,)).fetchone()
        should_set_scope = existing is None or (
            metadata["menu_scope"] == "platform"
            and menu_key in default_tenant_scoped_platform_keys
            and str(existing["menu_scope"] or "") == "tenant"
        )
        conn.execute(
            """
            UPDATE menus
            SET menu_type = CASE
                    WHEN menu_type IS NULL OR menu_type = '' THEN ?
                    WHEN ? = 'directory'
                        AND menu_type = 'page'
                        AND EXISTS (SELECT 1 FROM menus child WHERE child.parent_key = menus.menu_key)
                    THEN 'directory'
                    ELSE menu_type
                END,
                component = CASE WHEN component IS NULL OR component = '' THEN ? ELSE component END,
                menu_scope = CASE WHEN ? THEN ? ELSE menu_scope END
            WHERE menu_key = ?
            """,
            (
                metadata["menu_type"],
                metadata["menu_type"],
                metadata["component"],
                should_set_scope,
                metadata["menu_scope"],
                menu_key,
            ),
        )
    conn.execute("UPDATE menus SET menu_scope = 'tenant' WHERE menu_key IN ('llm', 'llm-config', 'llm-debug')")
    conn.execute("UPDATE menus SET parent_key = '' WHERE menu_key = 'llm' AND menu_scope = 'tenant' AND parent_key IS NULL")
    conn.execute("UPDATE menus SET parent_key = 'llm' WHERE menu_key IN ('llm-config', 'llm-debug') AND (parent_key IS NULL OR parent_key = '')")
    label_rows = [
        ("llm", "大模型"),
        ("llm-config", "模型配置"),
        ("llm-debug", "模型调试"),
        ("tenant-settings", "租户设置"),
        ("tenant-user-management", "成员管理"),
        ("tenant-api-keys", "API 密钥"),
        ("tenant-management", "租户管理"),
        ("appearance-studio", "主题管理"),
        ("rbac", "权限管理"),
        ("menu-management", "菜单权限"),
        ("role-management", "角色权限"),
    ]
    for menu_key, label in label_rows:
        conn.execute("UPDATE menus SET label = ? WHERE menu_key = ? AND (label IS NULL OR label = '')", (label, menu_key))
    conn.execute(
        """
        UPDATE menus
        SET label = '平台管理',
            menu_type = 'page',
            path = '/platform',
            route_name = 'platform-management',
            component = '/platform/index',
            icon = 'SettingOutlined',
            parent_key = '',
            permission_code = '',
            sort_order = 109,
            is_visible = TRUE,
            menu_scope = 'platform'
        WHERE menu_key = 'platform-management'
        """
    )


def retire_platform_menu_keys(conn: Any, menu_keys: list[str]) -> None:
    placeholders = ", ".join("?" for _ in menu_keys)
    conn.execute(
        f"""
        DELETE FROM role_menus
        WHERE menu_id IN (
            SELECT id FROM menus
            WHERE menu_scope = 'platform'
              AND menu_key IN ({placeholders})
        )
        """,
        tuple(menu_keys),
    )
    conn.execute(
        f"""
        DELETE FROM menus
        WHERE menu_scope = 'platform'
          AND menu_key IN ({placeholders})
        """,
        tuple(menu_keys),
    )


def ensure_platform_default_menus(conn: Any) -> None:
    platform_menu_rows = [
        ("platform-management", "平台管理", "/platform", "platform-management", "SettingOutlined", "", "", 109),
        ("rbac", "权限管理", "", "", "shield", "", "", 100),
        ("menu-management", "菜单权限", "/rbac/menus", "menu-management", "menu", "rbac", "system:menu:access", 101),
        ("role-management", "角色权限", "/rbac/roles", "role-management", "users", "rbac", "system:role:access", 102),
        ("tenant-management", "租户管理", "/tenant", "tenant-management", "ApartmentOutlined", "", "tenant:access", 110),
        ("appearance-studio", "主题管理", "/settings/appearance-studio", "appearance-studio", "BgColorsOutlined", "", "appearance:access", 120),
    ]
    for key, label, path, route_name, icon, parent_key, permission_code, sort_order in platform_menu_rows:
        conn.execute(
            """
            INSERT INTO menus (
                menu_key, menu_scope, label, menu_type, path, route_name, component, icon,
                parent_key, permission_code, sort_order, is_visible
            )
            SELECT ?, 'platform', ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE
            WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = ?)
            """,
            (
                key,
                label,
                DEFAULT_MENU_METADATA[key]["menu_type"],
                path,
                route_name,
                DEFAULT_MENU_METADATA[key]["component"],
                icon,
                parent_key,
                permission_code,
                sort_order,
                key,
            ),
        )
    backfill_default_menu_metadata(conn)


def ensure_tenant_default_menus(conn: Any) -> None:
    tenant_menu_rows = [
        (
            "tenant-settings",
            "租户设置",
            "",
            "",
            "setting",
            "",
            "",
            80,
        ),
        (
            "tenant-user-management",
            "成员管理",
            "/tenant",
            "tenant-user-management",
            "user",
            "tenant-settings",
            "tenant:user:manage",
            81,
        ),
        (
            "tenant-api-keys",
            "API 密钥",
            "/settings/api-keys",
            "tenant-api-keys",
            "key",
            "tenant-settings",
            "tenant:api_key:manage",
            82,
        ),
        (
            "llm",
            "大模型",
            "",
            "",
            "experiment",
            "",
            "",
            90,
        ),
        (
            "messaging",
            "消息系统",
            "",
            "",
            "message",
            "",
            "",
            85,
        ),
        (
            "message-inbox",
            "站内信",
            "/messaging/inbox",
            "message-inbox",
            "inbox",
            "messaging",
            "messaging:inbox:view",
            86,
        ),
        (
            "message-outbox",
            "发送记录",
            "/messaging/outbox",
            "message-outbox",
            "send",
            "messaging",
            "messaging:messages:view",
            87,
        ),
        (
            "message-send",
            "发送消息",
            "/messaging/send",
            "message-send",
            "edit",
            "messaging",
            "messaging:messages:send",
            88,
        ),
        (
            "llm-config",
            "模型配置",
            "/settings/llm-config",
            "llm-config",
            "settings",
            "llm",
            "llm_config:access",
            91,
        ),
        (
            "llm-debug",
            "模型调试",
            "/settings/llm-debug",
            "llm-debug",
            "experiment",
            "llm",
            "llm_debug:access",
            92,
        ),
    ]
    for key, label, path, route_name, icon, parent_key, permission_code, sort_order in tenant_menu_rows:
        conn.execute(
            """
            INSERT INTO menus (
                menu_key, menu_scope, label, menu_type, path, route_name, component, icon,
                parent_key, permission_code, sort_order, is_visible
            )
            SELECT ?, 'tenant', ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE
            WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = ?)
            """,
            (
                key,
                label,
                DEFAULT_MENU_METADATA[key]["menu_type"],
                path,
                route_name,
                DEFAULT_MENU_METADATA[key]["component"],
                icon,
                parent_key,
                permission_code,
                sort_order,
                key,
            ),
        )


def repair_tenant_rbac_boundaries(conn: Any) -> None:
    conn.execute(
        """
        DELETE FROM tenant_memberships
        WHERE user_id IN (SELECT id FROM users WHERE is_superuser = TRUE)
        """
    )
    conn.execute(
        """
        DELETE FROM user_roles
        WHERE role_id IN (SELECT id FROM roles WHERE role_scope = 'tenant')
          AND user_id IN (
              SELECT u.id
              FROM users u
              JOIN tenants t ON t.id = u.tenant_id
              WHERE t.tenant_key = ?
          )
        """,
        (PLATFORM_TENANT_KEY,),
    )
    platform_role_rows = conn.execute("SELECT id FROM roles WHERE role_scope = 'platform'").fetchall()
    platform_role_ids = [int(row["id"]) for row in platform_role_rows]
    if platform_role_ids:
        placeholders = ",".join(["?"] * len(platform_role_ids))
        conn.execute(
            f"""
            DELETE FROM user_roles
            WHERE role_id IN ({placeholders})
              AND user_id IN (
                  SELECT u.id
                  FROM users u
                  JOIN tenants t ON t.id = u.tenant_id
                  WHERE t.tenant_key <> ?
              )
            """,
            (*platform_role_ids, PLATFORM_TENANT_KEY),
        )

    tenant_admin_role = conn.execute("SELECT id FROM roles WHERE role_key = ?", ("tenant-admin",)).fetchone()
    tenant_member_role = conn.execute("SELECT id FROM roles WHERE role_key = ?", ("tenant-member",)).fetchone()
    if tenant_admin_role:
        conn.execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT tm.user_id, ?
            FROM tenant_memberships tm
            JOIN users u ON u.id = tm.user_id
            WHERE tm.is_tenant_admin = TRUE
              AND u.is_superuser = FALSE
              AND NOT EXISTS (
                  SELECT 1 FROM user_roles ur
                  WHERE ur.user_id = tm.user_id AND ur.role_id = ?
              )
            """,
            (int(tenant_admin_role["id"]), int(tenant_admin_role["id"])),
        )
    if tenant_member_role:
        conn.execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT tm.user_id, ?
            FROM tenant_memberships tm
            JOIN users u ON u.id = tm.user_id
            WHERE tm.is_tenant_admin = FALSE
              AND u.is_superuser = FALSE
              AND NOT EXISTS (
                  SELECT 1 FROM user_roles ur
                  WHERE ur.user_id = tm.user_id AND ur.role_id = ?
              )
            """,
            (int(tenant_member_role["id"]), int(tenant_member_role["id"])),
        )


def ensure_role_access_by_key(conn: Any, role_key: str, menu_keys: list[str]) -> None:
    role_row = conn.execute("SELECT id, role_scope FROM roles WHERE role_key = ?", (role_key,)).fetchone()
    if not role_row:
        return
    role_id = int(role_row["id"])
    role_scope = str(role_row["role_scope"] or "platform")
    conn.execute("DELETE FROM role_menus WHERE role_id = ?", (role_id,))
    conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
    for menu_key in menu_keys:
        menu_row = conn.execute(
            "SELECT id, permission_code FROM menus WHERE menu_key = ? AND menu_scope = ?",
            (menu_key, role_scope),
        ).fetchone()
        if not menu_row:
            continue
        conn.execute(
            """
            INSERT INTO role_menus (role_id, menu_id)
            VALUES (?, ?)
            """,
            (role_id, int(menu_row["id"])),
        )
        permission_code = str(menu_row["permission_code"] or "").strip()
        if not permission_code:
            continue
        permission_row = conn.execute("SELECT id FROM permissions WHERE code = ?", (permission_code,)).fetchone()
        if permission_row:
            conn.execute(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
                """,
                (role_id, int(permission_row["id"])),
            )


def ensure_role_menus_by_key(conn: Any, role_key: str, menu_keys: list[str]) -> None:
    role_row = conn.execute("SELECT id, role_scope FROM roles WHERE role_key = ?", (role_key,)).fetchone()
    if not role_row:
        return
    role_id = int(role_row["id"])
    role_scope = str(role_row["role_scope"] or "platform")
    for menu_key in menu_keys:
        menu_row = conn.execute(
            "SELECT id, permission_code FROM menus WHERE menu_key = ? AND menu_scope = ?",
            (str(menu_key).strip(), role_scope),
        ).fetchone()
        if not menu_row:
            continue
        menu_id = int(menu_row["id"])
        conn.execute(
            """
            INSERT INTO role_menus (role_id, menu_id)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM role_menus WHERE role_id = ? AND menu_id = ?
            )
            """,
            (role_id, menu_id, role_id, menu_id),
        )
        permission_code = str(menu_row["permission_code"] or "").strip()
        if permission_code:
            ensure_role_permissions_by_code(conn, role_key, [permission_code])


def ensure_role_permissions_by_code(conn: Any, role_key: str, permission_codes: list[str]) -> None:
    role_row = conn.execute("SELECT id FROM roles WHERE role_key = ?", (role_key,)).fetchone()
    if not role_row:
        return
    role_id = int(role_row["id"])
    for permission_code in permission_codes:
        normalized = str(permission_code).strip()
        if not normalized:
            continue
        permission_row = conn.execute("SELECT id FROM permissions WHERE code = ?", (normalized,)).fetchone()
        if not permission_row:
            continue
        permission_id = int(permission_row["id"])
        conn.execute(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM role_permissions WHERE role_id = ? AND permission_id = ?
            )
            """,
            (role_id, permission_id, role_id, permission_id),
        )


def ensure_tenant_default_roles(conn: Any) -> None:
    now = now_iso()
    role_rows = [
        ("tenant-admin", "Tenant Administrator", "Manage current tenant members and API keys", TENANT_ADMIN_MENU_KEYS),
        ("tenant-member", "Tenant Member", "Use tenant business features", TENANT_MEMBER_MENU_KEYS),
    ]
    for role_key, name, description, menu_keys in role_rows:
        existing_role = conn.execute("SELECT id FROM roles WHERE role_key = ?", (role_key,)).fetchone()
        is_new_role = existing_role is None
        conn.execute(
            """
            INSERT INTO roles (role_key, name, description, is_system, role_scope, create_time, update_time)
            SELECT ?, ?, ?, TRUE, 'tenant', ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_key = ?)
            """,
            (role_key, name, description, now, now, role_key),
        )
        conn.execute(
            """
            UPDATE roles
            SET role_scope = 'tenant'
            WHERE role_key = ?
            """,
            (role_key,),
        )
        if is_new_role:
            ensure_role_access_by_key(conn, role_key, menu_keys)
        if role_key == "tenant-admin":
            ensure_role_menus_by_key(conn, role_key, TENANT_LLM_MENU_KEYS)
            ensure_role_permissions_by_code(conn, role_key, TENANT_ADMIN_EXTRA_PERMISSION_CODES)

    admin_role = conn.execute("SELECT id FROM roles WHERE role_key = ?", (DEFAULT_ROLE_KEY,)).fetchone()
    has_platform_user = False
    if admin_role:
        has_platform_user = bool(
            conn.execute(
                """
                SELECT 1
                FROM user_roles ur
                JOIN users u ON u.id = ur.user_id
                JOIN tenants t ON t.id = u.tenant_id
                WHERE ur.role_id = ?
                  AND t.tenant_key = ?
                LIMIT 1
                """,
                (int(admin_role["id"]), PLATFORM_TENANT_KEY),
            ).fetchone()
        )
    if admin_role:
        role_id = int(admin_role["id"])
        conn.execute(
            """
            UPDATE roles
            SET role_scope = 'platform'
            WHERE id = ?
            """,
            (role_id,),
        )
        if not has_platform_user:
            conn.execute("DELETE FROM role_menus WHERE role_id = ?", (role_id,))
            conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
            conn.execute(
                """
                INSERT INTO role_menus (role_id, menu_id)
                SELECT ?, id FROM menus WHERE menu_scope = 'platform'
                """,
                (role_id,),
            )
            conn.execute(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT ?, id FROM permissions
                """,
                (role_id,),
            )


def initialize_auth_storage(conn: Any) -> None:
    if getattr(conn, "backend", "sqlite") == "postgres":
        conn.execute("SELECT pg_advisory_xact_lock(?)", (7183001,))
        ensure_auth_schema(conn)
        ensure_platform_tenant(conn)
        ensure_default_tenant(conn)
        ensure_default_admin(conn)
        ensure_default_rbac(conn)
        return
    with _auth_schema_lock:
        ensure_auth_schema(conn)
        ensure_platform_tenant(conn)
        ensure_default_tenant(conn)
        ensure_default_admin(conn)
        ensure_default_rbac(conn)


def require_auth_ready(conn: Any) -> None:
    try:
        platform_row = conn.execute(
            "SELECT id FROM tenants WHERE tenant_key = ?",
            (PLATFORM_TENANT_KEY,),
        ).fetchone()
        default_row = conn.execute(
            "SELECT id FROM tenants WHERE tenant_key = ?",
            (DEFAULT_TENANT_KEY,),
        ).fetchone()
        admin_row = conn.execute(
            """
            SELECT u.id
            FROM users u
            JOIN tenants t ON t.id = u.tenant_id
            WHERE t.tenant_key = ?
              AND u.username = ?
              AND u.is_superuser = TRUE
            LIMIT 1
            """,
            (PLATFORM_TENANT_KEY, default_admin_username()),
        ).fetchone()
        conn.execute("SELECT 1 FROM roles LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM permissions LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM menus LIMIT 1").fetchone()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"identity storage is not initialized; run `{AUTH_INIT_COMMAND}`",
        ) from exc
    if not platform_row or not default_row or not admin_row:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"identity storage is not initialized; run `{AUTH_INIT_COMMAND}`",
        )


def row_to_api_key(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "tenant_id": int(row.get("tenant_id", 0) or 0),
        "name": str(row.get("name", "")),
        "prefix": str(row.get("prefix", "")),
        "is_active": bool(row.get("is_active", True)),
        "creator": str(row.get("creator", "") or ""),
        "creator_id": row.get("creator_id"),
        "create_time": str(row.get("create_time", "") or ""),
        "editor": str(row.get("editor", "") or ""),
        "editor_id": row.get("editor_id"),
        "update_time": str(row.get("update_time", "") or ""),
    }


def row_to_menu(row: dict[str, Any]) -> dict[str, Any]:
    key = str(row.get("menu_key", ""))
    return {
        "id": int(row.get("id", 0) or 0),
        "key": key,
        "label": str(row.get("label", "")),
        "menu_scope": str(row.get("menu_scope", "") or "tenant"),
        "menu_type": str(row.get("menu_type", "") or "page"),
        "path": str(row.get("path", "") or ""),
        "route_name": str(row.get("route_name", "") or ""),
        "component": str(row.get("component", "") or ""),
        "icon": str(row.get("icon", "") or ""),
        "parent_key": str(row.get("parent_key", "") or ""),
        "permission_code": str(row.get("permission_code", "") or ""),
        "sort_order": int(row.get("sort_order", 0) or 0),
        "is_visible": bool(row.get("is_visible", True)),
        "children": [],
    }


def build_menu_tree(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    menus = [row_to_menu(row) for row in rows if bool(row.get("is_visible", True))]
    by_key = {menu["key"]: menu for menu in menus}
    roots: list[dict[str, Any]] = []
    for menu in menus:
        parent_key = menu["parent_key"]
        if parent_key and parent_key in by_key:
            by_key[parent_key]["children"].append(menu)
        else:
            roots.append(menu)
    return roots
