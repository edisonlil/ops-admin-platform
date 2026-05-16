CREATE TABLE IF NOT EXISTS ai_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    app_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    app_type TEXT NOT NULL DEFAULT 'single_turn_generation',
    status TEXT NOT NULL DEFAULT 'draft',
    endpoint_slug TEXT NOT NULL DEFAULT '',
    system_prompt TEXT NOT NULL DEFAULT '',
    developer_prompt TEXT NOT NULL DEFAULT '',
    user_prompt_template TEXT NOT NULL DEFAULT '',
    variables_schema_json TEXT NOT NULL DEFAULT '{}',
    output_schema_json TEXT NOT NULL DEFAULT '{}',
    model_preferences_json TEXT NOT NULL DEFAULT '{}',
    auth_policy_json TEXT NOT NULL DEFAULT '{}',
    quota_policy_json TEXT NOT NULL DEFAULT '{}',
    trace_policy_json TEXT NOT NULL DEFAULT '{}',
    runtime_config_json TEXT NOT NULL DEFAULT '{}',
    published_time TEXT DEFAULT NULL,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, app_key, deleted)
);

CREATE INDEX IF NOT EXISTS idx_ai_applications_tenant ON ai_applications(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_applications_status ON ai_applications(tenant_id, status, deleted);

CREATE TABLE IF NOT EXISTS tenant_ai_quotas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    max_applications INTEGER NOT NULL DEFAULT 5,
    max_capabilities INTEGER NOT NULL DEFAULT 50,
    max_assets INTEGER NOT NULL DEFAULT 200,
    daily_run_limit INTEGER NOT NULL DEFAULT 1000,
    monthly_token_limit INTEGER NOT NULL DEFAULT 1000000,
    enabled INTEGER NOT NULL DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_ai_quotas_tenant ON tenant_ai_quotas(tenant_id);

CREATE TABLE IF NOT EXISTS prompt_runtime_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    trace_id TEXT NOT NULL,
    caller_type TEXT NOT NULL DEFAULT 'studio_draft',
    caller_key TEXT NOT NULL DEFAULT '',
    app_key TEXT NOT NULL DEFAULT '',
    app_version TEXT NOT NULL DEFAULT '',
    route_key TEXT NOT NULL DEFAULT '',
    model_key TEXT NOT NULL DEFAULT '',
    provider_key TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    input_variables_json TEXT NOT NULL DEFAULT '{}',
    rendered_messages_json TEXT NOT NULL DEFAULT '[]',
    rendered_prompt TEXT NOT NULL DEFAULT '',
    answer_text TEXT NOT NULL DEFAULT '',
    usage_json TEXT NOT NULL DEFAULT '{}',
    elapsed_ms INTEGER NOT NULL DEFAULT 0,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    request_id TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, trace_id)
);

CREATE INDEX IF NOT EXISTS idx_prompt_runtime_traces_tenant ON prompt_runtime_traces(tenant_id);
CREATE INDEX IF NOT EXISTS idx_prompt_runtime_traces_caller ON prompt_runtime_traces(tenant_id, caller_type, caller_key);
CREATE INDEX IF NOT EXISTS idx_prompt_runtime_traces_created ON prompt_runtime_traces(create_time);
