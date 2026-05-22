INSERT INTO roles (role_key, name, description, is_system, create_time, update_time)
SELECT 'admin', 'Administrator', 'Full backend administrator', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_key = 'admin');

UPDATE roles SET role_scope = 'platform'
WHERE role_key = 'admin';

INSERT INTO permissions (code, name, description)
SELECT 'llm_config:access', 'LLM config access', 'View LLM provider configuration'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm_config:access');

INSERT INTO permissions (code, name, description)
SELECT 'llm_config:update', 'LLM config update', 'Update LLM provider configuration'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm_config:update');

INSERT INTO permissions (code, name, description)
SELECT 'llm:providers:save', 'LLM provider save', 'Create or update LLM providers'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm:providers:save');

INSERT INTO permissions (code, name, description)
SELECT 'llm:models:save', 'LLM model save', 'Create or update LLM models'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm:models:save');

INSERT INTO permissions (code, name, description)
SELECT 'llm:tasks:register', 'LLM task register', 'Register or update LLM tasks'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm:tasks:register');

INSERT INTO permissions (code, name, description)
SELECT 'llm:routing_policies:save', 'LLM routing policy save', 'Create or update LLM routing policies'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm:routing_policies:save');

INSERT INTO permissions (code, name, description)
SELECT 'llm_debug:access', 'LLM debug access', 'Debug configured LLM models and routes'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm_debug:access');

INSERT INTO permissions (code, name, description)
SELECT 'llm_debug:send', 'LLM debug send', 'Send LLM debug requests'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm_debug:send');

INSERT INTO permissions (code, name, description)
SELECT 'api_keys:access', 'API key access', 'View integration API keys'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'api_keys:access');

INSERT INTO permissions (code, name, description)
SELECT 'api_keys:create', 'API key create', 'Create integration API keys'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'api_keys:create');

INSERT INTO permissions (code, name, description)
SELECT 'api_keys:revoke', 'API key revoke', 'Revoke integration API keys'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'api_keys:revoke');

INSERT INTO permissions (code, name, description)
SELECT 'system:menu:access', 'Menu management access', 'View backend menu definitions'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:menu:access');

INSERT INTO permissions (code, name, description)
SELECT 'system:role:access', 'Role management access', 'View roles and role permissions'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:role:access');

INSERT INTO permissions (code, name, description)
SELECT 'system:user:access', 'User management access', 'View user and role assignments'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:user:access');

INSERT INTO permissions (code, name, description)
SELECT 'system:users:create', 'User create', 'Create platform users'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:users:create');

INSERT INTO permissions (code, name, description)
SELECT 'system:users:update', 'User update', 'Update platform users'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:users:update');

INSERT INTO permissions (code, name, description)
SELECT 'system:users:enable', 'User enable', 'Enable platform users'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:users:enable');

INSERT INTO permissions (code, name, description)
SELECT 'system:users:disable', 'User disable', 'Disable platform users'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:users:disable');

INSERT INTO permissions (code, name, description)
SELECT 'system:menus:create', 'Menu create', 'Create menu and action permissions'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:menus:create');

INSERT INTO permissions (code, name, description)
SELECT 'system:menus:update', 'Menu update', 'Update menu and action permissions'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:menus:update');

INSERT INTO permissions (code, name, description)
SELECT 'system:menus:delete', 'Menu delete', 'Delete menu and action permissions'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:menus:delete');

INSERT INTO permissions (code, name, description)
SELECT 'system:roles:create', 'Role create', 'Create roles'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:roles:create');

INSERT INTO permissions (code, name, description)
SELECT 'system:roles:update', 'Role update', 'Update roles'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:roles:update');

INSERT INTO permissions (code, name, description)
SELECT 'system:roles:delete', 'Role delete', 'Delete roles'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:roles:delete');

INSERT INTO permissions (code, name, description)
SELECT 'system:roles:assign_menus', 'Role menu assignment', 'Assign menu and action permissions to roles'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'system:roles:assign_menus');

INSERT INTO permissions (code, name, description)
SELECT 'platform:branding:update', 'Platform branding update', 'Update platform branding'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'platform:branding:update');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:access', 'Tenant management access', 'View platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:access');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:create', 'Tenant create', 'Create platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:create');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:update', 'Tenant update', 'Update platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:update');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:suspend', 'Tenant suspend', 'Suspend or activate platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:suspend');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:activate', 'Tenant activate', 'Activate platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:activate');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:users:create', 'Tenant user create', 'Create tenant users'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:users:create');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:users:update', 'Tenant user update', 'Update tenant users'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:users:update');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:users:enable', 'Tenant user enable', 'Enable tenant users'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:users:enable');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:users:disable', 'Tenant user disable', 'Disable tenant users'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:users:disable');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:api_keys:create', 'Tenant API key create', 'Create tenant API keys'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:api_keys:create');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:api_keys:revoke', 'Tenant API key revoke', 'Revoke tenant API keys'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:api_keys:revoke');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:theme:assign', 'Tenant theme assignment', 'Assign appearance theme to tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:theme:assign');

INSERT INTO permissions (code, name, description)
SELECT 'appearance:access', 'Appearance Studio access', 'Customize admin appearance presets and tokens'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'appearance:access');

INSERT INTO permissions (code, name, description)
SELECT 'appearance:themes:create', 'Appearance theme create', 'Create appearance themes'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'appearance:themes:create');

INSERT INTO permissions (code, name, description)
SELECT 'appearance:themes:update', 'Appearance theme update', 'Update appearance themes'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'appearance:themes:update');

INSERT INTO permissions (code, name, description)
SELECT 'appearance:themes:publish', 'Appearance theme publish', 'Publish appearance themes'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'appearance:themes:publish');

INSERT INTO permissions (code, name, description)
SELECT 'appearance:themes:disable', 'Appearance theme disable', 'Disable appearance themes'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'appearance:themes:disable');

INSERT INTO permissions (code, name, description)
SELECT 'appearance:themes:set_default', 'Appearance theme platform default', 'Set platform default appearance theme'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'appearance:themes:set_default');

INSERT INTO permissions (code, name, description)
SELECT 'file:library:manage', 'Manage file libraries', 'Create, update, and delete tenant file libraries'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'file:library:manage');

INSERT INTO permissions (code, name, description)
SELECT 'file:object:read', 'Read files', 'List, search, and download tenant files'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'file:object:read');

INSERT INTO permissions (code, name, description)
SELECT 'file:object:upload', 'Upload files', 'Upload files to tenant file libraries'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'file:object:upload');

INSERT INTO permissions (code, name, description)
SELECT 'file:object:delete', 'Delete files', 'Delete tenant files'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'file:object:delete');

INSERT INTO permissions (code, name, description)
SELECT 'file:quota:manage', 'Manage file quotas', 'Configure tenant file storage quotas'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'file:quota:manage');

INSERT INTO permissions (code, name, description)
SELECT 'file:storage_profiles:manage', 'Manage file storage profiles', 'Configure object storage profiles for file management'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'file:storage_profiles:manage');

INSERT INTO permissions (code, name, description)
SELECT 'audit:system-log:view', '查看系统日志', '查看平台和租户系统审计日志'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'audit:system-log:view');

INSERT INTO permissions (code, name, description)
SELECT 'audit:operation-log:view', '查看操作日志', '查看用户操作审计日志'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'audit:operation-log:view');

INSERT INTO permissions (code, name, description)
SELECT 'audit:api-log:view', '查看接口日志', '查看接口请求审计日志'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'audit:api-log:view');

INSERT INTO permissions (code, name, description)
SELECT 'audit:sql-log:view', '查看 SQL 日志', '查看慢 SQL 和错误 SQL 审计日志'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'audit:sql-log:view');

INSERT INTO permissions (code, name, description)
SELECT 'audit:visitor-log:view', '查看访客日志', '查看访客访问审计日志'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'audit:visitor-log:view');

INSERT INTO permissions (code, name, description)
SELECT 'audit:settings:view', '查看日志配置', '查看日志采集、队列和保留配置'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'audit:settings:view');

INSERT INTO permissions (code, name, description)
SELECT 'audit:settings:manage', '管理日志配置', '管理日志采集、队列和保留配置'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'audit:settings:manage');

INSERT INTO permissions (code, name, description)
SELECT 'prompt:assets:view', 'View prompt assets', 'View prompt assets and versions'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'prompt:assets:view');

INSERT INTO permissions (code, name, description)
SELECT 'prompt:assets:manage', 'Manage prompt assets', 'Create, update, publish, and archive prompt assets'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'prompt:assets:manage');

INSERT INTO permissions (code, name, description)
SELECT 'skill:assets:view', '查看技能资产', '查看技能资产和版本'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'skill:assets:view');

INSERT INTO permissions (code, name, description)
SELECT 'skill:assets:manage', '管理技能资产', '创建、更新、发布和归档技能资产'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'skill:assets:manage');

INSERT INTO permissions (code, name, description)
SELECT 'ai_studio:access', 'AI Studio access', 'Access tenant AI Studio'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_studio:access');

INSERT INTO permissions (code, name, description)
SELECT 'ai_applications:read', 'AI application read', 'View tenant AI applications'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_applications:read');

INSERT INTO permissions (code, name, description)
SELECT 'ai_applications:manage', 'AI application manage', 'Create and update tenant AI applications'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_applications:manage');

INSERT INTO permissions (code, name, description)
SELECT 'ai_applications:publish', 'AI application publish', 'Publish tenant AI application APIs'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_applications:publish');

INSERT INTO permissions (code, name, description)
SELECT 'ai_applications:run', 'AI application run', 'Run or debug tenant AI applications'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_applications:run');

INSERT INTO permissions (code, name, description)
SELECT 'ai_capabilities:read', 'AI capability read', 'View tenant AI capabilities'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_capabilities:read');

INSERT INTO permissions (code, name, description)
SELECT 'ai_capabilities:manage', 'AI capability manage', 'Create and update tenant AI capabilities'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_capabilities:manage');

INSERT INTO permissions (code, name, description)
SELECT 'ai_capabilities:execute', 'AI capability execute', 'Execute tenant AI capabilities'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_capabilities:execute');

INSERT INTO permissions (code, name, description)
SELECT 'ai_runtime:trace:read', 'AI runtime trace read', 'View AI runtime traces'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_runtime:trace:read');

INSERT INTO permissions (code, name, description)
SELECT 'ai_studio:quota:read', 'AI Studio quota read', 'View tenant AI Studio quotas'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_studio:quota:read');

INSERT INTO permissions (code, name, description)
SELECT 'ai_studio:quota:manage', 'AI Studio quota manage', 'Manage tenant AI Studio quotas'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'ai_studio:quota:manage');




INSERT INTO permissions (code, name, description)
SELECT 'basic-data:dictionary:read', 'Read business dictionaries', 'View and consume tenant business dictionaries'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'basic-data:dictionary:read');

INSERT INTO permissions (code, name, description)
SELECT 'basic-data:dictionary:manage', 'Manage business dictionaries', 'Create, update, disable, and delete tenant business dictionaries'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'basic-data:dictionary:manage');

INSERT INTO permissions (code, name, description)
SELECT 'basic-data:region:read', 'Read regions', 'View and consume tenant regions'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'basic-data:region:read');

INSERT INTO permissions (code, name, description)
SELECT 'basic-data:region:manage', 'Manage regions', 'Create, update, disable, and delete tenant regions'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'basic-data:region:manage');

INSERT INTO permissions (code, name, description)
SELECT 'basic-data:region:import', 'Import regions', 'Import tenant region data'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'basic-data:region:import');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:user:manage', 'Tenant user manage', 'Manage users inside platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:user:manage');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:api_key:manage', 'Tenant API key manage', 'Manage API keys inside platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:api_key:manage');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:inbox:view', 'Messaging inbox view', 'View own in-app messages'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:inbox:view');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:inbox:manage_self', 'Messaging inbox manage self', 'Update own in-app message read state'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:inbox:manage_self');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:messages:view', 'Messaging messages view', 'View tenant message send records'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:messages:view');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:messages:send', 'Messaging messages send', 'Send tenant in-app messages'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:messages:send');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:messages:cancel', 'Messaging messages cancel', 'Cancel queued tenant messages'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:messages:cancel');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:templates:view', 'Messaging templates view', 'View tenant message templates'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:templates:view');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:templates:manage', 'Messaging templates manage', 'Manage tenant message templates'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:templates:manage');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:templates:create', 'Messaging templates create', 'Create tenant message templates'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:templates:create');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:templates:update', 'Messaging templates update', 'Update tenant message templates'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:templates:update');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:templates:enable', 'Messaging templates enable', 'Enable tenant message templates'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:templates:enable');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:templates:disable', 'Messaging templates disable', 'Disable tenant message templates'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:templates:disable');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:channels:view', 'Messaging channels view', 'View tenant message channels'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:channels:view');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:channels:manage', 'Messaging channels manage', 'Manage tenant message channels'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:channels:manage');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:channels:create', 'Messaging channels create', 'Create tenant message channels'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:channels:create');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:channels:update', 'Messaging channels update', 'Update tenant message channels'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:channels:update');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:channels:enable', 'Messaging channels enable', 'Enable tenant message channels'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:channels:enable');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:channels:disable', 'Messaging channels disable', 'Disable tenant message channels'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:channels:disable');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:channels:test', 'Messaging channels test', 'Test tenant message channels'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:channels:test');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:chat_bots:view', 'Messaging chat bots view', 'View tenant group chat robots'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:chat_bots:view');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:chat_bots:create', 'Messaging chat bots create', 'Create tenant group chat robots'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:chat_bots:create');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:chat_bots:update', 'Messaging chat bots update', 'Update tenant group chat robots'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:chat_bots:update');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:chat_bots:enable', 'Messaging chat bots enable', 'Enable tenant group chat robots'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:chat_bots:enable');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:chat_bots:disable', 'Messaging chat bots disable', 'Disable tenant group chat robots'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:chat_bots:disable');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:chat_bots:test', 'Messaging chat bots test', 'Test tenant group chat robots'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:chat_bots:test');

INSERT INTO permissions (code, name, description)
SELECT 'messaging:dispatch:manage', 'Messaging dispatch manage', 'Dispatch and retry tenant messages'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'messaging:dispatch:manage');

INSERT INTO permissions (code, name, description)
SELECT 'cron:tasks:view', '查看定时任务', '查看定时任务'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:tasks:view');

INSERT INTO permissions (code, name, description)
SELECT 'cron:tasks:create', '新增定时任务', '新增定时任务'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:tasks:create');

INSERT INTO permissions (code, name, description)
SELECT 'cron:tasks:update', '编辑定时任务', '编辑定时任务'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:tasks:update');

INSERT INTO permissions (code, name, description)
SELECT 'cron:tasks:enable', '启用定时任务', '启用定时任务'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:tasks:enable');

INSERT INTO permissions (code, name, description)
SELECT 'cron:tasks:disable', '停用定时任务', '停用定时任务'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:tasks:disable');

INSERT INTO permissions (code, name, description)
SELECT 'cron:tasks:delete', '删除定时任务', '删除定时任务'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:tasks:delete');

INSERT INTO permissions (code, name, description)
SELECT 'cron:tasks:trigger', '手动触发定时任务', '手动触发定时任务'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:tasks:trigger');

INSERT INTO permissions (code, name, description)
SELECT 'cron:runs:view', '查看运行记录', '查看定时任务运行记录'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:runs:view');

INSERT INTO permissions (code, name, description)
SELECT 'cron:runs:stop', '停止运行任务', '停止等待中或运行中的定时任务运行记录'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:runs:stop');

INSERT INTO permissions (code, name, description)
SELECT 'cron:runs:delete', '删除运行记录', '删除定时任务运行记录和关联执行尝试'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'cron:runs:delete');

UPDATE permissions SET name = '查看定时任务', description = '查看定时任务' WHERE code = 'cron:tasks:view';
UPDATE permissions SET name = '新增定时任务', description = '新增定时任务' WHERE code = 'cron:tasks:create';
UPDATE permissions SET name = '编辑定时任务', description = '编辑定时任务' WHERE code = 'cron:tasks:update';
UPDATE permissions SET name = '启用定时任务', description = '启用定时任务' WHERE code = 'cron:tasks:enable';
UPDATE permissions SET name = '停用定时任务', description = '停用定时任务' WHERE code = 'cron:tasks:disable';
UPDATE permissions SET name = '删除定时任务', description = '删除定时任务' WHERE code = 'cron:tasks:delete';
UPDATE permissions SET name = '手动触发定时任务', description = '手动触发定时任务' WHERE code = 'cron:tasks:trigger';
UPDATE permissions SET name = '查看运行记录', description = '查看定时任务运行记录' WHERE code = 'cron:runs:view';

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'messaging', 'tenant', '消息系统', 'directory', '', '', '', 'message', '', '', 85, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'messaging');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-inbox', 'tenant', '站内信', 'page', '/messaging/inbox', 'message-inbox', '/messaging/inbox/index', 'message', 'messaging', 'messaging:inbox:view', 86, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-inbox');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-inbox-read', 'tenant', '标记已读', 'action', '', '', '', '', 'message-inbox', 'messaging:inbox:manage_self', 861, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-inbox-read');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-inbox-unread', 'tenant', '标记未读', 'action', '', '', '', '', 'message-inbox', 'messaging:inbox:manage_self', 862, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-inbox-unread');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-inbox-delete', 'tenant', '删除站内信', 'action', '', '', '', '', 'message-inbox', 'messaging:inbox:manage_self', 863, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-inbox-delete');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-outbox', 'tenant', '发送记录', 'page', '/messaging/outbox', 'message-outbox', '/messaging/outbox/index', 'FileSearchOutlined', 'messaging', 'messaging:messages:view', 87, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-outbox');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-outbox-cancel', 'tenant', '取消发送', 'action', '', '', '', '', 'message-outbox', 'messaging:messages:cancel', 871, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-outbox-cancel');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-send', 'tenant', '发送消息', 'page', '/messaging/send', 'message-send', '/messaging/send/index', 'message', 'messaging', 'messaging:messages:send', 88, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-send');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-send-submit', 'tenant', '发送消息', 'action', '', '', '', '', 'message-send', 'messaging:messages:send', 881, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-send-submit');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-templates', 'tenant', '消息模板', 'page', '/messaging/templates', 'message-templates', '/messaging/templates/index', 'file-text', 'messaging', 'messaging:templates:view', 89, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-templates');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-templates-create', 'tenant', '新增模板', 'action', '', '', '', '', 'message-templates', 'messaging:templates:create', 891, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-templates-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-templates-update', 'tenant', '编辑模板', 'action', '', '', '', '', 'message-templates', 'messaging:templates:update', 892, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-templates-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-templates-enable', 'tenant', '启用模板', 'action', '', '', '', '', 'message-templates', 'messaging:templates:enable', 893, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-templates-enable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-templates-disable', 'tenant', '停用模板', 'action', '', '', '', '', 'message-templates', 'messaging:templates:disable', 894, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-templates-disable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-channels', 'tenant', '渠道配置', 'page', '/messaging/channels', 'message-channels', '/messaging/channels/index', 'api', 'messaging', 'messaging:channels:view', 90, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-channels');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-channels-create', 'tenant', '新增渠道', 'action', '', '', '', '', 'message-channels', 'messaging:channels:create', 901, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-channels-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-channels-update', 'tenant', '编辑渠道', 'action', '', '', '', '', 'message-channels', 'messaging:channels:update', 902, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-channels-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-channels-enable', 'tenant', '启用渠道', 'action', '', '', '', '', 'message-channels', 'messaging:channels:enable', 903, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-channels-enable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-channels-disable', 'tenant', '停用渠道', 'action', '', '', '', '', 'message-channels', 'messaging:channels:disable', 904, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-channels-disable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-channels-test', 'tenant', '测试渠道', 'action', '', '', '', '', 'message-channels', 'messaging:channels:test', 905, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-channels-test');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-chat-bots', 'tenant', '群聊机器人', 'page', '/messaging/chat-bots', 'message-chat-bots', '/messaging/chat-bots/index', 'robot', 'messaging', 'messaging:chat_bots:view', 91, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-chat-bots');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-chat-bots-create', 'tenant', '新增机器人', 'action', '', '', '', '', 'message-chat-bots', 'messaging:chat_bots:create', 911, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-chat-bots-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-chat-bots-update', 'tenant', '编辑机器人', 'action', '', '', '', '', 'message-chat-bots', 'messaging:chat_bots:update', 912, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-chat-bots-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-chat-bots-enable', 'tenant', '启用机器人', 'action', '', '', '', '', 'message-chat-bots', 'messaging:chat_bots:enable', 913, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-chat-bots-enable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-chat-bots-disable', 'tenant', '停用机器人', 'action', '', '', '', '', 'message-chat-bots', 'messaging:chat_bots:disable', 914, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-chat-bots-disable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'message-chat-bots-test', 'tenant', '测试机器人', 'action', '', '', '', '', 'message-chat-bots', 'messaging:chat_bots:test', 915, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'message-chat-bots-test');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron', 'tenant', '定时任务', 'directory', '', '', '', 'ScheduleOutlined', '', '', 93, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-tasks', 'tenant', '任务管理', 'page', '/cron/tasks', 'cron-tasks', '/cron/tasks/index', 'ScheduleOutlined', 'cron', 'cron:tasks:view', 931, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-tasks');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-tasks-create', 'tenant', '新增定时任务', 'action', '', '', '', '', 'cron-tasks', 'cron:tasks:create', 9311, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-tasks-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-tasks-update', 'tenant', '编辑定时任务', 'action', '', '', '', '', 'cron-tasks', 'cron:tasks:update', 9312, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-tasks-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-tasks-enable', 'tenant', '启用定时任务', 'action', '', '', '', '', 'cron-tasks', 'cron:tasks:enable', 9313, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-tasks-enable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-tasks-disable', 'tenant', '停用定时任务', 'action', '', '', '', '', 'cron-tasks', 'cron:tasks:disable', 9314, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-tasks-disable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-tasks-delete', 'tenant', '删除定时任务', 'action', '', '', '', '', 'cron-tasks', 'cron:tasks:delete', 9315, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-tasks-delete');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-tasks-trigger', 'tenant', '手动触发', 'action', '', '', '', '', 'cron-tasks', 'cron:tasks:trigger', 9316, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-tasks-trigger');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-runs', 'tenant', '运行记录', 'page', '/cron/runs', 'cron-runs', '/cron/runs/index', 'FileSearchOutlined', 'cron', 'cron:runs:view', 932, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-runs');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-runs-stop', 'tenant', '停止运行任务', 'action', '', '', '', '', 'cron-runs', 'cron:runs:stop', 9321, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-runs-stop');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'cron-runs-delete', 'tenant', '删除运行记录', 'action', '', '', '', '', 'cron-runs', 'cron:runs:delete', 9322, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'cron-runs-delete');

UPDATE menus SET label = '定时任务' WHERE menu_key = 'cron';
UPDATE menus SET label = '任务管理' WHERE menu_key = 'cron-tasks';
UPDATE menus SET label = '新增定时任务' WHERE menu_key = 'cron-tasks-create';
UPDATE menus SET label = '编辑定时任务' WHERE menu_key = 'cron-tasks-update';
UPDATE menus SET label = '启用定时任务' WHERE menu_key = 'cron-tasks-enable';
UPDATE menus SET label = '停用定时任务' WHERE menu_key = 'cron-tasks-disable';
UPDATE menus SET label = '删除定时任务' WHERE menu_key = 'cron-tasks-delete';
UPDATE menus SET label = '手动触发' WHERE menu_key = 'cron-tasks-trigger';
UPDATE menus
SET label = '运行记录',
    menu_type = 'page',
    path = '/cron/runs',
    route_name = 'cron-runs',
    component = '/cron/runs/index',
    icon = 'FileSearchOutlined',
    parent_key = 'cron',
    permission_code = 'cron:runs:view',
    sort_order = 932,
    is_visible = TRUE
WHERE menu_key = 'cron-runs';

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm', 'tenant', '大模型', 'directory', '', '', '', 'experiment', '', '', 90, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-config', 'tenant', '模型配置', 'page', '/settings/llm-config', 'llm-config', '/settings/llm-config/index', 'settings', 'llm', 'llm_config:access', 91, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-config');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-providers-save', 'tenant', '保存供应商', 'action', '', '', '', '', 'llm-config', 'llm:providers:save', 911, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-providers-save');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-models-save', 'tenant', '保存模型', 'action', '', '', '', '', 'llm-config', 'llm:models:save', 912, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-models-save');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-tasks-register', 'tenant', '注册任务', 'action', '', '', '', '', 'llm-config', 'llm:tasks:register', 913, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-tasks-register');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-routing-policies-save', 'tenant', '保存路由策略', 'action', '', '', '', '', 'llm-config', 'llm:routing_policies:save', 914, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-routing-policies-save');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-debug', 'tenant', '模型调试', 'page', '/settings/llm-debug', 'llm-debug', '/settings/llm-debug/index', 'experiment', 'llm', 'llm_debug:access', 92, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-debug');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-debug-send', 'tenant', '发送调试请求', 'action', '', '', '', '', 'llm-debug', 'llm_debug:send', 921, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-debug-send');

INSERT INTO menus (menu_key, label, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'rbac', '权限管理', '', '', 'shield', '', '', 100, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'rbac');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'user-management', 'platform', '用户管理', 'page', '/rbac/users', 'user-management', '/rbac/user/index', 'user', 'rbac', 'system:user:access', 100, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'user-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'user-management-create', 'platform', '新增用户', 'action', '', '', '', '', 'user-management', 'system:users:create', 1001, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'user-management-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'user-management-update', 'platform', '编辑用户', 'action', '', '', '', '', 'user-management', 'system:users:update', 1002, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'user-management-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'user-management-enable', 'platform', '启用用户', 'action', '', '', '', '', 'user-management', 'system:users:enable', 1003, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'user-management-enable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'user-management-disable', 'platform', '停用用户', 'action', '', '', '', '', 'user-management', 'system:users:disable', 1004, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'user-management-disable');

INSERT INTO menus (menu_key, label, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'menu-management', '菜单权限', '/rbac/menus', 'menu-management', 'menu', 'rbac', 'system:menu:access', 101, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'menu-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'menu-management-create', 'platform', '新增菜单', 'action', '', '', '', '', 'menu-management', 'system:menus:create', 1011, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'menu-management-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'menu-management-update', 'platform', '编辑菜单', 'action', '', '', '', '', 'menu-management', 'system:menus:update', 1012, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'menu-management-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'menu-management-delete', 'platform', '删除菜单', 'action', '', '', '', '', 'menu-management', 'system:menus:delete', 1013, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'menu-management-delete');

INSERT INTO menus (menu_key, label, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'role-management', '角色权限', '/rbac/roles', 'role-management', 'users', 'rbac', 'system:role:access', 102, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'role-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'role-management-create', 'platform', '新增角色', 'action', '', '', '', '', 'role-management', 'system:roles:create', 1021, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'role-management-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'role-management-update', 'platform', '编辑角色', 'action', '', '', '', '', 'role-management', 'system:roles:update', 1022, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'role-management-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'role-management-delete', 'platform', '删除角色', 'action', '', '', '', '', 'role-management', 'system:roles:delete', 1023, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'role-management-delete');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'role-management-assign-menus', 'platform', '分配菜单权限', 'action', '', '', '', '', 'role-management', 'system:roles:assign_menus', 1024, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'role-management-assign-menus');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'platform-management', 'platform', '平台管理', 'directory', '/platform', 'platform-management', '', 'SettingOutlined', '', '', 109, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'platform-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'platform-branding', 'platform', '平台信息', 'page', '/platform/branding', 'platform-branding', '/platform/index', 'SettingOutlined', 'platform-management', '', 1091, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'platform-branding');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'platform-branding-update', 'platform', '更新平台标识', 'action', '', '', '', '', 'platform-branding', 'platform:branding:update', 10911, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'platform-branding-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-storage-profiles', 'platform', '文件存储', 'page', '/files/storage-profiles', 'file-storage-profiles', '/files/storage-profiles/index', 'database', 'platform-management', 'file:storage_profiles:manage', 1092, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-storage-profiles');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-storage-profiles-manage', 'platform', '管理文件存储', 'action', '', '', '', '', 'file-storage-profiles', 'file:storage_profiles:manage', 10921, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-storage-profiles-manage');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-tenant-quotas', 'platform', '文件配额', 'page', '/files/tenant-quotas', 'file-tenant-quotas', '/files/tenant-quotas/index', 'hdd', 'platform-management', 'file:quota:manage', 1093, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-tenant-quotas');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-tenant-quotas-manage', 'platform', '管理文件配额', 'action', '', '', '', '', 'file-tenant-quotas', 'file:quota:manage', 10931, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-tenant-quotas-manage');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'audit-log-settings', 'platform', '日志配置', 'page', '/audit/settings', 'audit-log-settings', '/audit/settings/index', 'setting', 'platform-management', 'audit:settings:view', 1094, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'audit-log-settings');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'audit-log-settings-manage', 'platform', '管理日志配置', 'action', '', '', '', '', 'audit-log-settings', 'audit:settings:manage', 10941, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'audit-log-settings-manage');

UPDATE menus SET
    menu_scope = 'platform',
    menu_type = 'directory',
    label = '平台管理',
    path = '/platform',
    route_name = 'platform-management',
    component = '',
    icon = 'SettingOutlined',
    parent_key = '',
    permission_code = '',
    sort_order = 109,
    is_visible = TRUE
WHERE menu_key = 'platform-management';

UPDATE menus SET
    menu_scope = 'platform',
    menu_type = 'page',
    label = '平台信息',
    path = '/platform/branding',
    route_name = 'platform-branding',
    component = '/platform/index',
    icon = 'SettingOutlined',
    parent_key = 'platform-management',
    permission_code = '',
    sort_order = 1091,
    is_visible = TRUE
WHERE menu_key = 'platform-branding';

UPDATE menus SET
    parent_key = 'platform-branding',
    sort_order = 10911
WHERE menu_key = 'platform-branding-update';

INSERT INTO menus (menu_key, label, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management', '租户管理', '/tenant', 'tenant-management', 'ApartmentOutlined', '', 'tenant:access', 110, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-create', 'platform', '新增租户', 'action', '', '', '', '', 'tenant-management', 'tenant:create', 1101, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-update', 'platform', '编辑租户', 'action', '', '', '', '', 'tenant-management', 'tenant:update', 1102, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-activate', 'platform', '启用租户', 'action', '', '', '', '', 'tenant-management', 'tenant:activate', 1103, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-activate');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-suspend', 'platform', '停用租户', 'action', '', '', '', '', 'tenant-management', 'tenant:suspend', 1104, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-suspend');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-users-create', 'platform', '新增租户成员', 'action', '', '', '', '', 'tenant-management', 'tenant:users:create', 1105, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-users-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-users-update', 'platform', '编辑租户成员', 'action', '', '', '', '', 'tenant-management', 'tenant:users:update', 1106, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-users-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-api-keys-create', 'platform', '新增租户 API Key', 'action', '', '', '', '', 'tenant-management', 'tenant:api_keys:create', 1107, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-api-keys-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-api-keys-revoke', 'platform', '撤销租户 API Key', 'action', '', '', '', '', 'tenant-management', 'tenant:api_keys:revoke', 1108, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-api-keys-revoke');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management-theme-assign', 'platform', '分配租户主题', 'action', '', '', '', '', 'tenant-management', 'tenant:theme:assign', 1109, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management-theme-assign');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'appearance-studio', 'platform', '主题管理', 'page', '/settings/appearance-studio', 'appearance-studio', '/settings/appearance-studio/index', 'BgColorsOutlined', '', 'appearance:access', 120, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'appearance-studio');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'appearance-themes-create', 'platform', '新建主题', 'action', '', '', '', '', 'appearance-studio', 'appearance:themes:create', 1201, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'appearance-themes-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'appearance-themes-update', 'platform', '编辑主题', 'action', '', '', '', '', 'appearance-studio', 'appearance:themes:update', 1202, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'appearance-themes-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'appearance-themes-publish', 'platform', '发布主题', 'action', '', '', '', '', 'appearance-studio', 'appearance:themes:publish', 1203, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'appearance-themes-publish');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'appearance-themes-disable', 'platform', '停用主题', 'action', '', '', '', '', 'appearance-studio', 'appearance:themes:disable', 1204, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'appearance-themes-disable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'appearance-themes-set-default', 'platform', '设为平台默认', 'action', '', '', '', '', 'appearance-studio', 'appearance:themes:set_default', 1205, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'appearance-themes-set-default');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-settings', 'tenant', '租户设置', 'directory', '', '', 'settings', '', '', 80, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-settings');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-user-management', 'tenant', '成员管理', 'page', '/tenant', 'tenant-user-management', '/tenant/index', 'user', 'tenant-settings', 'tenant:user:manage', 81, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-user-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-users-create', 'tenant', '新增成员', 'action', '', '', '', '', 'tenant-user-management', 'tenant:users:create', 811, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-users-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-users-update', 'tenant', '编辑成员', 'action', '', '', '', '', 'tenant-user-management', 'tenant:users:update', 812, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-users-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-users-enable', 'tenant', '启用成员', 'action', '', '', '', '', 'tenant-user-management', 'tenant:users:enable', 813, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-users-enable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-users-disable', 'tenant', '停用成员', 'action', '', '', '', '', 'tenant-user-management', 'tenant:users:disable', 814, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-users-disable');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-api-keys', 'tenant', 'API 密钥', 'page', '/settings/api-keys', 'tenant-api-keys', '/settings/api-keys/index', 'key', 'tenant-settings', 'tenant:api_key:manage', 82, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-api-keys');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-api-keys-create', 'tenant', '新增 API Key', 'action', '', '', '', '', 'tenant-api-keys', 'tenant:api_keys:create', 821, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-api-keys-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-api-keys-revoke', 'tenant', '撤销 API Key', 'action', '', '', '', '', 'tenant-api-keys', 'tenant:api_keys:revoke', 822, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-api-keys-revoke');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-management', 'tenant', '文件管理', 'directory', '', '', '', 'folder', '', '', 83, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-libraries', 'tenant', '文件库', 'page', '/files/libraries', 'file-libraries', '/files/libraries/index', 'folder-open', 'file-management', 'file:object:read', 831, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-libraries');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-libraries-create', 'tenant', '新建文件库', 'action', '', '', '', '', 'file-libraries', 'file:library:manage', 8311, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-libraries-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-libraries-update', 'tenant', '编辑文件库', 'action', '', '', '', '', 'file-libraries', 'file:library:manage', 8312, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-libraries-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-libraries-delete', 'tenant', '删除文件库', 'action', '', '', '', '', 'file-libraries', 'file:library:manage', 8313, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-libraries-delete');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-objects', 'tenant', '文件', 'page', '/files/objects', 'file-objects', '/files/objects/index', 'file', 'file-management', 'file:object:read', 832, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-objects');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-objects-upload', 'tenant', '上传文件', 'action', '', '', '', '', 'file-objects', 'file:object:upload', 8321, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-objects-upload');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'file-objects-delete', 'tenant', '删除文件', 'action', '', '', '', '', 'file-objects', 'file:object:delete', 8322, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'file-objects-delete');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'audit-logs', 'tenant', '审计日志', 'directory', '', '', '', 'file-search', '', '', 835, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'audit-logs');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'audit-system-logs', 'tenant', '系统日志', 'page', '/audit/system', 'audit-system-logs', '/audit/system/index', 'monitor', 'audit-logs', 'audit:system-log:view', 8351, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'audit-system-logs');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'audit-operation-logs', 'tenant', '操作日志', 'page', '/audit/operations', 'audit-operation-logs', '/audit/operations/index', 'edit', 'audit-logs', 'audit:operation-log:view', 8352, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'audit-operation-logs');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'audit-api-logs', 'tenant', '接口日志', 'page', '/audit/apis', 'audit-api-logs', '/audit/apis/index', 'api', 'audit-logs', 'audit:api-log:view', 8353, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'audit-api-logs');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'audit-sql-logs', 'tenant', 'SQL 日志', 'page', '/audit/sql', 'audit-sql-logs', '/audit/sql/index', 'database', 'audit-logs', 'audit:sql-log:view', 8354, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'audit-sql-logs');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'audit-visitor-logs', 'tenant', '访客日志', 'page', '/audit/visitors', 'audit-visitor-logs', '/audit/visitors/index', 'user', 'audit-logs', 'audit:visitor-log:view', 8355, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'audit-visitor-logs');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-assets', 'tenant', 'AI 资产', 'directory', '', '', '', 'robot', '', '', 84, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-assets');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'prompt-library', 'tenant', '提示词库', 'page', '/prompts/library', 'prompt-library', '/prompts/library/index', 'message', 'ai-assets', 'prompt:assets:view', 841, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'prompt-library');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'prompt-library-manage', 'tenant', '管理提示词', 'action', '', '', '', '', 'prompt-library', 'prompt:assets:manage', 8411, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'prompt-library-manage');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'skill-library', 'tenant', '技能库', 'page', '/skills/library', 'skill-library', '/skills/library/index', 'tool', 'ai-assets', 'skill:assets:view', 842, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'skill-library');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'skill-library-manage', 'tenant', '管理技能', 'action', '', '', '', '', 'skill-library', 'skill:assets:manage', 8421, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'skill-library-manage');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio', 'tenant', 'AI Studio', 'page', '/ai/studio', 'ai-studio', '/ai/studio/index', 'robot', '', 'ai_studio:access', 84, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio-app-read', 'tenant', 'View AI applications', 'action', '', '', '', '', 'ai-studio', 'ai_applications:read', 840, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio-app-read');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio-app-manage', 'tenant', 'Manage AI applications', 'action', '', '', '', '', 'ai-studio', 'ai_applications:manage', 841, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio-app-manage');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio-app-publish', 'tenant', 'Publish AI applications', 'action', '', '', '', '', 'ai-studio', 'ai_applications:publish', 842, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio-app-publish');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio-app-run', 'tenant', 'Run AI applications', 'action', '', '', '', '', 'ai-studio', 'ai_applications:run', 843, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio-app-run');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio-trace-read', 'tenant', 'View runtime traces', 'action', '', '', '', '', 'ai-studio', 'ai_runtime:trace:read', 844, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio-trace-read');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio-capability-read', 'tenant', 'View AI capabilities', 'action', '', '', '', '', 'ai-studio', 'ai_capabilities:read', 845, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio-capability-read');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio-capability-manage', 'tenant', 'Manage AI capabilities', 'action', '', '', '', '', 'ai-studio', 'ai_capabilities:manage', 846, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio-capability-manage');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-studio-capability-execute', 'tenant', 'Execute AI capabilities', 'action', '', '', '', '', 'ai-studio', 'ai_capabilities:execute', 847, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-studio-capability-execute');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-tenant-quotas', 'platform', 'AI application quotas', 'page', '/ai/tenant-quotas', 'ai-tenant-quotas', '/ai/tenant-quotas/index', 'robot', 'platform-management', 'ai_studio:quota:manage', 1095, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-tenant-quotas');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'ai-tenant-quotas-manage', 'platform', 'Manage AI application quotas', 'action', '', '', '', '', 'ai-tenant-quotas', 'ai_studio:quota:manage', 10951, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'ai-tenant-quotas-manage');






INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data', 'tenant', '基础数据', 'directory', '', '', '', 'database', '', '', 85, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-dictionaries', 'tenant', '业务字典', 'page', '/basic-data/dictionaries', 'basic-data-dictionaries', '/basic-data/dictionaries/index', 'database', 'basic-data', 'basic-data:dictionary:read', 841, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-dictionaries');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-dictionaries-create', 'tenant', '新建业务字典', 'action', '', '', '', '', 'basic-data-dictionaries', 'basic-data:dictionary:manage', 8411, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-dictionaries-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-dictionaries-update', 'tenant', '编辑业务字典', 'action', '', '', '', '', 'basic-data-dictionaries', 'basic-data:dictionary:manage', 8412, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-dictionaries-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-dictionaries-delete', 'tenant', '删除业务字典', 'action', '', '', '', '', 'basic-data-dictionaries', 'basic-data:dictionary:manage', 8413, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-dictionaries-delete');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-items-create', 'tenant', '新建字典项', 'action', '', '', '', '', 'basic-data-dictionaries', 'basic-data:dictionary:manage', 8414, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-items-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-items-update', 'tenant', '编辑字典项', 'action', '', '', '', '', 'basic-data-dictionaries', 'basic-data:dictionary:manage', 8415, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-items-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-items-delete', 'tenant', '删除字典项', 'action', '', '', '', '', 'basic-data-dictionaries', 'basic-data:dictionary:manage', 8416, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-items-delete');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-regions', 'tenant', '区域管理', 'page', '/basic-data/regions', 'basic-data-regions', '/basic-data/regions/index', 'environment', 'basic-data', 'basic-data:region:read', 842, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-regions');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-regions-create', 'tenant', '新建区域', 'action', '', '', '', '', 'basic-data-regions', 'basic-data:region:manage', 8421, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-regions-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-regions-update', 'tenant', '编辑区域', 'action', '', '', '', '', 'basic-data-regions', 'basic-data:region:manage', 8422, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-regions-update');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-regions-delete', 'tenant', '删除区域', 'action', '', '', '', '', 'basic-data-regions', 'basic-data:region:manage', 8423, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-regions-delete');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'basic-data-regions-import', 'tenant', '导入区域', 'action', '', '', '', '', 'basic-data-regions', 'basic-data:region:import', 8424, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'basic-data-regions-import');

DELETE FROM role_menus
WHERE menu_id IN (
    SELECT id FROM menus
WHERE menu_scope = 'platform'
      AND menu_key IN ('settings', 'api-keys')
);

DELETE FROM menus
WHERE menu_scope = 'platform'
  AND menu_key IN ('settings', 'api-keys');

UPDATE menus SET menu_scope = 'platform'
WHERE menu_key IN ('platform-management', 'tenant-management', 'appearance-studio', 'rbac', 'user-management', 'menu-management', 'role-management')
  AND (menu_scope IS NULL OR menu_scope = '');

UPDATE menus SET menu_scope = 'tenant'
WHERE menu_key IN ('tenant-settings', 'tenant-user-management', 'tenant-api-keys', 'llm', 'llm-config', 'llm-debug')
  AND (menu_scope IS NULL OR menu_scope = '');

UPDATE menus SET
    menu_scope = 'tenant',
    menu_type = 'directory',
    parent_key = ''
WHERE menu_key = 'llm';

UPDATE menus SET
    menu_scope = 'tenant',
    menu_type = 'page',
    parent_key = 'llm'
WHERE menu_key IN ('llm-config', 'llm-debug');

INSERT INTO role_menus (role_id, menu_id)
SELECT r.id, m.id
FROM roles r
JOIN menus m ON m.menu_scope = 'platform'
WHERE r.role_key = 'admin'
  AND m.menu_key IN ('platform-management', 'platform-branding', 'platform-branding-update')
  AND NOT EXISTS (
      SELECT 1 FROM role_menus rm
      WHERE rm.role_id = r.id AND rm.menu_id = m.id
  );

UPDATE permissions SET name = '查看系统日志', description = '查看平台和租户系统审计日志'
WHERE code = 'audit:system-log:view';

UPDATE permissions SET name = '查看操作日志', description = '查看用户操作审计日志'
WHERE code = 'audit:operation-log:view';

UPDATE permissions SET name = '查看接口日志', description = '查看接口请求审计日志'
WHERE code = 'audit:api-log:view';

UPDATE permissions SET name = '查看 SQL 日志', description = '查看慢 SQL 和错误 SQL 审计日志'
WHERE code = 'audit:sql-log:view';

UPDATE permissions SET name = '查看访客日志', description = '查看访客访问审计日志'
WHERE code = 'audit:visitor-log:view';

UPDATE permissions SET name = '查看日志配置', description = '查看日志采集、队列和保留配置'
WHERE code = 'audit:settings:view';

UPDATE permissions SET name = '管理日志配置', description = '管理日志采集、队列和保留配置'
WHERE code = 'audit:settings:manage';

UPDATE menus SET label = '日志配置'
WHERE menu_key = 'audit-log-settings';

UPDATE menus SET label = '管理日志配置'
WHERE menu_key = 'audit-log-settings-manage';

UPDATE menus SET label = '审计日志'
WHERE menu_key = 'audit-logs';

UPDATE menus SET label = '系统日志'
WHERE menu_key = 'audit-system-logs';

UPDATE menus SET label = '操作日志'
WHERE menu_key = 'audit-operation-logs';

UPDATE menus SET label = '接口日志'
WHERE menu_key = 'audit-api-logs';

UPDATE menus SET label = 'SQL 日志'
WHERE menu_key = 'audit-sql-logs';

UPDATE menus SET label = '访客日志'
WHERE menu_key = 'audit-visitor-logs';
UPDATE menus
SET menu_type = 'page',
    path = '/audit/logs',
    route_name = menu_key,
    component = '/audit/logs/index',
    permission_code = '',
    is_visible = TRUE
WHERE menu_key IN ('audit-logs', 'platform-audit-logs');

UPDATE menus
SET path = '/audit/logs',
    component = '/audit/logs/index',
    is_visible = FALSE
WHERE menu_key IN (
    'audit-system-logs',
    'audit-operation-logs',
    'audit-api-logs',
    'audit-sql-logs',
    'audit-visitor-logs',
    'platform-audit-system-logs',
    'platform-audit-operation-logs',
    'platform-audit-api-logs',
    'platform-audit-sql-logs',
    'platform-audit-visitor-logs'
);
