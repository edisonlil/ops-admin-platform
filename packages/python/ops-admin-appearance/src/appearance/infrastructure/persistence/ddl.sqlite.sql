CREATE TABLE IF NOT EXISTS appearance_themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'published',
    version INTEGER NOT NULL DEFAULT 1,
    preset_id TEXT NOT NULL DEFAULT 'default',
    token_overrides_json TEXT NOT NULL DEFAULT '{}',
    layout_overrides_json TEXT NOT NULL DEFAULT '{}',
    project_overrides_json TEXT NOT NULL DEFAULT '{}',
    skin_class TEXT NOT NULL DEFAULT '',
    draft_preset_id TEXT NOT NULL DEFAULT 'default',
    draft_token_overrides_json TEXT NOT NULL DEFAULT '{}',
    draft_layout_overrides_json TEXT NOT NULL DEFAULT '{}',
    draft_project_overrides_json TEXT NOT NULL DEFAULT '{}',
    draft_skin_class TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appearance_theme_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type TEXT NOT NULL,
    scope_id INTEGER NOT NULL,
    theme_id INTEGER NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 1,
    assigned_by TEXT NOT NULL DEFAULT '',
    assigned_at TEXT NOT NULL,
    UNIQUE (scope_type, scope_id, is_default),
    FOREIGN KEY (theme_id) REFERENCES appearance_themes(id)
);

CREATE TABLE IF NOT EXISTS appearance_theme_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_id INTEGER NOT NULL,
    revision_no INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (theme_id, revision_no),
    FOREIGN KEY (theme_id) REFERENCES appearance_themes(id)
);

CREATE TABLE IF NOT EXISTS appearance_platform_branding (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    platform_name TEXT NOT NULL DEFAULT 'fg-agent',
    logo_url TEXT NOT NULL DEFAULT '',
    platform_name_font_size INTEGER NOT NULL DEFAULT 20,
    updated_by TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_appearance_themes_tenant ON appearance_themes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_appearance_assignments_scope ON appearance_theme_assignments(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_appearance_revisions_theme ON appearance_theme_revisions(theme_id);
