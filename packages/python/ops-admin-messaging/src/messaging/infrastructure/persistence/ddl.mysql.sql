CREATE TABLE IF NOT EXISTS message_intents (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    message_type VARCHAR(255) NOT NULL DEFAULT ('system'),
    priority TEXT NOT NULL DEFAULT ('normal'),
    template_id BIGINT DEFAULT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    payload_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    sender_user_id BIGINT DEFAULT NULL,
    sender_name VARCHAR(255) NOT NULL DEFAULT (''),
    target_scope VARCHAR(255) NOT NULL DEFAULT ('users'),
    target_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    scheduled_time TEXT DEFAULT NULL,
    status VARCHAR(255) NOT NULL DEFAULT ('queued'),
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    template_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    channels_json JSON NOT NULL DEFAULT (CAST('["in_app"]' AS JSON)),
    title_template TEXT NOT NULL,
    content_template TEXT NOT NULL,
    variables_schema_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    status VARCHAR(255) NOT NULL DEFAULT ('draft'),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, template_key)
);

CREATE TABLE IF NOT EXISTS message_recipients (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    message_id BIGINT NOT NULL,
    recipient_user_id BIGINT NOT NULL,
    recipient_name VARCHAR(255) NOT NULL DEFAULT (''),
    read_status VARCHAR(255) NOT NULL DEFAULT ('unread'),
    read_time TEXT DEFAULT NULL,
    archive_status VARCHAR(255) NOT NULL DEFAULT ('active'),
    pin_status VARCHAR(255) NOT NULL DEFAULT ('normal'),
    delivery_summary_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, message_id, recipient_user_id)
);

CREATE TABLE IF NOT EXISTS message_channel_accounts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    channel VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    config_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    secret_ref TEXT NOT NULL DEFAULT (''),
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_channel_deliveries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    message_id BIGINT NOT NULL,
    recipient_id BIGINT NOT NULL,
    channel VARCHAR(255) NOT NULL DEFAULT ('in_app'),
    channel_account_id BIGINT DEFAULT NULL,
    status VARCHAR(255) NOT NULL DEFAULT ('sent'),
    external_message_id VARCHAR(255) NOT NULL DEFAULT (''),
    request_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    response_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    failure_code VARCHAR(255) NOT NULL DEFAULT (''),
    failure_message TEXT NOT NULL DEFAULT (''),
    attempt_count BIGINT NOT NULL DEFAULT 1,
    next_retry_time TEXT DEFAULT NULL,
    sent_time TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_user_preferences (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    user_id BIGINT NOT NULL,
    message_type VARCHAR(255) NOT NULL DEFAULT ('system'),
    channels_json JSON NOT NULL DEFAULT (CAST('["in_app"]' AS JSON)),
    quiet_hours_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, user_id, message_type)
);

CREATE INDEX idx_message_intents_tenant ON message_intents(tenant_id);
CREATE INDEX idx_message_intents_status ON message_intents(status);
CREATE INDEX idx_message_templates_tenant ON message_templates(tenant_id, status);
CREATE INDEX idx_message_recipients_user ON message_recipients(tenant_id, recipient_user_id, read_status);
CREATE INDEX idx_message_recipients_message ON message_recipients(message_id);
CREATE INDEX idx_message_channel_accounts_tenant ON message_channel_accounts(tenant_id, channel);
CREATE INDEX idx_message_deliveries_message ON message_channel_deliveries(message_id);
CREATE INDEX idx_message_deliveries_recipient ON message_channel_deliveries(recipient_id);
CREATE INDEX idx_message_preferences_user ON message_user_preferences(tenant_id, user_id);
