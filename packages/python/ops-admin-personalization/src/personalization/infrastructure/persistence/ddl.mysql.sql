CREATE TABLE IF NOT EXISTS personalization_table_column_preferences (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    view_key VARCHAR(160) NOT NULL,
    visible_column_keys_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    column_order_keys_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    settings_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    active_marker BIGINT DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, user_id, view_key, active_marker)
);

CREATE INDEX idx_personalization_table_columns_user ON personalization_table_column_preferences(tenant_id, user_id);
CREATE INDEX idx_personalization_table_columns_view ON personalization_table_column_preferences(view_key);
CREATE INDEX idx_personalization_table_columns_deleted ON personalization_table_column_preferences(deleted);
