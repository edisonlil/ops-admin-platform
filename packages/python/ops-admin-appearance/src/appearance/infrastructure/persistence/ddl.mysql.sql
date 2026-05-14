CREATE TABLE IF NOT EXISTS appearance_themes (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT ('published'),
    version BIGINT NOT NULL DEFAULT 1,
    preset_id VARCHAR(255) NOT NULL DEFAULT ('default'),
    token_overrides_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    layout_overrides_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    project_overrides_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    skin_class VARCHAR(255) NOT NULL DEFAULT (''),
    draft_preset_id VARCHAR(255) NOT NULL DEFAULT ('default'),
    draft_token_overrides_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    draft_layout_overrides_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    draft_project_overrides_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    draft_skin_class VARCHAR(255) NOT NULL DEFAULT (''),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS appearance_theme_assignments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    scope_type VARCHAR(255) NOT NULL,
    scope_id BIGINT NOT NULL,
    theme_id BIGINT NOT NULL REFERENCES appearance_themes(id),
    is_default TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, scope_type, scope_id, is_default)
);

CREATE TABLE IF NOT EXISTS appearance_theme_revisions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    theme_id BIGINT NOT NULL REFERENCES appearance_themes(id),
    revision_no BIGINT NOT NULL,
    snapshot_json JSON NOT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, theme_id, revision_no)
);

CREATE TABLE IF NOT EXISTS appearance_platform_branding (
    id BIGINT PRIMARY KEY CHECK (id = 1),
    tenant_id BIGINT NOT NULL,
    platform_name VARCHAR(255) NOT NULL DEFAULT ('fg-agent'),
    logo_url TEXT NOT NULL DEFAULT (''),
    platform_name_font_size BIGINT NOT NULL DEFAULT 20,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE INDEX idx_appearance_themes_tenant ON appearance_themes(tenant_id);
CREATE INDEX idx_appearance_themes_deleted ON appearance_themes(deleted);
CREATE INDEX idx_appearance_assignments_scope ON appearance_theme_assignments(tenant_id, scope_type, scope_id);
CREATE INDEX idx_appearance_revisions_theme ON appearance_theme_revisions(tenant_id, theme_id);

