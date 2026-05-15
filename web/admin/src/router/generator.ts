import { constantRouterIcon } from './icons';
import { RouteRecordRaw } from 'vue-router';
import { Layout, ParentLayout } from '@/router/constant';
import type { AppRouteRecordRaw } from '@/router/types';
import { filterOpsAdminMenuTree, isOpsAdminMenuAllowed } from '@edisonlil/ops-admin-web';

const Iframe = () => import('@/views/iframe/index.vue');
const LayoutMap = new Map<string, () => Promise<typeof import('*.vue')>>();

LayoutMap.set('LAYOUT', Layout);
LayoutMap.set('IFRAME', Iframe);

interface BackendMenu {
  key: string;
  label?: string;
  menu_type?: 'directory' | 'page' | 'action';
  path?: string;
  route_name?: string;
  component?: string;
  icon?: string;
  permission_code?: string;
  sort_order?: number;
  is_visible?: boolean;
  children?: BackendMenu[];
}

interface BackendRoute {
  path: string;
  name: string;
  component: string;
  redirect?: string;
  meta: {
    title: string;
    icon?: string;
    permissions?: string[];
    activeMenu?: string;
    hidden?: boolean;
  };
  children?: BackendRoute[];
}

const LEGACY_ICON_BY_KEY_OR_ALIAS: Record<string, string> = {
  api: 'ApiOutlined',
  key: 'ApiOutlined',
  menu: 'MenuOutlined',
  settings: 'SettingOutlined',
  'llm-config': 'SettingOutlined',
  'llm-debug': 'ExperimentOutlined',
  'api-keys': 'ApiOutlined',
  messaging: 'MessageOutlined',
  message: 'MessageOutlined',
  'message-inbox': 'MessageOutlined',
  'message-outbox': 'FileSearchOutlined',
  'message-send': 'MessageOutlined',
  'message-templates': 'FileTextOutlined',
  'message-channels': 'ApiOutlined',
  cron: 'ScheduleOutlined',
  'cron-tasks': 'ScheduleOutlined',
  'cron-runs': 'FileSearchOutlined',
  ScheduleOutlined: 'ScheduleOutlined',
  'file-text': 'FileTextOutlined',
  'tenant-settings': 'SettingOutlined',
  organization: 'ApartmentOutlined',
  'organization-departments': 'ApartmentOutlined',
  'tenant-user-management': 'UserOutlined',
  'tenant-api-keys': 'ApiOutlined',
  'tenant-management': 'ApartmentOutlined',
  'platform-management': 'SettingOutlined',
  'platform-branding': 'SettingOutlined',
  'appearance-studio': 'BgColorsOutlined',
  rbac: 'SafetyCertificateOutlined',
  'menu-management': 'MenuOutlined',
  'role-management': 'TeamOutlined',
  'user-management': 'UserOutlined',
  'data-scope-management': 'SafetyCertificateOutlined',
  shield: 'SafetyCertificateOutlined',
  users: 'TeamOutlined',
  user: 'UserOutlined',
  experiment: 'ExperimentOutlined',
};

function stripLeadingSlash(value: string) {
  return value.replace(/^\/+/, '');
}

function normalizeAbsolutePath(value: string, fallback: string) {
  const path = value.trim() || fallback;
  return path.startsWith('/') ? path : `/${path}`;
}

function childPath(path: string, parentPath: string) {
  const normalized = normalizeAbsolutePath(path, '');
  if (parentPath && normalized.startsWith(`${parentPath}/`)) {
    return normalized.slice(parentPath.length + 1) || 'index';
  }
  return stripLeadingSlash(normalized) || 'index';
}

function routeName(menu: BackendMenu) {
  return String(menu.route_name || menu.key || '').trim();
}

function routeIcon(menu: BackendMenu) {
  const icon = String(menu.icon || '').trim();
  return LEGACY_ICON_BY_KEY_OR_ALIAS[icon] || LEGACY_ICON_BY_KEY_OR_ALIAS[menu.key] || icon || 'DashboardOutlined';
}

function routeMeta(menu: BackendMenu) {
  const permissionCode = String(menu.permission_code || '').trim();
  return {
    title: String(menu.label || menu.key || ''),
    icon: routeIcon(menu),
    ...(permissionCode ? { permissions: [permissionCode] } : {}),
  };
}

function visibleSortedMenus(items: BackendMenu[] = []) {
  return items
    .filter((item) => item.is_visible !== false && item.menu_type !== 'action')
    .slice()
    .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0));
}

function moduleVisibleMenus(items: BackendMenu[] = []) {
  return filterOpsAdminMenuTree(visibleSortedMenus(items), isOpsAdminMenuAllowed) as BackendMenu[];
}

function menuToBackendRoute(menu: BackendMenu, parentPath = ''): BackendRoute {
  const key = String(menu.key || '').trim();
  const children = visibleSortedMenus(menu.children);
  const isDirectory = menu.menu_type === 'directory' || children.length > 0;

  if (isDirectory) {
    const groupPath = normalizeAbsolutePath(String(menu.path || ''), `/${key}`);
    const childRoutes = children.map((child) => menuToBackendRoute(child, groupPath));
    const route: BackendRoute = {
      path: parentPath ? childPath(groupPath, parentPath) : groupPath,
      name: routeName(menu) || key,
      component: 'LAYOUT',
      meta: routeMeta(menu),
      children: childRoutes,
    };
    if (childRoutes.length) {
      route.redirect = `${groupPath}/${childRoutes[0].path}`.replace('//', '/');
    }
    return route;
  }

  const pagePath = normalizeAbsolutePath(String(menu.path || ''), `/${key}`);
  const leaf: BackendRoute = {
    path: parentPath ? childPath(pagePath, parentPath) : 'index',
    name: routeName(menu) || key,
    component: String(menu.component || '').trim() || '/exception/404',
    meta: routeMeta(menu),
  };

  if (parentPath) {
    return leaf;
  }

  const pageChildren = [leaf];
  if (key === 'ai-studio') {
    pageChildren.push({
      path: 'apps/:appKey',
      name: 'ai-studio-app-detail',
      component: '/ai/studio/detail',
      meta: {
        title: 'AI 应用配置',
        permissions: ['ai_studio:access'],
        activeMenu: routeName(menu) || key,
        hidden: true,
      },
    });
  }

  return {
    path: pagePath,
    name: `${routeName(menu) || key}_root`,
    component: 'LAYOUT',
    redirect: `${pagePath}/index`,
    meta: routeMeta(menu),
    children: pageChildren,
  };
}

export const generateRoutes = (routerMap, parent?): any[] => {
  return routerMap.map((item) => {
    const currentRoute: any = {
      path: `${(parent && parent.path) ?? ''}/${item.path}`,
      name: item.name ?? '',
      component: item.component,
      meta: {
        ...item.meta,
        label: item.meta.title,
        icon: constantRouterIcon[item.meta.icon] || null,
        permissions: item.meta.permissions || null,
      },
    };

    currentRoute.path = currentRoute.path.replace('//', '/');
    item.redirect && (currentRoute.redirect = item.redirect);
    if (item.children && item.children.length > 0) {
      !item.redirect && (currentRoute.redirect = `${item.path}/${item.children[0].path}`);
      currentRoute.children = generateRoutes(item.children, currentRoute);
    }
    return currentRoute;
  });
};

export const generateDynamicRoutes = async (menus: BackendMenu[] = []): Promise<RouteRecordRaw[]> => {
  const backendRoutes = moduleVisibleMenus(menus).map((menu) => menuToBackendRoute(menu));
  const router = generateRoutes(backendRoutes);
  asyncImportRoute(router);
  return router;
};

let viewsModules: Record<string, () => Promise<Recordable>>;
export const asyncImportRoute = (routes: AppRouteRecordRaw[] | undefined): void => {
  viewsModules = viewsModules || import.meta.glob('../views/**/*.{vue,tsx}');
  if (!routes) return;
  routes.forEach((item) => {
    if (!item.component && item.meta?.frameSrc) {
      item.component = 'IFRAME';
    }
    const { component, name } = item;
    const { children } = item;
    if (component) {
      const layoutFound = LayoutMap.get(component as string);
      if (layoutFound) {
        item.component = layoutFound;
      } else {
        item.component = dynamicImport(viewsModules, component as string);
      }
    } else if (name) {
      item.component = ParentLayout;
    }
    children && asyncImportRoute(children);
  });
};

export const dynamicImport = (
  viewsModules: Record<string, () => Promise<Recordable>>,
  component: string
) => {
  const keys = Object.keys(viewsModules);
  const matchKeys = keys.filter((key) => {
    let k = key.replace('../views', '');
    const lastIndex = k.lastIndexOf('.');
    k = k.substring(0, lastIndex);
    return k === component;
  });
  if (matchKeys?.length === 1) {
    const matchKey = matchKeys[0];
    return viewsModules[matchKey];
  }
  if (matchKeys?.length > 1) {
    console.warn(
      'Please do not create `.vue` and `.TSX` files with the same file name in the same hierarchical directory under the views folder. This will cause dynamic introduction failure'
    );
    return;
  }
};
