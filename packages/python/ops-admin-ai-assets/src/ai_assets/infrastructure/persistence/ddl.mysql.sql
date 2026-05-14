CREATE TABLE IF NOT EXISTS prompt_assets (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    prompt_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    tags_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    status VARCHAR(255) NOT NULL DEFAULT ('draft'),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, prompt_key, deleted)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    prompt_id BIGINT NOT NULL,
    version VARCHAR(255) NOT NULL,
    system_prompt TEXT NOT NULL DEFAULT (''),
    developer_prompt TEXT NOT NULL DEFAULT (''),
    user_prompt_template TEXT NOT NULL DEFAULT (''),
    variables_schema_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    output_schema_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    example_inputs_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    example_outputs_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    model_preferences_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    render_engine TEXT NOT NULL DEFAULT ('simple'),
    status VARCHAR(255) NOT NULL DEFAULT ('draft'),
    published_time TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, prompt_id, version, deleted)
);

CREATE INDEX idx_prompt_assets_tenant_status ON prompt_assets(tenant_id, status, deleted);
CREATE INDEX idx_prompt_versions_prompt ON prompt_versions(tenant_id, prompt_id, status, deleted);
