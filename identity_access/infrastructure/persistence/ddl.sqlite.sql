CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    remark TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tenant_memberships (
    tenant_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    is_tenant_admin INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    username TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    is_superuser INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (tenant_id, username)
);

CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    prefix TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    revoked_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT NULL,
    role_scope TEXT NOT NULL DEFAULT 'platform',
    role_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    is_system INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS menus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_key TEXT NOT NULL UNIQUE,
    menu_scope TEXT NOT NULL DEFAULT 'tenant',
    label TEXT NOT NULL,
    menu_type TEXT DEFAULT 'page',
    path TEXT DEFAULT '',
    route_name TEXT DEFAULT '',
    component TEXT DEFAULT '',
    icon TEXT DEFAULT '',
    parent_key TEXT DEFAULT '',
    permission_code TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    is_visible INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS role_menus (
    role_id INTEGER NOT NULL,
    menu_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, menu_id)
);

CREATE TABLE IF NOT EXISTS tenant_menu_overrides (
    tenant_id INTEGER NOT NULL,
    menu_key TEXT NOT NULL,
    is_enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, menu_key)
);

CREATE INDEX IF NOT EXISTS idx_tenants_key ON tenants(tenant_key);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenant_memberships_user ON tenant_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_tenant_memberships_tenant ON tenant_memberships(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_roles_key ON roles(role_key);
CREATE INDEX IF NOT EXISTS idx_permissions_code ON permissions(code);
CREATE INDEX IF NOT EXISTS idx_menus_key ON menus(menu_key);
CREATE INDEX IF NOT EXISTS idx_tenant_menu_overrides_tenant ON tenant_menu_overrides(tenant_id);
