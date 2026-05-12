CREATE TABLE IF NOT EXISTS cron_tasks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    execution_target TEXT NOT NULL,
    payload_schema_version BIGINT NOT NULL DEFAULT 1,
    default_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    concurrency_policy TEXT NOT NULL DEFAULT 'forbid',
    timeout_seconds BIGINT NOT NULL DEFAULT 300,
    max_attempts BIGINT NOT NULL DEFAULT 1,
    retry_delay_seconds BIGINT NOT NULL DEFAULT 0,
    retry_backoff_multiplier DOUBLE PRECISION NOT NULL DEFAULT 1,
    misfire_policy TEXT NOT NULL DEFAULT 'skip',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, task_key)
);

CREATE TABLE IF NOT EXISTS cron_schedules (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_id BIGINT NOT NULL,
    trigger_type TEXT NOT NULL DEFAULT 'cron',
    trigger_expression TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    start_time TEXT DEFAULT NULL,
    end_time TEXT DEFAULT NULL,
    next_fire_time TEXT DEFAULT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, task_id)
);

CREATE TABLE IF NOT EXISTS cron_runs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_id BIGINT NOT NULL,
    schedule_id BIGINT DEFAULT NULL,
    fire_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    trigger_source TEXT NOT NULL DEFAULT 'manual',
    idempotency_key TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_time TEXT DEFAULT NULL,
    finished_time TEXT DEFAULT NULL,
    failure_code TEXT NOT NULL DEFAULT '',
    failure_message TEXT NOT NULL DEFAULT '',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, task_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS cron_attempts (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    run_id BIGINT NOT NULL,
    attempt_number BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    worker_id TEXT NOT NULL DEFAULT '',
    started_time TEXT NOT NULL,
    finished_time TEXT DEFAULT NULL,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, run_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS cron_external_bindings (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL DEFAULT 1,
    task_id BIGINT NOT NULL,
    scheduler_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator TEXT DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor TEXT DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, scheduler_type, external_id)
);

CREATE INDEX IF NOT EXISTS idx_cron_tasks_tenant ON cron_tasks(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_cron_schedules_task ON cron_schedules(task_id);
CREATE INDEX IF NOT EXISTS idx_cron_runs_task ON cron_runs(tenant_id, task_id, fire_time);
CREATE INDEX IF NOT EXISTS idx_cron_runs_status ON cron_runs(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_cron_attempts_run ON cron_attempts(run_id);
CREATE INDEX IF NOT EXISTS idx_cron_bindings_task ON cron_external_bindings(tenant_id, task_id);
