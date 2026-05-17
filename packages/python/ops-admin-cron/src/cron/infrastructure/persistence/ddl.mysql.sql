CREATE TABLE IF NOT EXISTS cron_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    status VARCHAR(255) NOT NULL DEFAULT ('draft'),
    execution_target TEXT NOT NULL,
    payload_schema_version BIGINT NOT NULL DEFAULT 1,
    default_payload_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    concurrency_policy VARCHAR(255) NOT NULL DEFAULT ('forbid'),
    timeout_seconds BIGINT NOT NULL DEFAULT 300,
    max_attempts BIGINT NOT NULL DEFAULT 1,
    retry_delay_seconds BIGINT NOT NULL DEFAULT 0,
    retry_backoff_multiplier DOUBLE PRECISION NOT NULL DEFAULT 1,
    misfire_policy VARCHAR(255) NOT NULL DEFAULT ('skip'),
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, task_key)
);

CREATE TABLE IF NOT EXISTS cron_schedules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_id BIGINT NOT NULL,
    trigger_type VARCHAR(255) NOT NULL DEFAULT ('cron'),
    trigger_expression TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT ('UTC'),
    start_time DATETIME(6) DEFAULT NULL,
    end_time DATETIME(6) DEFAULT NULL,
    next_fire_time DATETIME(6) DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, task_id)
);

CREATE TABLE IF NOT EXISTS cron_runs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_id BIGINT NOT NULL,
    schedule_id BIGINT DEFAULT NULL,
    fire_time DATETIME(6) NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT ('pending'),
    trigger_source VARCHAR(255) NOT NULL DEFAULT ('manual'),
    idempotency_key VARCHAR(255) NOT NULL,
    payload_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    result_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    started_time DATETIME(6) DEFAULT NULL,
    finished_time DATETIME(6) DEFAULT NULL,
    failure_code VARCHAR(255) NOT NULL DEFAULT (''),
    failure_message TEXT NOT NULL DEFAULT (''),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, task_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS cron_attempts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    run_id BIGINT NOT NULL,
    attempt_number BIGINT NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT ('running'),
    worker_id VARCHAR(255) NOT NULL DEFAULT (''),
    started_time DATETIME(6) NOT NULL,
    finished_time DATETIME(6) DEFAULT NULL,
    error_code VARCHAR(255) NOT NULL DEFAULT (''),
    error_message TEXT NOT NULL DEFAULT (''),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, run_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS cron_external_bindings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_id BIGINT NOT NULL,
    scheduler_type VARCHAR(255) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT ('active'),
    metadata_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    create_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, scheduler_type, external_id)
);

CREATE INDEX idx_cron_tasks_tenant ON cron_tasks(tenant_id, status);
CREATE INDEX idx_cron_schedules_task ON cron_schedules(task_id);
CREATE INDEX idx_cron_runs_task ON cron_runs(tenant_id, task_id, fire_time);
CREATE INDEX idx_cron_runs_status ON cron_runs(tenant_id, status);
CREATE INDEX idx_cron_attempts_run ON cron_attempts(run_id);
CREATE INDEX idx_cron_bindings_task ON cron_external_bindings(tenant_id, task_id);
