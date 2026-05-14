INSERT INTO data_resource_descriptors (
    resource_key, name, description, tenant_column, creator_column, owner_user_column,
    owner_department_column, supported_scopes_json, requires_data_scope
)
SELECT
    'basic-data.dictionary',
    '基础数据字典',
    '基础数据字典类型和字典项',
    'tenant_id',
    'creator_id',
    'owner_user_id',
    'owner_department_id',
    '["self","department","department_and_children","custom_departments","tenant"]',
    FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM data_resource_descriptors WHERE resource_key = 'basic-data.dictionary' AND deleted = FALSE
);
