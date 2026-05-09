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
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS appearance_theme_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    scope_type TEXT NOT NULL,
    scope_id INTEGER NOT NULL,
    theme_id INTEGER NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, scope_type, scope_id, is_default),
    FOREIGN KEY (theme_id) REFERENCES appearance_themes(id)
);

CREATE TABLE IF NOT EXISTS appearance_theme_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    theme_id INTEGER NOT NULL,
    revision_no INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, theme_id, revision_no),
    FOREIGN KEY (theme_id) REFERENCES appearance_themes(id)
);

CREATE TABLE IF NOT EXISTS appearance_platform_branding (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    tenant_id INTEGER NOT NULL,
    platform_name TEXT NOT NULL DEFAULT 'fg-agent',
    logo_url TEXT NOT NULL DEFAULT '',
    platform_name_font_size INTEGER NOT NULL DEFAULT 20,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_appearance_themes_tenant ON appearance_themes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_appearance_themes_deleted ON appearance_themes(deleted);
CREATE INDEX IF NOT EXISTS idx_appearance_assignments_scope ON appearance_theme_assignments(tenant_id, scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_appearance_revisions_theme ON appearance_theme_revisions(tenant_id, theme_id);

