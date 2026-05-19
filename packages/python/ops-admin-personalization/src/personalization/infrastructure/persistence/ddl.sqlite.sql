CREATE TABLE IF NOT EXISTS personalization_table_column_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    view_key TEXT NOT NULL,
    visible_column_keys_json TEXT NOT NULL DEFAULT '[]',
    column_order_keys_json TEXT NOT NULL DEFAULT '[]',
    settings_json TEXT NOT NULL DEFAULT '{}',
    active_marker INTEGER DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, user_id, view_key, active_marker)
);

CREATE INDEX IF NOT EXISTS idx_personalization_table_columns_user ON personalization_table_column_preferences(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_personalization_table_columns_view ON personalization_table_column_preferences(view_key);
CREATE INDEX IF NOT EXISTS idx_personalization_table_columns_deleted ON personalization_table_column_preferences(deleted);
