CREATE TABLE IF NOT EXISTS departments (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    parent_id BIGINT DEFAULT NULL,
    code VARCHAR(120) NOT NULL,
    name VARCHAR(200) NOT NULL,
    manager_user_id BIGINT DEFAULT NULL,
    base_location VARCHAR(120) NOT NULL DEFAULT '',
    region VARCHAR(120) NOT NULL DEFAULT '',
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    sort_order BIGINT NOT NULL DEFAULT 0,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, code, deleted)
);

CREATE TABLE IF NOT EXISTS user_department_memberships (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    department_id BIGINT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    lock_version BIGINT NOT NULL DEFAULT 0,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    create_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator VARCHAR(64) DEFAULT NULL,
    creator_id BIGINT DEFAULT NULL,
    update_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor VARCHAR(64) DEFAULT NULL,
    editor_id BIGINT DEFAULT NULL,
    UNIQUE (tenant_id, user_id, department_id, deleted)
);

CREATE INDEX IF NOT EXISTS idx_departments_tenant_parent ON departments(tenant_id, parent_id, deleted);
CREATE INDEX IF NOT EXISTS idx_departments_tenant_status ON departments(tenant_id, status, deleted);
CREATE INDEX IF NOT EXISTS idx_user_department_memberships_user ON user_department_memberships(tenant_id, user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_user_department_memberships_department ON user_department_memberships(tenant_id, department_id, deleted);
