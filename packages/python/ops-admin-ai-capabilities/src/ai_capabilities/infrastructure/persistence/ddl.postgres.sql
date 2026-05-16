CREATE TABLE IF NOT EXISTS ai_capabilities (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    capability_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT 'tenant',
    binding_type TEXT NOT NULL DEFAULT 'prompt_runtime',
    binding_key TEXT NOT NULL DEFAULT '',
    call_method TEXT NOT NULL DEFAULT 'aiService.execute',
    system_prompt TEXT NOT NULL DEFAULT '',
    developer_prompt TEXT NOT NULL DEFAULT '',
    user_prompt_template TEXT NOT NULL DEFAULT '',
    input_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_preferences_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    runtime_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, capability_key, deleted)
);

CREATE INDEX IF NOT EXISTS idx_ai_capabilities_tenant ON ai_capabilities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_capabilities_scope ON ai_capabilities(tenant_id, scope, deleted);
CREATE INDEX IF NOT EXISTS idx_ai_capabilities_binding ON ai_capabilities(tenant_id, binding_type, binding_key, deleted);
