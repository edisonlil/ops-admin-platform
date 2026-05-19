CREATE TABLE IF NOT EXISTS personalization_table_column_preferences (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    view_key TEXT NOT NULL,
    visible_column_keys_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    column_order_keys_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, user_id, view_key, active_marker)
);

CREATE INDEX IF NOT EXISTS idx_personalization_table_columns_user ON personalization_table_column_preferences(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_personalization_table_columns_view ON personalization_table_column_preferences(view_key);
CREATE INDEX IF NOT EXISTS idx_personalization_table_columns_deleted ON personalization_table_column_preferences(deleted);
