CREATE TABLE IF NOT EXISTS prompt_assets (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    prompt_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    tags_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    status VARCHAR(255) NOT NULL DEFAULT ('draft'),
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, prompt_key, active_marker)
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
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, prompt_id, version, active_marker)
);

CREATE TABLE IF NOT EXISTS skill_assets (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    skill_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    tags_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    status VARCHAR(255) NOT NULL DEFAULT ('draft'),
    source_type VARCHAR(255) NOT NULL DEFAULT ('upload'),
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, skill_key, active_marker)
);

CREATE TABLE IF NOT EXISTS skill_versions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    skill_id BIGINT NOT NULL,
    version VARCHAR(255) NOT NULL,
    manifest_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    content_text LONGTEXT NOT NULL,
    content_sha256 VARCHAR(255) NOT NULL DEFAULT (''),
    entrypoint VARCHAR(255) NOT NULL DEFAULT ('SKILL.md'),
    runtime_constraints_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    validation_report_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    status VARCHAR(255) NOT NULL DEFAULT ('draft'),
    published_time TEXT DEFAULT NULL,
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, skill_id, version, active_marker)
);

CREATE INDEX idx_prompt_assets_tenant_status ON prompt_assets(tenant_id, status, deleted);
CREATE INDEX idx_prompt_versions_prompt ON prompt_versions(tenant_id, prompt_id, status, deleted);
CREATE INDEX idx_skill_assets_tenant_status ON skill_assets(tenant_id, status, deleted);
CREATE INDEX idx_skill_versions_skill ON skill_versions(tenant_id, skill_id, status, deleted);
