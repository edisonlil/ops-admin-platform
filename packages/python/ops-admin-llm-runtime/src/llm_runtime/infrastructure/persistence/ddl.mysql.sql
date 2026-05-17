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
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
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
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
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
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
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
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
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
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
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
    owner_department_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX idx_llm_call_logs_tenant ON llm_call_logs(tenant_id);
CREATE INDEX idx_llm_call_logs_task ON llm_call_logs(task_key);
CREATE INDEX idx_llm_call_logs_created ON llm_call_logs(create_time);
CREATE INDEX idx_llm_call_logs_creator ON llm_call_logs(tenant_id, creator_id, deleted);
CREATE INDEX idx_llm_call_logs_owner_department ON llm_call_logs(tenant_id, owner_department_id, deleted);
