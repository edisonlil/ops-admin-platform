CREATE TABLE IF NOT EXISTS message_intents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    message_type TEXT NOT NULL DEFAULT 'system',
    priority TEXT NOT NULL DEFAULT 'normal',
    template_id INTEGER DEFAULT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    sender_user_id INTEGER DEFAULT NULL,
    sender_name TEXT NOT NULL DEFAULT '',
    target_scope TEXT NOT NULL DEFAULT 'users',
    target_json TEXT NOT NULL DEFAULT '{}',
    scheduled_time TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    owner_user_id INTEGER DEFAULT NULL,
    owner_department_id INTEGER DEFAULT NULL,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    template_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    channels_json TEXT NOT NULL DEFAULT '["in_app"]',
    title_template TEXT NOT NULL,
    content_template TEXT NOT NULL,
    variables_schema_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, template_key)
);

CREATE TABLE IF NOT EXISTS message_recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    message_id INTEGER NOT NULL,
    recipient_user_id INTEGER NOT NULL,
    recipient_name TEXT NOT NULL DEFAULT '',
    read_status TEXT NOT NULL DEFAULT 'unread',
    read_time TEXT DEFAULT NULL,
    archive_status TEXT NOT NULL DEFAULT 'active',
    pin_status TEXT NOT NULL DEFAULT 'normal',
    delivery_summary_json TEXT NOT NULL DEFAULT '{}',
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, message_id, recipient_user_id)
);

CREATE TABLE IF NOT EXISTS message_channel_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    channel TEXT NOT NULL,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}',
    secret_ref TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    is_default INTEGER NOT NULL DEFAULT 0,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_channel_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    message_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    channel TEXT NOT NULL DEFAULT 'in_app',
    channel_account_id INTEGER DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    external_message_id TEXT NOT NULL DEFAULT '',
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    failure_code TEXT NOT NULL DEFAULT '',
    failure_message TEXT NOT NULL DEFAULT '',
    attempt_count INTEGER NOT NULL DEFAULT 1,
    next_retry_time TEXT DEFAULT NULL,
    sent_time TEXT DEFAULT NULL,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS message_user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    user_id INTEGER NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'system',
    channels_json TEXT NOT NULL DEFAULT '["in_app"]',
    quiet_hours_json TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    lock_version INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id INTEGER DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id INTEGER DEFAULT NULL,
    UNIQUE (tenant_id, user_id, message_type)
);

CREATE INDEX IF NOT EXISTS idx_message_intents_tenant ON message_intents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_message_intents_status ON message_intents(status);
CREATE INDEX IF NOT EXISTS idx_message_intents_owner_user ON message_intents(tenant_id, owner_user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_message_intents_owner_department ON message_intents(tenant_id, owner_department_id, deleted);
CREATE INDEX IF NOT EXISTS idx_message_templates_tenant ON message_templates(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_message_recipients_user ON message_recipients(tenant_id, recipient_user_id, read_status);
CREATE INDEX IF NOT EXISTS idx_message_recipients_message ON message_recipients(message_id);
CREATE INDEX IF NOT EXISTS idx_message_channel_accounts_tenant ON message_channel_accounts(tenant_id, channel);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_message ON message_channel_deliveries(message_id);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_recipient ON message_channel_deliveries(recipient_id);
CREATE INDEX IF NOT EXISTS idx_message_preferences_user ON message_user_preferences(tenant_id, user_id);
