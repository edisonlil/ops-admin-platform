CREATE TABLE IF NOT EXISTS llm_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    provider VARCHAR(255) NOT NULL DEFAULT ('minimax'),
    model VARCHAR(255) DEFAULT (''),
    base_url TEXT DEFAULT (''),
    api_key VARCHAR(255) DEFAULT (''),
    command TEXT DEFAULT (''),
    timeout_seconds DOUBLE PRECISION DEFAULT 120,
    temperature DOUBLE PRECISION DEFAULT 0.1,
    extra_body JSON NOT NULL DEFAULT (JSON_OBJECT()),
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX idx_llm_configs_active ON llm_configs(is_active);
CREATE INDEX idx_llm_configs_tenant ON llm_configs(tenant_id);

CREATE TABLE IF NOT EXISTS llm_providers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    provider_key VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL DEFAULT (''),
    base_url TEXT NOT NULL DEFAULT (''),
    api_key VARCHAR(255) NOT NULL DEFAULT (''),
    auth_type VARCHAR(255) NOT NULL DEFAULT ('bearer'),
    extra_headers JSON NOT NULL DEFAULT (JSON_OBJECT()),
    extra_body JSON NOT NULL DEFAULT (JSON_OBJECT()),
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE(tenant_id, provider_key)
);

CREATE INDEX idx_llm_providers_enabled ON llm_providers(enabled);
CREATE INDEX idx_llm_providers_tenant ON llm_providers(tenant_id);

CREATE TABLE IF NOT EXISTS llm_models (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    model_key VARCHAR(255) NOT NULL,
    provider_key VARCHAR(255) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL DEFAULT (''),
    capabilities JSON NOT NULL DEFAULT (JSON_OBJECT()),
    context_window BIGINT,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE(tenant_id, model_key)
);

CREATE INDEX idx_llm_models_tenant ON llm_models(tenant_id);
CREATE INDEX idx_llm_models_provider ON llm_models(provider_key);
CREATE INDEX idx_llm_models_enabled ON llm_models(enabled);

CREATE TABLE IF NOT EXISTS llm_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_key VARCHAR(255) NOT NULL,
    context_key VARCHAR(255) NOT NULL DEFAULT (''),
    scene_key VARCHAR(255) NOT NULL DEFAULT (''),
    task_name VARCHAR(255) NOT NULL DEFAULT (''),
    display_name VARCHAR(255) NOT NULL DEFAULT (''),
    description TEXT NOT NULL DEFAULT (''),
    owner_context TEXT NOT NULL DEFAULT (''),
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE(tenant_id, task_key)
);

CREATE INDEX idx_llm_tasks_tenant ON llm_tasks(tenant_id);
CREATE INDEX idx_llm_tasks_context ON llm_tasks(context_key);
CREATE INDEX idx_llm_tasks_enabled ON llm_tasks(enabled);

CREATE TABLE IF NOT EXISTS llm_routing_policies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    route_key VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL DEFAULT (''),
    strategy TEXT NOT NULL DEFAULT ('priority'),
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE(tenant_id, route_key)
);

CREATE INDEX idx_llm_routing_policies_tenant ON llm_routing_policies(tenant_id);
CREATE INDEX idx_llm_routing_policies_enabled ON llm_routing_policies(enabled);

CREATE TABLE IF NOT EXISTS llm_routing_policy_entries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    policy_id BIGINT NOT NULL,
    model_key VARCHAR(255) NOT NULL,
    priority BIGINT NOT NULL DEFAULT 100,
    temperature DOUBLE PRECISION DEFAULT 0.1,
    timeout_seconds DOUBLE PRECISION DEFAULT 120,
    max_retries BIGINT NOT NULL DEFAULT 0,
    response_format VARCHAR(255) NOT NULL DEFAULT ('text'),
    extra_body JSON NOT NULL DEFAULT (JSON_OBJECT()),
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX idx_llm_routing_entries_tenant ON llm_routing_policy_entries(tenant_id);
CREATE INDEX idx_llm_routing_entries_policy ON llm_routing_policy_entries(policy_id);
CREATE INDEX idx_llm_routing_entries_model ON llm_routing_policy_entries(model_key);
CREATE INDEX idx_llm_routing_entries_enabled ON llm_routing_policy_entries(enabled);

CREATE TABLE IF NOT EXISTS llm_call_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_key VARCHAR(255) NOT NULL,
    route_key VARCHAR(255) NOT NULL DEFAULT (''),
    policy_id BIGINT,
    entry_id BIGINT,
    provider_key VARCHAR(255) NOT NULL DEFAULT (''),
    model_key VARCHAR(255) NOT NULL DEFAULT (''),
    model_name VARCHAR(255) NOT NULL DEFAULT (''),
    status VARCHAR(255) NOT NULL,
    is_fallback TINYINT(1) NOT NULL DEFAULT 0,
    elapsed_ms BIGINT DEFAULT 0,
    prompt_tokens BIGINT DEFAULT 0,
    completion_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    error_code VARCHAR(255) NOT NULL DEFAULT (''),
    error_message TEXT NOT NULL DEFAULT (''),
    request_id TEXT NOT NULL DEFAULT (''),
    correlation_id TEXT NOT NULL DEFAULT (''),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX idx_llm_call_logs_tenant ON llm_call_logs(tenant_id);
CREATE INDEX idx_llm_call_logs_task ON llm_call_logs(task_key);
CREATE INDEX idx_llm_call_logs_created ON llm_call_logs(create_time);

CREATE TABLE IF NOT EXISTS ai_applications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    app_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    app_type VARCHAR(255) NOT NULL DEFAULT ('single_turn_generation'),
    status VARCHAR(255) NOT NULL DEFAULT ('draft'),
    endpoint_slug VARCHAR(255) NOT NULL DEFAULT (''),
    system_prompt TEXT NOT NULL DEFAULT (''),
    developer_prompt TEXT NOT NULL DEFAULT (''),
    user_prompt_template TEXT NOT NULL DEFAULT (''),
    variables_schema_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    output_schema_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    model_preferences_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    auth_policy_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    quota_policy_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    trace_policy_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    runtime_config_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    published_time TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, app_key, deleted)
);

CREATE INDEX idx_ai_applications_tenant ON ai_applications(tenant_id);
CREATE INDEX idx_ai_applications_status ON ai_applications(tenant_id, status, deleted);

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

CREATE TABLE IF NOT EXISTS tenant_ai_quotas (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    max_applications BIGINT NOT NULL DEFAULT 5,
    max_capabilities BIGINT NOT NULL DEFAULT 50,
    max_assets BIGINT NOT NULL DEFAULT 200,
    daily_run_limit BIGINT NOT NULL DEFAULT 1000,
    monthly_token_limit BIGINT NOT NULL DEFAULT 1000000,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id)
);

CREATE INDEX idx_tenant_ai_quotas_tenant ON tenant_ai_quotas(tenant_id);

CREATE TABLE IF NOT EXISTS prompt_runtime_traces (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    trace_id VARCHAR(255) NOT NULL,
    caller_type VARCHAR(255) NOT NULL DEFAULT ('studio_draft'),
    caller_key VARCHAR(255) NOT NULL DEFAULT (''),
    app_key VARCHAR(255) NOT NULL DEFAULT (''),
    app_version VARCHAR(255) NOT NULL DEFAULT (''),
    route_key VARCHAR(255) NOT NULL DEFAULT (''),
    model_key VARCHAR(255) NOT NULL DEFAULT (''),
    provider_key VARCHAR(255) NOT NULL DEFAULT (''),
    status VARCHAR(255) NOT NULL,
    input_variables_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    rendered_messages_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    rendered_prompt TEXT NOT NULL DEFAULT (''),
    answer_text TEXT NOT NULL DEFAULT (''),
    usage_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    elapsed_ms BIGINT NOT NULL DEFAULT 0,
    error_code VARCHAR(255) NOT NULL DEFAULT (''),
    error_message TEXT NOT NULL DEFAULT (''),
    request_id TEXT NOT NULL DEFAULT (''),
    correlation_id TEXT NOT NULL DEFAULT (''),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, trace_id)
);

CREATE INDEX idx_prompt_runtime_traces_tenant ON prompt_runtime_traces(tenant_id);
CREATE INDEX idx_prompt_runtime_traces_caller ON prompt_runtime_traces(tenant_id, caller_type, caller_key);
CREATE INDEX idx_prompt_runtime_traces_created ON prompt_runtime_traces(create_time);
