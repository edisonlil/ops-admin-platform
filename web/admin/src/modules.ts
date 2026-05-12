import {
  clearOpsAdminModules,
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
}
