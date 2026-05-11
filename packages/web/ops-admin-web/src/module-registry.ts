import type { App } from 'vue';
import type { RouteRecordRaw } from 'vue-router';

export type OpsAdminModuleKey = 'identity_access' | 'appearance' | 'llm_runtime' | string;

export interface OpsAdminWebModule {
  key: OpsAdminModuleKey;
  label: string;
  menuKeys: string[];
  routes?: RouteRecordRaw[];
  install?: (app: App) => void;
}

export interface OpsAdminModuleOptions {
  label?: string;
  menuKeys?: string[];
  routes?: RouteRecordRaw[];
  install?: (app: App) => void;
}

const DEFAULT_MODULE_MENU_KEYS: Record<string, string[]> = {
  identity_access: [
    'platform-management',
    'platform-branding-update',
    'tenant-management',
    'tenant-management-create',
    'tenant-management-update',
    'tenant-management-activate',
    'tenant-management-suspend',
    'tenant-management-users-create',
    'tenant-management-users-update',
    'tenant-management-api-keys-create',
    'tenant-management-api-keys-revoke',
    'tenant-management-theme-assign',
    'rbac',
    'menu-management',
    'menu-management-create',
    'menu-management-update',
    'menu-management-delete',
    'role-management',
    'role-management-create',
    'role-management-update',
    'role-management-delete',
    'role-management-assign-menus',
    'user-management',
    'user-management-create',
    'user-management-update',
    'user-management-enable',
    'user-management-disable',
    'tenant-settings',
    'tenant-user-management',
    'tenant-users-create',
    'tenant-users-update',
    'tenant-users-enable',
    'tenant-users-disable',
    'tenant-api-keys',
    'tenant-api-keys-create',
    'tenant-api-keys-revoke',
    'api-keys',
  ],
  appearance: [
    'appearance-studio',
    'appearance-themes-create',
    'appearance-themes-update',
    'appearance-themes-publish',
    'appearance-themes-disable',
    'appearance-themes-set-default',
  ],
  llm_runtime: [
    'llm-config',
    'llm-providers-save',
    'llm-models-save',
    'llm-tasks-register',
    'llm-routing-policies-save',
    'llm-debug',
    'llm-debug-send',
  ],
  messaging: [
    'messaging',
    'message-inbox',
    'message-inbox-read',
    'message-inbox-unread',
    'message-inbox-delete',
    'message-outbox',
    'message-outbox-cancel',
    'message-send',
    'message-send-submit',
    'message-templates',
    'message-templates-create',
    'message-templates-update',
    'message-templates-enable',
    'message-templates-disable',
    'message-channels',
    'message-channels-create',
    'message-channels-update',
    'message-channels-enable',
    'message-channels-disable',
    'message-channels-test',
  ],
};

const modules = new Map<OpsAdminModuleKey, OpsAdminWebModule>();

function knownMenuKeys() {
  return new Set(Object.values(DEFAULT_MODULE_MENU_KEYS).flat());
}

export function registerOpsAdminModule(module: OpsAdminWebModule) {
  modules.set(module.key, {
    ...module,
    menuKeys: [...module.menuKeys],
  });
}

export function clearOpsAdminModules() {
  modules.clear();
}

export function registeredOpsAdminModules() {
  return Array.from(modules.values()).map((module) => ({
    ...module,
    menuKeys: [...module.menuKeys],
  }));
}

export function registeredOpsAdminMenuKeys() {
  return new Set(registeredOpsAdminModules().flatMap((module) => module.menuKeys));
}

export function isOpsAdminMenuAllowed(menuKey: string) {
  const normalized = String(menuKey || '').trim();
  if (!normalized) return true;
  if (!knownMenuKeys().has(normalized)) return true;
  return registeredOpsAdminMenuKeys().has(normalized);
}

export function registerIdentityAccessModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'identity_access',
    label: options.label || 'Identity Access',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.identity_access,
    routes: options.routes,
    install: options.install,
  });
}

export function registerAppearanceModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'appearance',
    label: options.label || 'Appearance',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.appearance,
    routes: options.routes,
    install: options.install,
  });
}

export function registerLlmRuntimeModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'llm_runtime',
    label: options.label || 'LLM Runtime',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.llm_runtime,
    routes: options.routes,
    install: options.install,
  });
}

export function registerMessagingModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'messaging',
    label: options.label || '消息系统',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.messaging,
    routes: options.routes,
    install: options.install,
  });
}
