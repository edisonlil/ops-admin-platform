CREATE TABLE IF NOT EXISTS file_libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    library_type TEXT NOT NULL DEFAULT 'general',
    visibility TEXT NOT NULL DEFAULT 'tenant',
    status TEXT NOT NULL DEFAULT 'active',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, name, deleted)
);

CREATE TABLE IF NOT EXISTS file_objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    library_id INTEGER DEFAULT NULL,
    folder_id INTEGER DEFAULT NULL,
    original_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    extension TEXT NOT NULL DEFAULT '',
    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL DEFAULT '',
    storage_provider TEXT NOT NULL DEFAULT 'minio',
    storage_bucket TEXT NOT NULL DEFAULT '',
    storage_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    visibility TEXT NOT NULL DEFAULT 'tenant',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    indexed_at TEXT DEFAULT NULL,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    library_id INTEGER NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, library_id, parent_id, name, deleted)
);

CREATE TABLE IF NOT EXISTS tenant_file_storage_quotas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    quota_bytes INTEGER NOT NULL DEFAULT 0,
    max_file_size_bytes INTEGER NOT NULL DEFAULT 0,
    allowed_mime_types_json TEXT NOT NULL DEFAULT '[]',
    blocked_extensions_json TEXT NOT NULL DEFAULT '[]',
    enabled INTEGER NOT NULL DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, deleted)
);

CREATE TABLE IF NOT EXISTS file_storage_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 0,
    provider TEXT NOT NULL DEFAULT 'minio',
    name TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT '',
    bucket TEXT NOT NULL,
    access_key_id TEXT NOT NULL DEFAULT '',
    secret_access_key_encrypted TEXT NOT NULL DEFAULT '',
    path_style_enabled INTEGER NOT NULL DEFAULT 1,
    tls_enabled INTEGER NOT NULL DEFAULT 1,
    is_default INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    extra_config_json TEXT NOT NULL DEFAULT '{}',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_preview_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 0,
    provider TEXT NOT NULL DEFAULT 'kkfileview',
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    is_default INTEGER NOT NULL DEFAULT 0,
    supported_extensions_json TEXT NOT NULL DEFAULT '[]',
    config_json TEXT NOT NULL DEFAULT '{}',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    file_id INTEGER DEFAULT NULL,
    action TEXT NOT NULL,
    actor_user_id INTEGER DEFAULT NULL,
    actor_name TEXT NOT NULL DEFAULT '',
    client_ip TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT 'success',
    detail_json TEXT NOT NULL DEFAULT '{}',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_search_index_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    file_id INTEGER DEFAULT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    scheduled_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_time TEXT DEFAULT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_file_libraries_tenant ON file_libraries(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_library ON file_objects(tenant_id, library_id, deleted);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_folder ON file_objects(tenant_id, library_id, folder_id, deleted);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_name ON file_objects(tenant_id, original_name);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_hash ON file_objects(tenant_id, sha256);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_update ON file_objects(tenant_id, update_time);
CREATE INDEX IF NOT EXISTS idx_file_folders_tenant_parent ON file_folders(tenant_id, library_id, parent_id, deleted);
CREATE INDEX IF NOT EXISTS idx_file_storage_profiles_default ON file_storage_profiles(provider, is_default, enabled, deleted);
CREATE INDEX IF NOT EXISTS idx_file_preview_profiles_default ON file_preview_profiles(provider, is_default, enabled, deleted);
CREATE INDEX IF NOT EXISTS idx_file_access_logs_tenant_file ON file_access_logs(tenant_id, file_id, create_time);
CREATE INDEX IF NOT EXISTS idx_file_index_jobs_tenant_status ON file_search_index_jobs(tenant_id, status, create_time);
