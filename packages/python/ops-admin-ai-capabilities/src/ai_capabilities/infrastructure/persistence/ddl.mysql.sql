CREATE TABLE IF NOT EXISTS ai_capabilities (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    capability_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    scope VARCHAR(64) NOT NULL DEFAULT ('tenant'),
    binding_type VARCHAR(64) NOT NULL DEFAULT ('prompt_runtime'),
    binding_key VARCHAR(255) NOT NULL DEFAULT (''),
    call_method VARCHAR(255) NOT NULL DEFAULT ('aiService.execute'),
    system_prompt TEXT NOT NULL DEFAULT (''),
    developer_prompt TEXT NOT NULL DEFAULT (''),
    user_prompt_template TEXT NOT NULL DEFAULT (''),
    input_schema_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    output_schema_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    model_preferences_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    runtime_config_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, capability_key, deleted)
);

CREATE INDEX idx_ai_capabilities_tenant ON ai_capabilities(tenant_id);
CREATE INDEX idx_ai_capabilities_scope ON ai_capabilities(tenant_id, scope, deleted);
CREATE INDEX idx_ai_capabilities_binding ON ai_capabilities(tenant_id, binding_type, binding_key, deleted);
