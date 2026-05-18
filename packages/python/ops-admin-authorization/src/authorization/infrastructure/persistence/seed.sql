INSERT INTO data_resource_descriptors (
    resource_key, name, description, tenant_column, creator_column, owner_user_column,
    owner_department_column, supported_scopes_json, requires_data_scope
)
SELECT
    resource_key, name, description, tenant_column, creator_column, owner_user_column,
    owner_department_column, supported_scopes_json, requires_data_scope
FROM (
    SELECT
        'cron.task' AS resource_key,
        '定时任务' AS name,
        '租户定时任务和执行记录' AS description,
        'tenant_id' AS tenant_column,
        'creator_id' AS creator_column,
        'owner_user_id' AS owner_user_column,
        'owner_department_id' AS owner_department_column,
        '["self","department","department_and_children","custom_departments","tenant"]' AS supported_scopes_json,
        FALSE AS requires_data_scope
    UNION ALL
    SELECT
        'llm.model-config',
        '模型配置',
        '模型供应商、模型、任务和路由策略配置',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'messaging.message',
        '消息系统',
        '站内消息、发件箱、模板和通道配置',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'prompt.asset',
        '提示词库',
        '提示词资产和版本',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'basic-data.dictionary',
        '业务字典',
        '业务字典类型和字典项',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'basic-data.region',
        'Region',
        'Tenant region data',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'file.object',
        '文件管理',
        '文件库、文件对象和文件访问记录',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'identity.api-key',
        'API 密钥',
        '租户 API 密钥',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'llm.call-log',
        'LLM Call Log',
        'Tenant LLM invocation logs',
        'tenant_id',
        'creator_id',
        'creator_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'audit.system-log',
        '系统日志',
        '租户系统审计日志',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'audit.operation-log',
        '操作日志',
        '租户操作审计日志',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'audit.api-log',
        '接口日志',
        '租户接口请求审计日志',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'audit.sql-log',
        'SQL 日志',
        '租户慢 SQL 和错误 SQL 审计日志',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
    UNION ALL
    SELECT
        'audit.visitor-log',
        '访客日志',
        '租户访客访问审计日志',
        'tenant_id',
        'creator_id',
        'owner_user_id',
        'owner_department_id',
        '["self","department","department_and_children","custom_departments","tenant"]',
        FALSE
) AS seed_rows
WHERE NOT EXISTS (
    SELECT 1 FROM data_resource_descriptors
    WHERE data_resource_descriptors.resource_key = seed_rows.resource_key
      AND data_resource_descriptors.deleted = FALSE
);

UPDATE data_resource_descriptors
SET name = '业务字典',
    description = '业务字典类型和字典项'
WHERE resource_key = 'basic-data.dictionary'
  AND deleted = FALSE;

UPDATE data_resource_descriptors SET name = '系统日志', description = '租户系统审计日志'
WHERE resource_key = 'audit.system-log' AND deleted = FALSE;

UPDATE data_resource_descriptors SET name = '操作日志', description = '租户操作审计日志'
WHERE resource_key = 'audit.operation-log' AND deleted = FALSE;

UPDATE data_resource_descriptors SET name = '接口日志', description = '租户接口请求审计日志'
WHERE resource_key = 'audit.api-log' AND deleted = FALSE;

UPDATE data_resource_descriptors SET name = 'SQL 日志', description = '租户慢 SQL 和错误 SQL 审计日志'
WHERE resource_key = 'audit.sql-log' AND deleted = FALSE;

UPDATE data_resource_descriptors SET name = '访客日志', description = '租户访客访问审计日志'
WHERE resource_key = 'audit.visitor-log' AND deleted = FALSE;
