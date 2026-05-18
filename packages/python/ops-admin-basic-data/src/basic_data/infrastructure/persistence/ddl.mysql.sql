CREATE TABLE IF NOT EXISTS business_dictionary_types (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    parent_id BIGINT DEFAULT NULL,
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    code VARCHAR(120) NOT NULL,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(120) NOT NULL DEFAULT 'general',
    description TEXT NOT NULL DEFAULT (''),
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    sort_order BIGINT NOT NULL DEFAULT 0,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS business_dictionary_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    type_id BIGINT NOT NULL,
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    code VARCHAR(120) NOT NULL,
    value VARCHAR(300) NOT NULL,
    color VARCHAR(80) NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT (''),
    extra_json TEXT NOT NULL DEFAULT ('{}'),
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    sort_order BIGINT NOT NULL DEFAULT 0,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, type_id, code, deleted)
);

CREATE INDEX idx_business_dictionary_types_tenant ON business_dictionary_types(tenant_id, deleted, status);
CREATE INDEX idx_business_dictionary_types_parent ON business_dictionary_types(tenant_id, parent_id, deleted);
CREATE INDEX idx_business_dictionary_types_code ON business_dictionary_types(tenant_id, code, deleted);
CREATE INDEX idx_business_dictionary_types_owner_department ON business_dictionary_types(tenant_id, owner_department_id, deleted);
CREATE INDEX idx_business_dictionary_items_type ON business_dictionary_items(tenant_id, type_id, deleted, status);
CREATE INDEX idx_business_dictionary_items_owner_department ON business_dictionary_items(tenant_id, owner_department_id, deleted);

CREATE TABLE IF NOT EXISTS business_regions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    parent_id BIGINT DEFAULT NULL,
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    parent_code VARCHAR(120) NOT NULL DEFAULT '',
    code VARCHAR(120) NOT NULL,
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(200) NOT NULL DEFAULT '',
    level VARCHAR(40) NOT NULL,
    path VARCHAR(1000) NOT NULL DEFAULT '',
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    sort_order BIGINT NOT NULL DEFAULT 0,
    extra_json TEXT NOT NULL DEFAULT ('{}'),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, code, deleted)
);

CREATE INDEX idx_business_regions_parent ON business_regions(tenant_id, parent_id, deleted, status, sort_order);
CREATE INDEX idx_business_regions_code ON business_regions(tenant_id, code, deleted);
CREATE INDEX idx_business_regions_level ON business_regions(tenant_id, level, deleted, status);
CREATE INDEX idx_business_regions_path ON business_regions(tenant_id, path(255));
CREATE INDEX idx_business_regions_owner_department ON business_regions(tenant_id, owner_department_id, deleted);
