import type { App } from 'vue';

export type OpsAdminStoreInstaller = (app: App<Element>) => void;

export interface OpsAdminStoreModule {
  key: string;
  install?: OpsAdminStoreInstaller;
}
