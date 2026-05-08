CREATE TABLE IF NOT EXISTS llm_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    provider TEXT NOT NULL DEFAULT 'minimax',
    model TEXT DEFAULT '',
    base_url TEXT DEFAULT '',
    api_key TEXT DEFAULT '',
    command TEXT DEFAULT '',
    timeout_seconds REAL DEFAULT 120,
    temperature REAL DEFAULT 0.1,
    extra_body TEXT DEFAULT '{}',
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_llm_configs_active ON llm_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_llm_configs_tenant ON llm_configs(tenant_id);

CREATE TABLE IF NOT EXISTS llm_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    provider_key TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    base_url TEXT NOT NULL DEFAULT '',
    api_key TEXT NOT NULL DEFAULT '',
    auth_type TEXT NOT NULL DEFAULT 'bearer',
    extra_headers TEXT NOT NULL DEFAULT '{}',
    extra_body TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
    ,UNIQUE(tenant_id, provider_key)
);

CREATE INDEX IF NOT EXISTS idx_llm_providers_enabled ON llm_providers(enabled);
CREATE INDEX IF NOT EXISTS idx_llm_providers_tenant ON llm_providers(tenant_id);

CREATE TABLE IF NOT EXISTS llm_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    model_key TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    model_name TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    capabilities TEXT NOT NULL DEFAULT '{}',
    context_window INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
    ,UNIQUE(tenant_id, model_key)
);

CREATE INDEX IF NOT EXISTS idx_llm_models_tenant ON llm_models(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_models_provider ON llm_models(provider_key);
CREATE INDEX IF NOT EXISTS idx_llm_models_enabled ON llm_models(enabled);

CREATE TABLE IF NOT EXISTS llm_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    task_key TEXT NOT NULL,
    context_key TEXT NOT NULL DEFAULT '',
    scene_key TEXT NOT NULL DEFAULT '',
    task_name TEXT NOT NULL DEFAULT '',
    display_name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    owner_context TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
    ,UNIQUE(tenant_id, task_key)
);

CREATE INDEX IF NOT EXISTS idx_llm_tasks_tenant ON llm_tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_tasks_context ON llm_tasks(context_key);
CREATE INDEX IF NOT EXISTS idx_llm_tasks_enabled ON llm_tasks(enabled);

CREATE TABLE IF NOT EXISTS llm_routing_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    route_key TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT 'priority',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
    ,UNIQUE(tenant_id, route_key)
);

CREATE INDEX IF NOT EXISTS idx_llm_routing_policies_tenant ON llm_routing_policies(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_routing_policies_enabled ON llm_routing_policies(enabled);

CREATE TABLE IF NOT EXISTS llm_routing_policy_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    policy_id INTEGER NOT NULL,
    model_key TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    temperature REAL DEFAULT 0.1,
    timeout_seconds REAL DEFAULT 120,
    max_retries INTEGER NOT NULL DEFAULT 0,
    response_format TEXT NOT NULL DEFAULT 'text',
    extra_body TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_llm_routing_entries_tenant ON llm_routing_policy_entries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_routing_entries_policy ON llm_routing_policy_entries(policy_id);
CREATE INDEX IF NOT EXISTS idx_llm_routing_entries_model ON llm_routing_policy_entries(model_key);
CREATE INDEX IF NOT EXISTS idx_llm_routing_entries_enabled ON llm_routing_policy_entries(enabled);

CREATE TABLE IF NOT EXISTS llm_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    task_key TEXT NOT NULL,
    route_key TEXT NOT NULL DEFAULT '',
    policy_id INTEGER,
    entry_id INTEGER,
    provider_key TEXT NOT NULL DEFAULT '',
    model_key TEXT NOT NULL DEFAULT '',
    model_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    is_fallback INTEGER NOT NULL DEFAULT 0,
    elapsed_ms INTEGER DEFAULT 0,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    request_id TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_llm_call_logs_tenant ON llm_call_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_task ON llm_call_logs(task_key);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_created ON llm_call_logs(created_at);
