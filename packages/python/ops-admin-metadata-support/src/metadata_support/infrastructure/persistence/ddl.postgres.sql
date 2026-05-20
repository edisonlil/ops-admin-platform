CREATE TABLE IF NOT EXISTS metadata_resource_types (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_context TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted SMALLINT NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL,
    creator TEXT NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL,
    editor TEXT NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_field_definitions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    resource_type_code TEXT NOT NULL,
    field_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'string',
    required SMALLINT NOT NULL DEFAULT 0,
    searchable SMALLINT NOT NULL DEFAULT 1,
    sort_order BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted SMALLINT NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL,
    creator TEXT NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL,
    editor TEXT NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, resource_type_code, field_key, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_tag_groups (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    sort_order BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted SMALLINT NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL,
    creator TEXT NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL,
    editor TEXT NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_tags (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 0,
    group_id BIGINT DEFAULT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    sort_order BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted SMALLINT NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL,
    creator TEXT NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL,
    editor TEXT NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_resource_metadata (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    resource_type_code TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted SMALLINT NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL,
    creator TEXT NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL,
    editor TEXT NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, resource_type_code, resource_id, deleted)
);

CREATE TABLE IF NOT EXISTS metadata_resource_metadata_entries (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    resource_type_code TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    field_key TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'string',
    value_text TEXT DEFAULT NULL,
    value_number DOUBLE PRECISION DEFAULT NULL,
    value_datetime TEXT DEFAULT NULL,
    value_boolean SMALLINT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted SMALLINT NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL,
    creator TEXT NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL,
    editor TEXT NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS metadata_resource_tags (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    resource_type_code TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    tag_id BIGINT NOT NULL,
    tag_code TEXT NOT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted SMALLINT NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL,
    creator TEXT NOT NULL DEFAULT '',
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL,
    editor TEXT NOT NULL DEFAULT '',
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, resource_type_code, resource_id, tag_id, deleted)
);

CREATE INDEX IF NOT EXISTS idx_metadata_resource_types_tenant ON metadata_resource_types(tenant_id, deleted, status);
CREATE INDEX IF NOT EXISTS idx_metadata_fields_resource ON metadata_field_definitions(tenant_id, resource_type_code, deleted, status);
CREATE INDEX IF NOT EXISTS idx_metadata_tag_groups_tenant ON metadata_tag_groups(tenant_id, deleted, status);
CREATE INDEX IF NOT EXISTS idx_metadata_tags_tenant_code ON metadata_tags(tenant_id, code, deleted, status);
CREATE INDEX IF NOT EXISTS idx_metadata_resources_lookup ON metadata_resource_metadata(tenant_id, resource_type_code, resource_id, deleted);
CREATE INDEX IF NOT EXISTS idx_metadata_entries_text ON metadata_resource_metadata_entries(tenant_id, resource_type_code, field_key, value_text, deleted, resource_id);
CREATE INDEX IF NOT EXISTS idx_metadata_entries_number ON metadata_resource_metadata_entries(tenant_id, resource_type_code, field_key, value_number, deleted, resource_id);
CREATE INDEX IF NOT EXISTS idx_metadata_entries_datetime ON metadata_resource_metadata_entries(tenant_id, resource_type_code, field_key, value_datetime, deleted, resource_id);
CREATE INDEX IF NOT EXISTS idx_metadata_entries_boolean ON metadata_resource_metadata_entries(tenant_id, resource_type_code, field_key, value_boolean, deleted, resource_id);
CREATE INDEX IF NOT EXISTS idx_metadata_resource_tags_lookup ON metadata_resource_tags(tenant_id, resource_type_code, tag_code, deleted, resource_id);
