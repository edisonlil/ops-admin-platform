CREATE TABLE IF NOT EXISTS file_libraries (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    library_type TEXT NOT NULL DEFAULT 'general',
    visibility TEXT NOT NULL DEFAULT 'tenant',
    status TEXT NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, name, deleted)
);

CREATE TABLE IF NOT EXISTS file_objects (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    library_id BIGINT DEFAULT NULL,
    original_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    extension TEXT NOT NULL DEFAULT '',
    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    size_bytes BIGINT NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL DEFAULT '',
    storage_provider TEXT NOT NULL DEFAULT 'minio',
    storage_bucket TEXT NOT NULL DEFAULT '',
    storage_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    visibility TEXT NOT NULL DEFAULT 'tenant',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    indexed_at TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS tenant_file_storage_quotas (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    quota_bytes BIGINT NOT NULL DEFAULT 0,
    max_file_size_bytes BIGINT NOT NULL DEFAULT 0,
    allowed_mime_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    blocked_extensions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, deleted)
);

CREATE TABLE IF NOT EXISTS file_storage_profiles (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    provider TEXT NOT NULL DEFAULT 'minio',
    name TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT '',
    bucket TEXT NOT NULL,
    access_key_id TEXT NOT NULL DEFAULT '',
    secret_access_key_encrypted TEXT NOT NULL DEFAULT '',
    path_style_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    tls_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    extra_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_access_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    file_id BIGINT DEFAULT NULL,
    action TEXT NOT NULL,
    actor_user_id BIGINT DEFAULT NULL,
    actor_name TEXT NOT NULL DEFAULT '',
    client_ip TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT 'success',
    detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_search_index_jobs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    file_id BIGINT DEFAULT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts BIGINT NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    scheduled_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_time TEXT DEFAULT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_file_libraries_tenant ON file_libraries(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_library ON file_objects(tenant_id, library_id, deleted);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_name ON file_objects(tenant_id, original_name);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_hash ON file_objects(tenant_id, sha256);
CREATE INDEX IF NOT EXISTS idx_file_objects_tenant_update ON file_objects(tenant_id, update_time);
CREATE INDEX IF NOT EXISTS idx_file_storage_profiles_default ON file_storage_profiles(provider, is_default, enabled, deleted);
CREATE INDEX IF NOT EXISTS idx_file_access_logs_tenant_file ON file_access_logs(tenant_id, file_id, create_time);
CREATE INDEX IF NOT EXISTS idx_file_index_jobs_tenant_status ON file_search_index_jobs(tenant_id, status, create_time);
