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
    created_by TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appearance_theme_assignments (
    id BIGSERIAL PRIMARY KEY,
    scope_type TEXT NOT NULL,
    scope_id BIGINT NOT NULL,
    theme_id BIGINT NOT NULL REFERENCES appearance_themes(id),
    is_default BOOLEAN NOT NULL DEFAULT TRUE,
    assigned_by TEXT NOT NULL DEFAULT '',
    assigned_at TEXT NOT NULL,
    UNIQUE (scope_type, scope_id, is_default)
);

CREATE TABLE IF NOT EXISTS appearance_theme_revisions (
    id BIGSERIAL PRIMARY KEY,
    theme_id BIGINT NOT NULL REFERENCES appearance_themes(id),
    revision_no BIGINT NOT NULL,
    snapshot_json JSONB NOT NULL,
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (theme_id, revision_no)
);

CREATE TABLE IF NOT EXISTS appearance_platform_branding (
    id BIGINT PRIMARY KEY CHECK (id = 1),
    platform_name TEXT NOT NULL DEFAULT 'fg-agent',
    logo_url TEXT NOT NULL DEFAULT '',
    platform_name_font_size BIGINT NOT NULL DEFAULT 20,
    updated_by TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_appearance_themes_tenant ON appearance_themes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_appearance_assignments_scope ON appearance_theme_assignments(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_appearance_revisions_theme ON appearance_theme_revisions(theme_id);
