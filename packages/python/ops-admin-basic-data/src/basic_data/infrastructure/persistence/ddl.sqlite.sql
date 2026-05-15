CREATE TABLE IF NOT EXISTS business_dictionary_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    owner_user_id INTEGER DEFAULT NULL,
    owner_department_id INTEGER DEFAULT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    description TEXT NOT NULL DEFAULT '',
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

CREATE TABLE IF NOT EXISTS business_dictionary_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    owner_user_id INTEGER DEFAULT NULL,
    owner_department_id INTEGER DEFAULT NULL,
    code TEXT NOT NULL,
    value TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    extra_json TEXT NOT NULL DEFAULT '{}',
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
    UNIQUE (tenant_id, type_id, code, deleted)
);

CREATE INDEX IF NOT EXISTS idx_business_dictionary_types_tenant ON business_dictionary_types(tenant_id, deleted, status);
CREATE INDEX IF NOT EXISTS idx_business_dictionary_types_parent ON business_dictionary_types(tenant_id, parent_id, deleted);
CREATE INDEX IF NOT EXISTS idx_business_dictionary_types_code ON business_dictionary_types(tenant_id, code, deleted);
CREATE INDEX IF NOT EXISTS idx_business_dictionary_types_owner_department ON business_dictionary_types(tenant_id, owner_department_id, deleted);
CREATE INDEX IF NOT EXISTS idx_business_dictionary_items_type ON business_dictionary_items(tenant_id, type_id, deleted, status);
CREATE INDEX IF NOT EXISTS idx_business_dictionary_items_owner_department ON business_dictionary_items(tenant_id, owner_department_id, deleted);

CREATE TABLE IF NOT EXISTS business_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    parent_code TEXT NOT NULL DEFAULT '',
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    sort_order INTEGER NOT NULL DEFAULT 0,
    extra_json TEXT NOT NULL DEFAULT '{}',
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

CREATE INDEX IF NOT EXISTS idx_business_regions_parent ON business_regions(tenant_id, parent_id, deleted, status, sort_order);
CREATE INDEX IF NOT EXISTS idx_business_regions_code ON business_regions(tenant_id, code, deleted);
CREATE INDEX IF NOT EXISTS idx_business_regions_level ON business_regions(tenant_id, level, deleted, status);
CREATE INDEX IF NOT EXISTS idx_business_regions_path ON business_regions(tenant_id, path);
