CREATE TABLE IF NOT EXISTS ai_capabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
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
    input_schema_json TEXT NOT NULL DEFAULT '{}',
    output_schema_json TEXT NOT NULL DEFAULT '{}',
    model_preferences_json TEXT NOT NULL DEFAULT '{}',
    runtime_config_json TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, capability_key, deleted)
);

CREATE INDEX IF NOT EXISTS idx_ai_capabilities_tenant ON ai_capabilities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_capabilities_scope ON ai_capabilities(tenant_id, scope, deleted);
CREATE INDEX IF NOT EXISTS idx_ai_capabilities_binding ON ai_capabilities(tenant_id, binding_type, binding_key, deleted);
