export interface OpsAdminUser {
  id?: number | string;
  username: string;
  tenant_key?: string;
  auth_scope?: 'platform' | 'tenant' | string;
  is_platform_admin?: boolean;
  is_tenant_admin?: boolean;
  menus?: unknown[];
  permissions?: string[];
  token?: string;
}

export interface OpsAdminAuthSession {
  token: string;
  user: OpsAdminUser;
}

export interface OpsAdminAuthStorage {
  getToken: () => string | undefined;
  setToken: (token: string) => void;
  clear: () => void;
}
