CREATE TABLE IF NOT EXISTS page_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    page_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    page_type TEXT NOT NULL DEFAULT 'dashboard',
    status TEXT NOT NULL DEFAULT 'draft',
    current_version_id INTEGER DEFAULT NULL,
    thumbnail_file_id INTEGER DEFAULT NULL,
    settings_json TEXT NOT NULL DEFAULT '{}',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, page_key, deleted)
);

CREATE TABLE IF NOT EXISTS page_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    page_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL DEFAULT 1,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    layout_json TEXT NOT NULL DEFAULT '{}',
    components_json TEXT NOT NULL DEFAULT '[]',
    data_bindings_json TEXT NOT NULL DEFAULT '{}',
    interactions_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, page_id, version_no, deleted)
);

CREATE TABLE IF NOT EXISTS page_menu_mounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    page_id INTEGER NOT NULL,
    menu_key TEXT NOT NULL,
    parent_key TEXT NOT NULL DEFAULT 'page-designer',
    path TEXT NOT NULL,
    route_name TEXT NOT NULL,
    permission_code TEXT NOT NULL DEFAULT 'page_designer:page:view',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, page_id, deleted),
    UNIQUE (tenant_id, menu_key, deleted)
);

CREATE INDEX IF NOT EXISTS idx_page_definitions_tenant ON page_definitions(tenant_id, deleted, status, page_type);
CREATE INDEX IF NOT EXISTS idx_page_definitions_key ON page_definitions(tenant_id, page_key, deleted);
CREATE INDEX IF NOT EXISTS idx_page_versions_page ON page_versions(tenant_id, page_id, deleted, status, version_no);
CREATE INDEX IF NOT EXISTS idx_page_menu_mounts_page ON page_menu_mounts(tenant_id, page_id, deleted);
CREATE INDEX IF NOT EXISTS idx_page_menu_mounts_key ON page_menu_mounts(tenant_id, menu_key, deleted);
