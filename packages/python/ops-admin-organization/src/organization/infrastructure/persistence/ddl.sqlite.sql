CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    manager_user_id INTEGER DEFAULT NULL,
    base_location TEXT NOT NULL DEFAULT '',
    region TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    sort_order INTEGER NOT NULL DEFAULT 0,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS user_department_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, user_id, department_id, active_marker)
);

CREATE TABLE IF NOT EXISTS user_reporting_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    manager_user_id INTEGER NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 1,
    relationship_type TEXT NOT NULL DEFAULT 'direct',
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, user_id, relationship_type, active_marker)
);

CREATE INDEX IF NOT EXISTS idx_departments_tenant_parent ON departments(tenant_id, parent_id, deleted);
CREATE INDEX IF NOT EXISTS idx_departments_tenant_status ON departments(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_user_department_memberships_user ON user_department_memberships(tenant_id, user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_user_department_memberships_department ON user_department_memberships(tenant_id, department_id, deleted);
CREATE INDEX IF NOT EXISTS idx_user_reporting_relationships_user ON user_reporting_relationships(tenant_id, user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_user_reporting_relationships_manager ON user_reporting_relationships(tenant_id, manager_user_id, deleted);
