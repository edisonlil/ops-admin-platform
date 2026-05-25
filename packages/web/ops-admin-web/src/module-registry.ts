import type { App } from 'vue';
import type { RouteRecordRaw } from 'vue-router';

export type OpsAdminModuleKey =
  | 'identity_access'
  | 'appearance'
  | 'llm_runtime'
  | 'basic_data'
  | 'page_designer'
  | 'file_management'
  | 'ai_assets'
  | 'audit_logging'
  | string;

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
    'platform-branding',
    'platform-branding-update',
    'platform-audit-logs',
    'platform-audit-system-logs',
    'platform-audit-operation-logs',
    'platform-audit-api-logs',
    'platform-audit-sql-logs',
    'platform-audit-visitor-logs',
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
    'menu-tenant-assignment',
    'menu-tenant-assignment-save',
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
    'message-chat-bots',
    'message-chat-bots-create',
    'message-chat-bots-update',
    'message-chat-bots-enable',
    'message-chat-bots-disable',
    'message-chat-bots-test',
  ],
  cron: [
    'cron',
    'cron-tasks',
    'cron-tasks-create',
    'cron-tasks-update',
    'cron-tasks-enable',
    'cron-tasks-disable',
    'cron-tasks-delete',
    'cron-tasks-trigger',
    'cron-runs',
    'cron-runs-stop',
    'cron-runs-delete',
  ],
  file_management: [
    'file-management',
    'file-libraries',
    'file-libraries-create',
    'file-libraries-update',
    'file-libraries-delete',
    'file-objects',
    'file-objects-upload',
    'file-objects-delete',
    'file-storage-profiles',
    'file-storage-profiles-manage',
    'file-preview-profiles',
    'file-preview-profiles-manage',
    'file-tenant-quotas',
    'file-tenant-quotas-manage',
  ],
  ai_assets: [
    'ai-assets',
    'prompt-library',
    'prompt-library-manage',
    'skill-library',
    'skill-library-manage',
  ],
  basic_data: [
    'basic-data',
    'basic-data-dictionaries',
    'basic-data-dictionaries-create',
    'basic-data-dictionaries-update',
    'basic-data-dictionaries-delete',
    'basic-data-items-create',
    'basic-data-items-update',
    'basic-data-items-delete',
    'basic-data-regions',
    'basic-data-regions-create',
    'basic-data-regions-update',
    'basic-data-regions-delete',
    'basic-data-regions-import',
  ],
  page_designer: [
    'page-designer',
    'page-designer-pages',
    'page-designer-create',
    'page-designer-publish',
  ],
  audit_logging: [
    'audit-logs',
  ],
};

const RETIRED_MODULE_MENU_KEYS = [
  'prompt-contracts',
  'prompt-contracts-manage',
  'prompt-bindings',
  'prompt-bindings-manage',
  'prompt-runs',
];

const modules = new Map<OpsAdminModuleKey, OpsAdminWebModule>();

function knownMenuKeys() {
  return new Set([...Object.values(DEFAULT_MODULE_MENU_KEYS).flat(), ...RETIRED_MODULE_MENU_KEYS]);
}

export function registerOpsAdminModule(module: OpsAdminWebModule) {
  modules.set(module.key, {
    ...module,
    menuKeys: [...module.menuKeys],
  });
}

export function registerCronModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'cron',
    label: options.label || '定时任务',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.cron,
    routes: options.routes,
    install: options.install,
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

export function registerBasicDataModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'basic_data',
    label: options.label || '基础数据',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.basic_data,
    routes: options.routes,
    install: options.install,
  });
}

export function registerPageDesignerModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'page_designer',
    label: options.label || '页面设计',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.page_designer,
    routes: options.routes,
    install: options.install,
  });
}

export function registerMessagingModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'messaging',
    label: options.label || '消息中心',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.messaging,
    routes: options.routes,
    install: options.install,
  });
}

export function registerFileManagementModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'file_management',
    label: options.label || '文件管理',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.file_management,
    routes: options.routes,
    install: options.install,
  });
}

export function registerAIAssetsModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'ai_assets',
    label: options.label || 'AI 资产',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.ai_assets,
    routes: options.routes,
    install: options.install,
  });
}

export function registerAuditLoggingModule(options: OpsAdminModuleOptions = {}) {
  registerOpsAdminModule({
    key: 'audit_logging',
    label: options.label || '审计日志',
    menuKeys: options.menuKeys || DEFAULT_MODULE_MENU_KEYS.audit_logging,
    routes: options.routes,
    install: options.install,
  });
}
