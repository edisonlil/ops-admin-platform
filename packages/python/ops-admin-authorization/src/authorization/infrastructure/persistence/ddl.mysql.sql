CREATE TABLE IF NOT EXISTS data_resource_descriptors (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    resource_key VARCHAR(160) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    tenant_column VARCHAR(120) NOT NULL DEFAULT 'tenant_id',
    creator_column VARCHAR(120) NOT NULL DEFAULT 'creator_id',
    owner_user_column VARCHAR(120) NOT NULL DEFAULT 'owner_user_id',
    owner_department_column VARCHAR(120) NOT NULL DEFAULT 'owner_department_id',
    supported_scopes_json TEXT NOT NULL DEFAULT ('[]'),
    requires_data_scope TINYINT(1) NOT NULL DEFAULT 0,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (resource_key, deleted)
);

CREATE TABLE IF NOT EXISTS data_access_policies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    subject_type VARCHAR(40) NOT NULL,
    subject_id BIGINT NOT NULL,
    resource_key VARCHAR(160) NOT NULL,
    action VARCHAR(80) NOT NULL,
    scope VARCHAR(80) NOT NULL,
    department_ids_json TEXT NOT NULL DEFAULT ('[]'),
    priority BIGINT NOT NULL DEFAULT 100,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, subject_type, subject_id, resource_key, action, deleted)
);

CREATE INDEX idx_data_resource_descriptors_key ON data_resource_descriptors(resource_key, deleted);
CREATE INDEX idx_data_access_policies_subject ON data_access_policies(tenant_id, subject_type, subject_id, deleted);
CREATE INDEX idx_data_access_policies_resource ON data_access_policies(tenant_id, resource_key, action, deleted);
