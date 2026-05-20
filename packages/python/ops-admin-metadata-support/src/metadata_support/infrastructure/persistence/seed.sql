INSERT INTO metadata_resource_types (
    tenant_id, code, name, owner_context, description, status,
    create_time, creator, update_time, editor
)
SELECT 0, 'file_management.file_object', '文件对象', 'file_management', '文件管理中的文件对象，可绑定通用元数据和标签。', 'active',
       '2026-05-20T00:00:00+00:00', 'system', '2026-05-20T00:00:00+00:00', 'system'
WHERE NOT EXISTS (
    SELECT 1 FROM metadata_resource_types WHERE tenant_id = 0 AND code = 'file_management.file_object' AND deleted = 0
);

INSERT INTO metadata_resource_types (
    tenant_id, code, name, owner_context, description, status,
    create_time, creator, update_time, editor
)
SELECT 0, 'file_management.file_folder', '文件目录', 'file_management', '文件管理目录资源类型，用于目录标签和目录元数据', 'active',
       '2026-05-20T00:00:00+00:00', 'system', '2026-05-20T00:00:00+00:00', 'system'
WHERE NOT EXISTS (
    SELECT 1 FROM metadata_resource_types WHERE tenant_id = 0 AND code = 'file_management.file_folder' AND deleted = 0
);

INSERT INTO metadata_tag_groups (
    tenant_id, code, name, description, sort_order, status,
    create_time, creator, update_time, editor
)
SELECT 0, 'file_tags', '文件标签', '文件管理默认标签分组。', 10, 'active',
       '2026-05-20T00:00:00+00:00', 'system', '2026-05-20T00:00:00+00:00', 'system'
WHERE NOT EXISTS (
    SELECT 1 FROM metadata_tag_groups WHERE tenant_id = 0 AND code = 'file_tags' AND deleted = 0
);
