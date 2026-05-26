CREATE TABLE IF NOT EXISTS datasets (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    `key` VARCHAR(191) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    dataset_type VARCHAR(64) NOT NULL DEFAULT 'manual',
    status VARCHAR(64) NOT NULL DEFAULT 'draft',
    visibility VARCHAR(64) NOT NULL DEFAULT 'platform',
    published_version_id BIGINT DEFAULT NULL,
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(255) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(255) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY datasets_current_unique (tenant_id, `key`, active_marker)
);

CREATE TABLE IF NOT EXISTS dataset_fields (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    field_key VARCHAR(191) NOT NULL,
    label VARCHAR(255) NOT NULL,
    data_type VARCHAR(64) NOT NULL DEFAULT 'text',
    semantic_type VARCHAR(64) NOT NULL DEFAULT '',
    unit VARCHAR(64) NOT NULL DEFAULT '',
    `precision` BIGINT DEFAULT NULL,
    nullable BOOLEAN NOT NULL DEFAULT TRUE,
    visible BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order BIGINT NOT NULL DEFAULT 0,
    expression TEXT NOT NULL,
    config_json TEXT NOT NULL,
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(255) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(255) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY dataset_fields_current_unique (tenant_id, dataset_id, field_key, active_marker)
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    version_no BIGINT NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'published',
    schema_json TEXT NOT NULL,
    query_config_json TEXT NOT NULL,
    sample_rows_json TEXT NOT NULL,
    published_time DATETIME DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(255) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(255) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY dataset_versions_current_unique (tenant_id, dataset_id, version_no, deleted)
);

CREATE TABLE IF NOT EXISTS dataset_rows (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    row_key VARCHAR(191) NOT NULL DEFAULT '',
    row_json TEXT NOT NULL,
    sort_order BIGINT NOT NULL DEFAULT 0,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(255) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(255) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS dataset_query_runs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    dataset_id BIGINT DEFAULT NULL,
    version_id BIGINT DEFAULT NULL,
    run_type VARCHAR(64) NOT NULL DEFAULT 'preview',
    status VARCHAR(64) NOT NULL DEFAULT 'succeeded',
    row_count BIGINT NOT NULL DEFAULT 0,
    duration_ms BIGINT NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL,
    request_json TEXT NOT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(255) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(255) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX idx_datasets_tenant_status ON datasets(tenant_id, status, deleted);
CREATE INDEX idx_datasets_owner_user ON datasets(tenant_id, owner_user_id, deleted);
CREATE INDEX idx_datasets_owner_department ON datasets(tenant_id, owner_department_id, deleted);
CREATE INDEX idx_dataset_fields_dataset ON dataset_fields(tenant_id, dataset_id, deleted, sort_order);
CREATE INDEX idx_dataset_versions_dataset ON dataset_versions(tenant_id, dataset_id, deleted, version_no);
CREATE INDEX idx_dataset_rows_dataset ON dataset_rows(tenant_id, dataset_id, deleted, sort_order);
CREATE INDEX idx_dataset_query_runs_dataset ON dataset_query_runs(tenant_id, dataset_id, create_time);
