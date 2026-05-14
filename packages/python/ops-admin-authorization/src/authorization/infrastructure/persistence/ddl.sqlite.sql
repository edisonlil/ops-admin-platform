CREATE TABLE IF NOT EXISTS data_resource_descriptors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    resource_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tenant_column TEXT NOT NULL DEFAULT 'tenant_id',
    creator_column TEXT NOT NULL DEFAULT 'creator_id',
    owner_user_column TEXT NOT NULL DEFAULT 'owner_user_id',
    owner_department_column TEXT NOT NULL DEFAULT 'owner_department_id',
    supported_scopes_json TEXT NOT NULL DEFAULT '[]',
    requires_data_scope INTEGER NOT NULL DEFAULT 0,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (resource_key, deleted)
);

CREATE TABLE IF NOT EXISTS role_data_scopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    role_key TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    action TEXT NOT NULL,
    scope TEXT NOT NULL,
    department_ids_json TEXT NOT NULL DEFAULT '[]',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, role_key, resource_key, action, deleted)
);

CREATE INDEX IF NOT EXISTS idx_data_resource_descriptors_key ON data_resource_descriptors(resource_key, deleted);
CREATE INDEX IF NOT EXISTS idx_role_data_scopes_role ON role_data_scopes(tenant_id, role_key, deleted);
CREATE INDEX IF NOT EXISTS idx_role_data_scopes_resource ON role_data_scopes(tenant_id, resource_key, action, deleted);
