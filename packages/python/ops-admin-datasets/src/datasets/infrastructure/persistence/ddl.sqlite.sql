CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    owner_user_id INTEGER DEFAULT NULL,
    owner_department_id INTEGER DEFAULT NULL,
    key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    dataset_type TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'draft',
    visibility TEXT NOT NULL DEFAULT 'tenant',
    published_version_id INTEGER DEFAULT NULL,
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, key, active_marker)
);

CREATE TABLE IF NOT EXISTS dataset_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    dataset_id INTEGER NOT NULL,
    field_key TEXT NOT NULL,
    label TEXT NOT NULL,
    data_type TEXT NOT NULL DEFAULT 'text',
    semantic_type TEXT NOT NULL DEFAULT '',
    unit TEXT NOT NULL DEFAULT '',
    precision INTEGER DEFAULT NULL,
    nullable INTEGER NOT NULL DEFAULT 1,
    visible INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    expression TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}',
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, dataset_id, field_key, active_marker)
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    dataset_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'published',
    schema_json TEXT NOT NULL DEFAULT '{}',
    query_config_json TEXT NOT NULL DEFAULT '{}',
    sample_rows_json TEXT NOT NULL DEFAULT '[]',
    published_time TEXT DEFAULT NULL,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, dataset_id, version_no, deleted)
);

CREATE TABLE IF NOT EXISTS dataset_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    dataset_id INTEGER NOT NULL,
    row_key TEXT NOT NULL DEFAULT '',
    row_json TEXT NOT NULL DEFAULT '{}',
    sort_order INTEGER NOT NULL DEFAULT 0,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS dataset_query_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    dataset_id INTEGER DEFAULT NULL,
    version_id INTEGER DEFAULT NULL,
    run_type TEXT NOT NULL DEFAULT 'preview',
    status TEXT NOT NULL DEFAULT 'succeeded',
    row_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL DEFAULT '',
    request_json TEXT NOT NULL DEFAULT '{}',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_datasets_tenant_status ON datasets(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_datasets_owner_user ON datasets(tenant_id, owner_user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_datasets_owner_department ON datasets(tenant_id, owner_department_id, deleted);
CREATE INDEX IF NOT EXISTS idx_dataset_fields_dataset ON dataset_fields(tenant_id, dataset_id, deleted, sort_order);
CREATE INDEX IF NOT EXISTS idx_dataset_versions_dataset ON dataset_versions(tenant_id, dataset_id, deleted, version_no);
CREATE INDEX IF NOT EXISTS idx_dataset_rows_dataset ON dataset_rows(tenant_id, dataset_id, deleted, sort_order);
CREATE INDEX IF NOT EXISTS idx_dataset_query_runs_dataset ON dataset_query_runs(tenant_id, dataset_id, create_time);
