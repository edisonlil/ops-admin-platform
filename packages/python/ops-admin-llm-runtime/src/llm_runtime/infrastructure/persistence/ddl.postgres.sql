CREATE TABLE IF NOT EXISTS llm_configs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    provider TEXT NOT NULL DEFAULT 'minimax',
    model TEXT DEFAULT '',
    base_url TEXT DEFAULT '',
    api_key TEXT DEFAULT '',
    command TEXT DEFAULT '',
    timeout_seconds DOUBLE PRECISION DEFAULT 120,
    temperature DOUBLE PRECISION DEFAULT 0.1,
    extra_body JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_llm_configs_active ON llm_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_llm_configs_tenant ON llm_configs(tenant_id);

CREATE TABLE IF NOT EXISTS llm_providers (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    provider_key TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    base_url TEXT NOT NULL DEFAULT '',
    api_key TEXT NOT NULL DEFAULT '',
    auth_type TEXT NOT NULL DEFAULT 'bearer',
    extra_headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    extra_body JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE(tenant_id, provider_key)
);

CREATE INDEX IF NOT EXISTS idx_llm_providers_enabled ON llm_providers(enabled);
CREATE INDEX IF NOT EXISTS idx_llm_providers_tenant ON llm_providers(tenant_id);

CREATE TABLE IF NOT EXISTS llm_models (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    model_key TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    model_name TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    context_window BIGINT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE(tenant_id, model_key)
);

CREATE INDEX IF NOT EXISTS idx_llm_models_tenant ON llm_models(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_models_provider ON llm_models(provider_key);
CREATE INDEX IF NOT EXISTS idx_llm_models_enabled ON llm_models(enabled);

CREATE TABLE IF NOT EXISTS llm_tasks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_key TEXT NOT NULL,
    context_key TEXT NOT NULL DEFAULT '',
    scene_key TEXT NOT NULL DEFAULT '',
    task_name TEXT NOT NULL DEFAULT '',
    display_name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    owner_context TEXT NOT NULL DEFAULT '',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE(tenant_id, task_key)
);

CREATE INDEX IF NOT EXISTS idx_llm_tasks_tenant ON llm_tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_tasks_context ON llm_tasks(context_key);
CREATE INDEX IF NOT EXISTS idx_llm_tasks_enabled ON llm_tasks(enabled);

CREATE TABLE IF NOT EXISTS llm_routing_policies (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    route_key TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT 'priority',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE(tenant_id, route_key)
);

CREATE INDEX IF NOT EXISTS idx_llm_routing_policies_tenant ON llm_routing_policies(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_routing_policies_enabled ON llm_routing_policies(enabled);

CREATE TABLE IF NOT EXISTS llm_routing_policy_entries (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    policy_id BIGINT NOT NULL,
    model_key TEXT NOT NULL,
    priority BIGINT NOT NULL DEFAULT 100,
    temperature DOUBLE PRECISION DEFAULT 0.1,
    timeout_seconds DOUBLE PRECISION DEFAULT 120,
    max_retries BIGINT NOT NULL DEFAULT 0,
    response_format TEXT NOT NULL DEFAULT 'text',
    extra_body JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_llm_routing_entries_tenant ON llm_routing_policy_entries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_routing_entries_policy ON llm_routing_policy_entries(policy_id);
CREATE INDEX IF NOT EXISTS idx_llm_routing_entries_model ON llm_routing_policy_entries(model_key);
CREATE INDEX IF NOT EXISTS idx_llm_routing_entries_enabled ON llm_routing_policy_entries(enabled);

CREATE TABLE IF NOT EXISTS llm_call_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_key TEXT NOT NULL,
    route_key TEXT NOT NULL DEFAULT '',
    policy_id BIGINT,
    entry_id BIGINT,
    provider_key TEXT NOT NULL DEFAULT '',
    model_key TEXT NOT NULL DEFAULT '',
    model_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    elapsed_ms BIGINT DEFAULT 0,
    prompt_tokens BIGINT DEFAULT 0,
    completion_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    request_id TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_llm_call_logs_tenant ON llm_call_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_task ON llm_call_logs(task_key);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_created ON llm_call_logs(create_time);

CREATE TABLE IF NOT EXISTS ai_applications (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    app_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    app_type TEXT NOT NULL DEFAULT 'single_turn_generation',
    status TEXT NOT NULL DEFAULT 'draft',
    endpoint_slug TEXT NOT NULL DEFAULT '',
    system_prompt TEXT NOT NULL DEFAULT '',
    developer_prompt TEXT NOT NULL DEFAULT '',
    user_prompt_template TEXT NOT NULL DEFAULT '',
    variables_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_preferences_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    auth_policy_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    quota_policy_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    trace_policy_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    runtime_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_time TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, app_key, deleted)
);

CREATE INDEX IF NOT EXISTS idx_ai_applications_tenant ON ai_applications(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_applications_status ON ai_applications(tenant_id, status, deleted);

CREATE TABLE IF NOT EXISTS tenant_ai_quotas (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    max_applications BIGINT NOT NULL DEFAULT 5,
    max_capabilities BIGINT NOT NULL DEFAULT 50,
    max_assets BIGINT NOT NULL DEFAULT 200,
    daily_run_limit BIGINT NOT NULL DEFAULT 1000,
    monthly_token_limit BIGINT NOT NULL DEFAULT 1000000,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_ai_quotas_tenant ON tenant_ai_quotas(tenant_id);

CREATE TABLE IF NOT EXISTS prompt_runtime_traces (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    trace_id TEXT NOT NULL,
    caller_type TEXT NOT NULL DEFAULT 'studio_draft',
    caller_key TEXT NOT NULL DEFAULT '',
    app_key TEXT NOT NULL DEFAULT '',
    app_version TEXT NOT NULL DEFAULT '',
    route_key TEXT NOT NULL DEFAULT '',
    model_key TEXT NOT NULL DEFAULT '',
    provider_key TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    input_variables_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    rendered_messages_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    rendered_prompt TEXT NOT NULL DEFAULT '',
    answer_text TEXT NOT NULL DEFAULT '',
    usage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    elapsed_ms BIGINT NOT NULL DEFAULT 0,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    request_id TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, trace_id)
);

CREATE INDEX IF NOT EXISTS idx_prompt_runtime_traces_tenant ON prompt_runtime_traces(tenant_id);
CREATE INDEX IF NOT EXISTS idx_prompt_runtime_traces_caller ON prompt_runtime_traces(tenant_id, caller_type, caller_key);
CREATE INDEX IF NOT EXISTS idx_prompt_runtime_traces_created ON prompt_runtime_traces(create_time);
