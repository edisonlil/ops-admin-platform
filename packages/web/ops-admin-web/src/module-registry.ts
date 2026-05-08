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
    'tenant-management',
    'rbac',
    'menu-management',
    'role-management',
    'user-management',
    'tenant-settings',
    'tenant-user-management',
    'tenant-api-keys',
    'api-keys',
  ],
  appearance: ['appearance-studio'],
  llm_runtime: ['llm-config', 'llm-debug'],
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
