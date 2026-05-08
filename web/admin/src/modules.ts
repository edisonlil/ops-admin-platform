import {
  clearOpsAdminModules,
  registerAppearanceModule,
  registerIdentityAccessModule,
  registerLlmRuntimeModule,
} from '@edisonlil/ops-admin-web';

export function setupStarterModules() {
  clearOpsAdminModules();
  registerIdentityAccessModule();
  registerAppearanceModule();

  if (import.meta.env.VITE_ENABLE_LLM_RUNTIME !== 'false') {
    registerLlmRuntimeModule();
  }
}
