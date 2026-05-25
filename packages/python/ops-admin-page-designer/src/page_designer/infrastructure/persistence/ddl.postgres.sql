CREATE TABLE IF NOT EXISTS page_definitions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    page_key VARCHAR(120) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    page_type VARCHAR(40) NOT NULL DEFAULT 'dashboard',
    status VARCHAR(40) NOT NULL DEFAULT 'draft',
    current_version_id BIGINT DEFAULT NULL,
    thumbnail_file_id BIGINT DEFAULT NULL,
    settings_json TEXT NOT NULL DEFAULT '{}',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, page_key, deleted)
);

CREATE TABLE IF NOT EXISTS page_versions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    page_id BIGINT NOT NULL,
    version_no BIGINT NOT NULL DEFAULT 1,
    schema_version VARCHAR(40) NOT NULL DEFAULT '1.0',
    layout_json TEXT NOT NULL DEFAULT '{}',
    components_json TEXT NOT NULL DEFAULT '[]',
    data_bindings_json TEXT NOT NULL DEFAULT '{}',
    interactions_json TEXT NOT NULL DEFAULT '{}',
    status VARCHAR(40) NOT NULL DEFAULT 'draft',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, page_id, version_no, deleted)
);

CREATE TABLE IF NOT EXISTS page_menu_mounts (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    page_id BIGINT NOT NULL,
    menu_key VARCHAR(120) NOT NULL,
    parent_key VARCHAR(120) NOT NULL DEFAULT 'page-designer',
    path VARCHAR(500) NOT NULL,
    route_name VARCHAR(120) NOT NULL,
    permission_code VARCHAR(200) NOT NULL DEFAULT 'page_designer:page:view',
    sort_order BIGINT NOT NULL DEFAULT 0,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, page_id, deleted),
    UNIQUE (tenant_id, menu_key, deleted)
);

CREATE INDEX IF NOT EXISTS idx_page_definitions_tenant ON page_definitions(tenant_id, deleted, status, page_type);
CREATE INDEX IF NOT EXISTS idx_page_definitions_key ON page_definitions(tenant_id, page_key, deleted);
CREATE INDEX IF NOT EXISTS idx_page_versions_page ON page_versions(tenant_id, page_id, deleted, status, version_no);
CREATE INDEX IF NOT EXISTS idx_page_menu_mounts_page ON page_menu_mounts(tenant_id, page_id, deleted);
CREATE INDEX IF NOT EXISTS idx_page_menu_mounts_key ON page_menu_mounts(tenant_id, menu_key, deleted);
