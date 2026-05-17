CREATE TABLE IF NOT EXISTS file_libraries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    library_type VARCHAR(255) NOT NULL DEFAULT ('general'),
    visibility VARCHAR(255) NOT NULL DEFAULT ('tenant'),
    status VARCHAR(255) NOT NULL DEFAULT ('active'),
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, name, active_marker)
);

CREATE TABLE IF NOT EXISTS file_objects (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    library_id BIGINT DEFAULT NULL,
    folder_id BIGINT DEFAULT NULL,
    original_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    extension VARCHAR(255) NOT NULL DEFAULT (''),
    mime_type VARCHAR(255) NOT NULL DEFAULT ('application/octet-stream'),
    size_bytes BIGINT NOT NULL DEFAULT 0,
    sha256 VARCHAR(255) NOT NULL DEFAULT (''),
    storage_provider VARCHAR(255) NOT NULL DEFAULT ('minio'),
    storage_bucket VARCHAR(255) NOT NULL DEFAULT (''),
    storage_key VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT ('available'),
    visibility VARCHAR(255) NOT NULL DEFAULT ('tenant'),
    metadata_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    indexed_at TEXT DEFAULT NULL,
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_folders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    library_id BIGINT NOT NULL,
    parent_id BIGINT DEFAULT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    status VARCHAR(255) NOT NULL DEFAULT ('active'),
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, library_id, parent_id, name, active_marker)
);

CREATE TABLE IF NOT EXISTS tenant_file_storage_quotas (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    quota_bytes BIGINT NOT NULL DEFAULT 0,
    max_file_size_bytes BIGINT NOT NULL DEFAULT 0,
    allowed_mime_types_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    blocked_extensions_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, deleted)
);

CREATE TABLE IF NOT EXISTS file_storage_profiles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    provider VARCHAR(255) NOT NULL DEFAULT ('minio'),
    name VARCHAR(255) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    region VARCHAR(255) NOT NULL DEFAULT (''),
    bucket VARCHAR(255) NOT NULL,
    access_key_id VARCHAR(255) NOT NULL DEFAULT (''),
    secret_access_key_encrypted VARCHAR(255) NOT NULL DEFAULT (''),
    path_style_enabled TINYINT(1) NOT NULL DEFAULT 1,
    tls_enabled TINYINT(1) NOT NULL DEFAULT 1,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    extra_config_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_preview_profiles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    provider VARCHAR(255) NOT NULL DEFAULT ('kkfileview'),
    name VARCHAR(255) NOT NULL,
    base_url TEXT NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    supported_extensions_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    config_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_access_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    file_id BIGINT DEFAULT NULL,
    action TEXT NOT NULL,
    actor_user_id BIGINT DEFAULT NULL,
    actor_name VARCHAR(255) NOT NULL DEFAULT (''),
    client_ip TEXT NOT NULL DEFAULT (''),
    user_agent TEXT NOT NULL DEFAULT (''),
    result TEXT NOT NULL DEFAULT ('success'),
    detail_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS file_search_index_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    file_id BIGINT DEFAULT NULL,
    job_type VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT ('pending'),
    attempts BIGINT NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT (''),
    scheduled_time TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    finished_time TEXT DEFAULT NULL,
    payload_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX idx_file_libraries_tenant ON file_libraries(tenant_id, status, deleted);
CREATE INDEX idx_file_objects_tenant_library ON file_objects(tenant_id, library_id, deleted);
CREATE INDEX idx_file_objects_tenant_folder ON file_objects(tenant_id, library_id, folder_id, deleted);
CREATE INDEX idx_file_objects_tenant_name ON file_objects(tenant_id, original_name);
CREATE INDEX idx_file_objects_tenant_hash ON file_objects(tenant_id, sha256);
CREATE INDEX idx_file_objects_tenant_update ON file_objects(tenant_id, update_time);
CREATE INDEX idx_file_folders_tenant_parent ON file_folders(tenant_id, library_id, parent_id, deleted);
CREATE INDEX idx_file_storage_profiles_default ON file_storage_profiles(provider, is_default, enabled, deleted);
CREATE INDEX idx_file_preview_profiles_default ON file_preview_profiles(provider, is_default, enabled, deleted);
CREATE INDEX idx_file_access_logs_tenant_file ON file_access_logs(tenant_id, file_id, create_time);
CREATE INDEX idx_file_index_jobs_tenant_status ON file_search_index_jobs(tenant_id, status, create_time);
