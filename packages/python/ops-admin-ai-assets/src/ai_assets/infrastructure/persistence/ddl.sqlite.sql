CREATE TABLE IF NOT EXISTS prompt_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    prompt_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft',
    owner_user_id INTEGER DEFAULT NULL,
    owner_department_id INTEGER DEFAULT NULL,
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, prompt_key, active_marker)
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
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, prompt_id, version, active_marker)
);

CREATE TABLE IF NOT EXISTS skill_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    skill_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft',
    source_type TEXT NOT NULL DEFAULT 'upload',
    owner_user_id INTEGER DEFAULT NULL,
    owner_department_id INTEGER DEFAULT NULL,
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, skill_key, active_marker)
);

CREATE TABLE IF NOT EXISTS skill_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    version TEXT NOT NULL,
    manifest_json TEXT NOT NULL DEFAULT '{}',
    content_text TEXT NOT NULL DEFAULT '',
    content_sha256 TEXT NOT NULL DEFAULT '',
    entrypoint TEXT NOT NULL DEFAULT 'SKILL.md',
    runtime_constraints_json TEXT NOT NULL DEFAULT '{}',
    package_sha256 TEXT NOT NULL DEFAULT '',
    package_size INTEGER NOT NULL DEFAULT 0,
    package_data_base64 TEXT NOT NULL DEFAULT '',
    package_files_json TEXT NOT NULL DEFAULT '[]',
    validation_report_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    published_time TEXT DEFAULT NULL,
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, skill_id, version, active_marker)
);

CREATE INDEX IF NOT EXISTS idx_prompt_assets_tenant_status ON prompt_assets(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_assets_owner_user ON prompt_assets(tenant_id, owner_user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_assets_owner_department ON prompt_assets(tenant_id, owner_department_id, deleted);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt ON prompt_versions(tenant_id, prompt_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_skill_assets_tenant_status ON skill_assets(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_skill_assets_owner_user ON skill_assets(tenant_id, owner_user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_skill_assets_owner_department ON skill_assets(tenant_id, owner_department_id, deleted);
CREATE INDEX IF NOT EXISTS idx_skill_versions_skill ON skill_versions(tenant_id, skill_id, status, deleted);
