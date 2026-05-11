CREATE TABLE IF NOT EXISTS message_intents (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    message_type TEXT NOT NULL DEFAULT 'system',
    priority TEXT NOT NULL DEFAULT 'normal',
    template_id BIGINT DEFAULT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    sender_user_id BIGINT DEFAULT NULL,
    sender_name TEXT NOT NULL DEFAULT '',
    target_scope TEXT NOT NULL DEFAULT 'users',
    target_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    scheduled_time TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_templates (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    template_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    channels_json JSONB NOT NULL DEFAULT '["in_app"]'::jsonb,
    title_template TEXT NOT NULL,
    content_template TEXT NOT NULL,
    variables_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, template_key)
);

CREATE TABLE IF NOT EXISTS message_recipients (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    message_id BIGINT NOT NULL,
    recipient_user_id BIGINT NOT NULL,
    recipient_name TEXT NOT NULL DEFAULT '',
    read_status TEXT NOT NULL DEFAULT 'unread',
    read_time TEXT DEFAULT NULL,
    archive_status TEXT NOT NULL DEFAULT 'active',
    pin_status TEXT NOT NULL DEFAULT 'normal',
    delivery_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, message_id, recipient_user_id)
);

CREATE TABLE IF NOT EXISTS message_channel_accounts (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    channel TEXT NOT NULL,
    name TEXT NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    secret_ref TEXT NOT NULL DEFAULT '',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_channel_deliveries (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    message_id BIGINT NOT NULL,
    recipient_id BIGINT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'in_app',
    channel_account_id BIGINT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    external_message_id TEXT NOT NULL DEFAULT '',
    request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    failure_code TEXT NOT NULL DEFAULT '',
    failure_message TEXT NOT NULL DEFAULT '',
    attempt_count BIGINT NOT NULL DEFAULT 1,
    next_retry_time TEXT DEFAULT NULL,
    sent_time TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_user_preferences (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    user_id BIGINT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'system',
    channels_json JSONB NOT NULL DEFAULT '["in_app"]'::jsonb,
    quiet_hours_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, user_id, message_type)
);

CREATE INDEX IF NOT EXISTS idx_message_intents_tenant ON message_intents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_message_intents_status ON message_intents(status);
CREATE INDEX IF NOT EXISTS idx_message_templates_tenant ON message_templates(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_message_recipients_user ON message_recipients(tenant_id, recipient_user_id, read_status);
CREATE INDEX IF NOT EXISTS idx_message_recipients_message ON message_recipients(message_id);
CREATE INDEX IF NOT EXISTS idx_message_channel_accounts_tenant ON message_channel_accounts(tenant_id, channel);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_message ON message_channel_deliveries(message_id);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_recipient ON message_channel_deliveries(recipient_id);
CREATE INDEX IF NOT EXISTS idx_message_preferences_user ON message_user_preferences(tenant_id, user_id);
