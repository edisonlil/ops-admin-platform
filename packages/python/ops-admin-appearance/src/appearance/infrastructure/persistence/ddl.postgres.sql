CREATE TABLE IF NOT EXISTS appearance_themes (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'published',
    version BIGINT NOT NULL DEFAULT 1,
    preset_id TEXT NOT NULL DEFAULT 'default',
    token_overrides_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    layout_overrides_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    project_overrides_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    skin_class TEXT NOT NULL DEFAULT '',
    draft_preset_id TEXT NOT NULL DEFAULT 'default',
    draft_token_overrides_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    draft_layout_overrides_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    draft_project_overrides_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    draft_skin_class TEXT NOT NULL DEFAULT '',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS appearance_theme_assignments (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    scope_type TEXT NOT NULL,
    scope_id BIGINT NOT NULL,
    theme_id BIGINT NOT NULL REFERENCES appearance_themes(id),
    is_default BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, scope_type, scope_id, is_default)
);

CREATE TABLE IF NOT EXISTS appearance_theme_revisions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    theme_id BIGINT NOT NULL REFERENCES appearance_themes(id),
    revision_no BIGINT NOT NULL,
    snapshot_json JSONB NOT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, theme_id, revision_no)
);

CREATE TABLE IF NOT EXISTS appearance_platform_branding (
    id BIGINT PRIMARY KEY CHECK (id = 1),
    tenant_id BIGINT NOT NULL,
    platform_name TEXT NOT NULL DEFAULT 'fg-agent',
    logo_url TEXT NOT NULL DEFAULT '',
    platform_name_font_size BIGINT NOT NULL DEFAULT 20,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_appearance_themes_tenant ON appearance_themes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_appearance_themes_deleted ON appearance_themes(deleted);
CREATE INDEX IF NOT EXISTS idx_appearance_assignments_scope ON appearance_theme_assignments(tenant_id, scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_appearance_revisions_theme ON appearance_theme_revisions(tenant_id, theme_id);

