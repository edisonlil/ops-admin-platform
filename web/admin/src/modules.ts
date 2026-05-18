import {
  clearOpsAdminModules,
  registerAIAssetsModule,
  registerAuditLoggingModule,
  registerBasicDataModule,
  registerCronModule,
  registerAppearanceModule,
  registerFileManagementModule,
  registerIdentityAccessModule,
  registerLlmRuntimeModule,
  registerMessagingModule,
} from '@edisonlil/ops-admin-web';

export function setupStarterModules() {
  clearOpsAdminModules();
  registerIdentityAccessModule();
  registerAppearanceModule();
  if (import.meta.env.VITE_ENABLE_BASIC_DATA !== 'false') {
    registerBasicDataModule();
  }

  if (import.meta.env.VITE_ENABLE_MESSAGING !== 'false') {
    registerMessagingModule();
  }

  if (import.meta.env.VITE_ENABLE_CRON !== 'false') {
    registerCronModule();
  }

  if (import.meta.env.VITE_ENABLE_FILE_MANAGEMENT !== 'false') {
    registerFileManagementModule();
  }

  if (import.meta.env.VITE_ENABLE_LLM_RUNTIME !== 'false') {
    registerLlmRuntimeModule();
  }

  if (import.meta.env.VITE_ENABLE_AI_ASSETS !== 'false') {
    registerAIAssetsModule();
  }

  if (import.meta.env.VITE_ENABLE_AUDIT_LOGGING !== 'false') {
    registerAuditLoggingModule();
  }
}
