CREATE TABLE IF NOT EXISTS datasets (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    dataset_type TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'draft',
    visibility TEXT NOT NULL DEFAULT 'tenant',
    published_version_id BIGINT DEFAULT NULL,
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, key, active_marker)
);

CREATE TABLE IF NOT EXISTS dataset_fields (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    field_key TEXT NOT NULL,
    label TEXT NOT NULL,
    data_type TEXT NOT NULL DEFAULT 'text',
    semantic_type TEXT NOT NULL DEFAULT '',
    unit TEXT NOT NULL DEFAULT '',
    precision BIGINT DEFAULT NULL,
    nullable BOOLEAN NOT NULL DEFAULT TRUE,
    visible BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order BIGINT NOT NULL DEFAULT 0,
    expression TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}',
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, dataset_id, field_key, active_marker)
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    version_no BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'published',
    schema_json TEXT NOT NULL DEFAULT '{}',
    query_config_json TEXT NOT NULL DEFAULT '{}',
    sample_rows_json TEXT NOT NULL DEFAULT '[]',
    published_time TIMESTAMPTZ DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, dataset_id, version_no, deleted)
);

CREATE TABLE IF NOT EXISTS dataset_rows (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    row_key TEXT NOT NULL DEFAULT '',
    row_json TEXT NOT NULL DEFAULT '{}',
    sort_order BIGINT NOT NULL DEFAULT 0,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS dataset_query_runs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    dataset_id BIGINT DEFAULT NULL,
    version_id BIGINT DEFAULT NULL,
    run_type TEXT NOT NULL DEFAULT 'preview',
    status TEXT NOT NULL DEFAULT 'succeeded',
    row_count BIGINT NOT NULL DEFAULT 0,
    duration_ms BIGINT NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL DEFAULT '',
    request_json TEXT NOT NULL DEFAULT '{}',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_datasets_tenant_status ON datasets(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_datasets_owner_user ON datasets(tenant_id, owner_user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_datasets_owner_department ON datasets(tenant_id, owner_department_id, deleted);
CREATE INDEX IF NOT EXISTS idx_dataset_fields_dataset ON dataset_fields(tenant_id, dataset_id, deleted, sort_order);
CREATE INDEX IF NOT EXISTS idx_dataset_versions_dataset ON dataset_versions(tenant_id, dataset_id, deleted, version_no);
CREATE INDEX IF NOT EXISTS idx_dataset_rows_dataset ON dataset_rows(tenant_id, dataset_id, deleted, sort_order);
CREATE INDEX IF NOT EXISTS idx_dataset_query_runs_dataset ON dataset_query_runs(tenant_id, dataset_id, create_time);
