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

CREATE TABLE IF NOT EXISTS ai_application_agent_conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    conversation_key VARCHAR(255) NOT NULL,
    app_key VARCHAR(255) NOT NULL,
    title TEXT NOT NULL DEFAULT (''),
    status VARCHAR(255) NOT NULL DEFAULT ('active'),
    last_message_role VARCHAR(255) NOT NULL DEFAULT (''),
    last_message_preview TEXT NOT NULL DEFAULT (''),
    last_message_time TEXT DEFAULT NULL,
    metadata_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, conversation_key, deleted)
);

CREATE INDEX idx_ai_app_agent_conversations_tenant_app
    ON ai_application_agent_conversations(tenant_id, app_key, deleted, update_time);

CREATE TABLE IF NOT EXISTS ai_application_agent_messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    conversation_key VARCHAR(255) NOT NULL,
    message_key VARCHAR(255) NOT NULL,
    app_key VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    content TEXT NOT NULL DEFAULT (''),
    content_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    status VARCHAR(255) NOT NULL DEFAULT ('completed'),
    trace_id VARCHAR(255) NOT NULL DEFAULT (''),
    error_code VARCHAR(255) NOT NULL DEFAULT (''),
    error_message TEXT NOT NULL DEFAULT (''),
    metadata_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, message_key)
);

CREATE INDEX idx_ai_app_agent_messages_conversation
    ON ai_application_agent_messages(tenant_id, conversation_key, deleted, id);
CREATE INDEX idx_ai_app_agent_messages_trace
    ON ai_application_agent_messages(tenant_id, trace_id);
