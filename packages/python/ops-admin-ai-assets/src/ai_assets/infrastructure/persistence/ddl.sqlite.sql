CREATE TABLE IF NOT EXISTS prompt_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    prompt_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'general',
    tags_json TEXT NOT NULL DEFAULT '[]',
    owner_context TEXT NOT NULL DEFAULT 'general',
    visibility TEXT NOT NULL DEFAULT 'tenant',
    status TEXT NOT NULL DEFAULT 'draft',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, prompt_key, deleted)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    prompt_id INTEGER NOT NULL,
    version TEXT NOT NULL,
    system_prompt TEXT NOT NULL DEFAULT '',
    developer_prompt TEXT NOT NULL DEFAULT '',
    user_prompt_template TEXT NOT NULL DEFAULT '',
    variables_schema_json TEXT NOT NULL DEFAULT '{}',
    output_schema_json TEXT NOT NULL DEFAULT '{}',
    example_inputs_json TEXT NOT NULL DEFAULT '[]',
    example_outputs_json TEXT NOT NULL DEFAULT '[]',
    model_preferences_json TEXT NOT NULL DEFAULT '{}',
    render_engine TEXT NOT NULL DEFAULT 'simple',
    status TEXT NOT NULL DEFAULT 'draft',
    published_time TEXT DEFAULT NULL,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, prompt_id, version, deleted)
);

CREATE TABLE IF NOT EXISTS prompt_task_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    contract_key TEXT NOT NULL,
    owner_context TEXT NOT NULL DEFAULT 'general',
    task_kind TEXT NOT NULL DEFAULT 'single_call',
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    llm_task_key TEXT NOT NULL,
    input_schema_json TEXT NOT NULL DEFAULT '{}',
    output_schema_json TEXT NOT NULL DEFAULT '{}',
    required_capabilities_json TEXT NOT NULL DEFAULT '[]',
    allowed_prompt_scopes_json TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, contract_key, deleted)
);

CREATE TABLE IF NOT EXISTS prompt_task_bindings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    contract_id INTEGER NOT NULL,
    prompt_id INTEGER NOT NULL,
    prompt_version_id INTEGER NOT NULL,
    binding_name TEXT NOT NULL DEFAULT '',
    priority INTEGER NOT NULL DEFAULT 100,
    environment TEXT NOT NULL DEFAULT 'dev',
    enabled INTEGER NOT NULL DEFAULT 1,
    effective_from TEXT DEFAULT NULL,
    effective_to TEXT DEFAULT NULL,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS prompt_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    contract_key TEXT NOT NULL,
    prompt_id INTEGER DEFAULT NULL,
    prompt_version_id INTEGER DEFAULT NULL,
    llm_task_key TEXT NOT NULL DEFAULT '',
    input_json TEXT NOT NULL DEFAULT '{}',
    rendered_messages_json TEXT NOT NULL DEFAULT '[]',
    output_text TEXT NOT NULL DEFAULT '',
    output_json TEXT DEFAULT NULL,
    schema_valid INTEGER NOT NULL DEFAULT 0,
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'succeeded',
    elapsed_ms INTEGER NOT NULL DEFAULT 0,
    request_id TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_prompt_assets_tenant_status ON prompt_assets(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_assets_tenant_owner ON prompt_assets(tenant_id, owner_context, category, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt ON prompt_versions(tenant_id, prompt_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_contracts_tenant_enabled ON prompt_task_contracts(tenant_id, enabled, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_bindings_contract ON prompt_task_bindings(tenant_id, contract_id, enabled, priority, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_bindings_version ON prompt_task_bindings(tenant_id, prompt_version_id, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_runs_tenant_contract ON prompt_runs(tenant_id, contract_key, create_time);
