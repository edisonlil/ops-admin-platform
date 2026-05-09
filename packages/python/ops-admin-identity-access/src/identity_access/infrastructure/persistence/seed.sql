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
SELECT 'llm_debug:access', 'LLM debug access', 'Debug configured LLM models and routes'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'llm_debug:access');

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
SELECT 'appearance:access', 'Appearance Studio access', 'Customize admin appearance presets and tokens'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'appearance:access');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:user:manage', 'Tenant user manage', 'Manage users inside platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:user:manage');

INSERT INTO permissions (code, name, description)
SELECT 'tenant:api_key:manage', 'Tenant API key manage', 'Manage API keys inside platform tenants'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenant:api_key:manage');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm', 'tenant', '大模型', 'directory', '', '', '', 'experiment', '', '', 90, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-config', 'tenant', '模型配置', 'page', '/settings/llm-config', 'llm-config', '/settings/llm-config/index', 'settings', 'llm', 'llm_config:access', 91, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-config');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'llm-debug', 'tenant', '模型调试', 'page', '/settings/llm-debug', 'llm-debug', '/settings/llm-debug/index', 'experiment', 'llm', 'llm_debug:access', 92, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'llm-debug');

INSERT INTO menus (menu_key, label, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'rbac', '权限管理', '', '', 'shield', '', '', 100, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'rbac');

INSERT INTO menus (menu_key, label, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'menu-management', '菜单权限', '/rbac/menus', 'menu-management', 'menu', 'rbac', 'system:menu:access', 101, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'menu-management');

INSERT INTO menus (menu_key, label, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'role-management', '角色权限', '/rbac/roles', 'role-management', 'users', 'rbac', 'system:role:access', 102, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'role-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'platform-management', 'platform', '平台管理', 'page', '/platform', 'platform-management', '/platform/index', 'SettingOutlined', '', '', 109, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'platform-management');

UPDATE menus SET
    menu_scope = 'platform',
    menu_type = 'page',
    label = '平台管理',
    path = '/platform',
    route_name = 'platform-management',
    component = '/platform/index',
    icon = 'SettingOutlined',
    parent_key = '',
    permission_code = '',
    sort_order = 109,
    is_visible = TRUE
WHERE menu_key = 'platform-management';

INSERT INTO menus (menu_key, label, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-management', '租户管理', '/tenant', 'tenant-management', 'ApartmentOutlined', '', 'tenant:access', 110, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'appearance-studio', 'platform', '主题管理', 'page', '/settings/appearance-studio', 'appearance-studio', '/settings/appearance-studio/index', 'BgColorsOutlined', '', 'appearance:access', 120, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'appearance-studio');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-settings', 'tenant', '租户设置', 'directory', '', '', 'settings', '', '', 80, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-settings');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-user-management', 'tenant', '成员管理', 'page', '/tenant', 'tenant-user-management', '/tenant/index', 'user', 'tenant-settings', 'tenant:user:manage', 81, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-user-management');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'tenant-api-keys', 'tenant', 'API 密钥', 'page', '/settings/api-keys', 'tenant-api-keys', '/settings/api-keys/index', 'key', 'tenant-settings', 'tenant:api_key:manage', 82, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'tenant-api-keys');

DELETE FROM role_menus
WHERE menu_id IN (
    SELECT id FROM menus
    WHERE menu_scope = 'platform'
      AND menu_key IN ('settings', 'api-keys', 'user-management')
);

DELETE FROM menus
WHERE menu_scope = 'platform'
  AND menu_key IN ('settings', 'api-keys', 'user-management');

UPDATE menus SET menu_scope = 'platform'
WHERE menu_key IN ('platform-management', 'tenant-management', 'appearance-studio', 'rbac', 'menu-management', 'role-management')
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
