INSERT INTO permissions (code, name, description)
SELECT 'page_designer:page:view', '查看页面设计', '查看已发布的页面设计运行时页面'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'page_designer:page:view');

INSERT INTO permissions (code, name, description)
SELECT 'page_designer:page:manage', '管理页面设计', '创建、编辑、发布和挂载页面设计'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'page_designer:page:manage');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'page-designer', 'platform', '页面设计', 'directory', '/page-designer', 'page-designer', '', 'DashboardOutlined', '', '', 860, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'page-designer');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'page-designer-pages', 'platform', '页面管理', 'page', '/page-designer/pages', 'page-designer-pages', '/page-designer/pages/index', 'DashboardOutlined', 'page-designer', 'page_designer:page:manage', 861, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'page-designer-pages');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'page-designer-create', 'platform', '新建页面', 'action', '', '', '', '', 'page-designer-pages', 'page_designer:page:manage', 8611, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'page-designer-create');

INSERT INTO menus (menu_key, menu_scope, label, menu_type, path, route_name, component, icon, parent_key, permission_code, sort_order, is_visible)
SELECT 'page-designer-publish', 'platform', '发布页面', 'action', '', '', '', '', 'page-designer-pages', 'page_designer:page:manage', 8612, TRUE
WHERE NOT EXISTS (SELECT 1 FROM menus WHERE menu_key = 'page-designer-publish');

UPDATE menus
SET menu_scope = 'platform'
WHERE menu_key IN ('page-designer', 'page-designer-pages', 'page-designer-create', 'page-designer-publish');

DELETE FROM tenant_menu_overrides
WHERE menu_key IN ('page-designer', 'page-designer-pages', 'page-designer-create', 'page-designer-publish');

UPDATE menus
SET parent_key = ''
WHERE menu_scope = 'tenant'
  AND parent_key = 'page-designer'
  AND menu_key LIKE 'page-designer-runtime-%';
