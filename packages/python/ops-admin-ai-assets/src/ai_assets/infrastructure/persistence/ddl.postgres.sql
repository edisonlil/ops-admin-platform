CREATE TABLE IF NOT EXISTS prompt_assets (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    prompt_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, prompt_key, deleted)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    prompt_id BIGINT NOT NULL,
    version TEXT NOT NULL,
    system_prompt TEXT NOT NULL DEFAULT '',
    developer_prompt TEXT NOT NULL DEFAULT '',
    user_prompt_template TEXT NOT NULL DEFAULT '',
    variables_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    example_inputs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    example_outputs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_preferences_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    render_engine TEXT NOT NULL DEFAULT 'simple',
    status TEXT NOT NULL DEFAULT 'draft',
    published_time TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, prompt_id, version, deleted)
);

CREATE TABLE IF NOT EXISTS prompt_task_contracts (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    contract_key TEXT NOT NULL,
    owner_context TEXT NOT NULL DEFAULT 'general',
    task_kind TEXT NOT NULL DEFAULT 'single_call',
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    llm_task_key TEXT NOT NULL,
    input_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    required_capabilities_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_prompt_scopes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, contract_key, deleted)
);

CREATE TABLE IF NOT EXISTS prompt_task_bindings (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    contract_id BIGINT NOT NULL,
    prompt_id BIGINT NOT NULL,
    prompt_version_id BIGINT NOT NULL,
    binding_name TEXT NOT NULL DEFAULT '',
    priority BIGINT NOT NULL DEFAULT 100,
    environment TEXT NOT NULL DEFAULT 'dev',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from TEXT DEFAULT NULL,
    effective_to TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS prompt_runs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    contract_key TEXT NOT NULL,
    prompt_id BIGINT DEFAULT NULL,
    prompt_version_id BIGINT DEFAULT NULL,
    llm_task_key TEXT NOT NULL DEFAULT '',
    input_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    rendered_messages_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_text TEXT NOT NULL DEFAULT '',
    output_json JSONB DEFAULT NULL,
    schema_valid BOOLEAN NOT NULL DEFAULT FALSE,
    validation_errors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'succeeded',
    elapsed_ms BIGINT NOT NULL DEFAULT 0,
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

CREATE INDEX IF NOT EXISTS idx_prompt_assets_tenant_status ON prompt_assets(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt ON prompt_versions(tenant_id, prompt_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_contracts_tenant_enabled ON prompt_task_contracts(tenant_id, enabled, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_bindings_contract ON prompt_task_bindings(tenant_id, contract_id, enabled, priority, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_bindings_version ON prompt_task_bindings(tenant_id, prompt_version_id, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_runs_tenant_contract ON prompt_runs(tenant_id, contract_key, create_time);
