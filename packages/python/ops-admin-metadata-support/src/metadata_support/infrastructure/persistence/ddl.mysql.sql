CREATE TABLE IF NOT EXISTS metadata_resource_types (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    code VARCHAR(191) NOT NULL,
    name VARCHAR(255) NOT NULL,
    owner_context VARCHAR(191) NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT NOT NULL DEFAULT 0,
    create_time VARCHAR(64) NOT NULL,
    creator VARCHAR(191) NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time VARCHAR(64) NOT NULL,
    editor VARCHAR(191) NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY metadata_resource_types_current_unique (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_field_definitions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    resource_type_code VARCHAR(191) NOT NULL,
    field_key VARCHAR(191) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    value_type VARCHAR(32) NOT NULL DEFAULT 'string',
    required TINYINT NOT NULL DEFAULT 0,
    searchable TINYINT NOT NULL DEFAULT 1,
    sort_order BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT NOT NULL DEFAULT 0,
    create_time VARCHAR(64) NOT NULL,
    creator VARCHAR(191) NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time VARCHAR(64) NOT NULL,
    editor VARCHAR(191) NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY metadata_fields_current_unique (tenant_id, resource_type_code, field_key, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_tag_groups (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    code VARCHAR(191) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    sort_order BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT NOT NULL DEFAULT 0,
    create_time VARCHAR(64) NOT NULL,
    creator VARCHAR(191) NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time VARCHAR(64) NOT NULL,
    editor VARCHAR(191) NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY metadata_tag_groups_current_unique (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_tags (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    group_id BIGINT DEFAULT NULL,
    code VARCHAR(191) NOT NULL,
    name VARCHAR(255) NOT NULL,
    color VARCHAR(64) NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    sort_order BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT NOT NULL DEFAULT 0,
    create_time VARCHAR(64) NOT NULL,
    creator VARCHAR(191) NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time VARCHAR(64) NOT NULL,
    editor VARCHAR(191) NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY metadata_tags_current_unique (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_resource_metadata (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    resource_type_code VARCHAR(191) NOT NULL,
    resource_id VARCHAR(191) NOT NULL,
    metadata_json JSON NOT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT NOT NULL DEFAULT 0,
    create_time VARCHAR(64) NOT NULL,
    creator VARCHAR(191) NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time VARCHAR(64) NOT NULL,
    editor VARCHAR(191) NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY metadata_resources_current_unique (tenant_id, resource_type_code, resource_id, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_resource_metadata_entries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    resource_type_code VARCHAR(191) NOT NULL,
    resource_id VARCHAR(191) NOT NULL,
    field_key VARCHAR(191) NOT NULL,
    value_type VARCHAR(32) NOT NULL DEFAULT 'string',
    value_text VARCHAR(512) DEFAULT NULL,
    value_number DOUBLE DEFAULT NULL,
    value_datetime VARCHAR(64) DEFAULT NULL,
    value_boolean TINYINT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT NOT NULL DEFAULT 0,
    create_time VARCHAR(64) NOT NULL,
    creator VARCHAR(191) NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time VARCHAR(64) NOT NULL,
    editor VARCHAR(191) NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS metadata_resource_tags (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    resource_type_code VARCHAR(191) NOT NULL,
    resource_id VARCHAR(191) NOT NULL,
    tag_id BIGINT NOT NULL,
    tag_code VARCHAR(191) NOT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT NOT NULL DEFAULT 0,
    create_time VARCHAR(64) NOT NULL,
    creator VARCHAR(191) NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time VARCHAR(64) NOT NULL,
    editor VARCHAR(191) NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE KEY metadata_resource_tags_current_unique (tenant_id, resource_type_code, resource_id, tag_id, deleted)
);

CREATE INDEX idx_metadata_resource_types_tenant ON metadata_resource_types(tenant_id, deleted, status);
CREATE INDEX idx_metadata_fields_resource ON metadata_field_definitions(tenant_id, resource_type_code, deleted, status);
CREATE INDEX idx_metadata_tag_groups_tenant ON metadata_tag_groups(tenant_id, deleted, status);
CREATE INDEX idx_metadata_tags_tenant_code ON metadata_tags(tenant_id, code, deleted, status);
CREATE INDEX idx_metadata_resources_lookup ON metadata_resource_metadata(tenant_id, resource_type_code, resource_id, deleted);
CREATE INDEX idx_metadata_entries_text ON metadata_resource_metadata_entries(tenant_id, resource_type_code, field_key, value_text(191), deleted, resource_id);
CREATE INDEX idx_metadata_entries_number ON metadata_resource_metadata_entries(tenant_id, resource_type_code, field_key, value_number, deleted, resource_id);
CREATE INDEX idx_metadata_entries_datetime ON metadata_resource_metadata_entries(tenant_id, resource_type_code, field_key, value_datetime, deleted, resource_id);
CREATE INDEX idx_metadata_entries_boolean ON metadata_resource_metadata_entries(tenant_id, resource_type_code, field_key, value_boolean, deleted, resource_id);
CREATE INDEX idx_metadata_resource_tags_lookup ON metadata_resource_tags(tenant_id, resource_type_code, tag_code, deleted, resource_id);
