import { Alova } from '@/utils/http/alova/index';
import { useGlobSetting } from '@/hooks/setting';
import { useUser } from '@/store/modules/user';

export interface ListQuery {
  q?: string;
  status?: string;
  request_id?: string;
  limit?: number;
  offset?: number;
}

export interface ApiKeyCreatePayload {
  name: string;
}

export interface ApiKeyUpdatePayload {
  name: string;
}

export interface TenantPayload {
  key?: string;
  tenant_key?: string;
  name: string;
  remark?: string;
  status?: string;
  admin_username?: string;
  admin_password?: string;
}

export interface RbacRoleCreatePayload {
  key: string;
  name: string;
  description?: string;
  role_scope?: 'platform' | 'tenant';
  menu_keys?: string[];
}

export interface RbacRoleUpdatePayload {
  key: string;
  name: string;
  description?: string;
  menu_keys?: string[];
}

export interface RbacUserCreatePayload {
  tenant_id?: number;
  username: string;
  full_name?: string;
  password: string;
  role_keys?: string[];
  department_ids?: number[] | null;
  primary_department_id?: number | null;
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface RbacUserUpdatePayload {
  tenant_id?: number;
  username: string;
  full_name?: string;
  password?: string;
  role_keys?: string[];
  department_ids?: number[] | null;
  primary_department_id?: number | null;
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface DepartmentPayload {
  id?: number;
  tenant_id?: number | null;
  parent_id?: number | null;
  code: string;
  name: string;
  manager_user_id?: number | null;
  base_location?: string;
  region?: string;
  status?: string;
  sort_order?: number;
}

export interface DataAccessPolicyPayload {
  tenant_id?: number | null;
  subject_type: 'user' | 'department' | string;
  subject_id: number;
  resource_key: string;
  action?: string;
  scope: string;
  department_ids?: number[];
  priority?: number;
}

export interface DataResourcePayload {
  resource_key: string;
  name: string;
  description?: string;
  tenant_column?: string;
  creator_column?: string;
  owner_user_column?: string;
  owner_department_column?: string;
  supported_scopes?: string[];
  requires_data_scope?: boolean;
}

export interface RbacMenuPayload {
  key: string;
  label: string;
  menu_scope?: 'platform' | 'tenant';
  menu_type: 'directory' | 'page' | 'action';
  path?: string;
  route_name?: string;
  component?: string;
  icon?: string;
  parent_key?: string;
  permission_code?: string;
  sort_order?: number;
  is_visible?: boolean;
}

export interface LlmConfigPayload {
  provider: string;
  model?: string;
  base_url?: string;
  api_key?: string;
  clear_api_key?: boolean;
  command?: string;
  timeout_seconds?: number;
  temperature?: number;
  extra_body?: Record<string, unknown>;
  enable_think_output?: boolean;
  enabled?: boolean;
}

export interface LlmProviderPayload {
  provider_key: string;
  display_name?: string;
  base_url?: string;
  api_key?: string;
  clear_api_key?: boolean;
  auth_type?: string;
  extra_headers?: Record<string, unknown>;
  extra_body?: Record<string, unknown>;
  enabled?: boolean;
}

export interface LlmModelPayload {
  model_key: string;
  provider_key: string;
  model_name: string;
  display_name?: string;
  capabilities?: Record<string, unknown>;
  context_window?: number | null;
  enabled?: boolean;
}

export interface LlmTaskPayload {
  task_key: string;
  context_key?: string;
  scene_key?: string;
  task_name?: string;
  display_name?: string;
  description?: string;
  owner_context?: string;
  enabled?: boolean;
}

export interface LlmRoutingEntryPayload {
  model_key: string;
  priority?: number;
  temperature?: number;
  timeout_seconds?: number;
  max_retries?: number;
  response_format?: string;
  extra_body?: Record<string, unknown>;
  enabled?: boolean;
}

export interface LlmRoutingPolicyPayload {
  route_key: string;
  display_name?: string;
  strategy?: string;
  enabled?: boolean;
  entries?: LlmRoutingEntryPayload[];
}

export interface OpenAIChatMessagePayload {
  role: string;
  content: string;
}

export interface OpenAIChatCompletionPayload {
  model: string;
  messages: OpenAIChatMessagePayload[];
  temperature?: number;
  response_format?: Record<string, unknown>;
  enable_think_output?: boolean;
  stream?: boolean;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export function getLlmConfig() {
  return Alova.Get('/llm-config', { params: withNoCacheParams() });
}

export function saveLlmConfig(payload: LlmConfigPayload) {
  return Alova.Put('/llm-config', payload);
}

export function getLlmProviders(params: PageParams & SortParams = {}) {
  return Alova.Get('/llm/providers', { params: withNoCacheParams(params) });
}

export function saveLlmProvider(payload: LlmProviderPayload) {
  return Alova.Post('/llm/providers', payload);
}

export function getLlmModels(params: PageParams & SortParams = {}) {
  return Alova.Get('/llm/models', { params: withNoCacheParams(params) });
}

export function saveLlmModel(payload: LlmModelPayload) {
  return Alova.Post('/llm/models', payload);
}

export function getLlmTasks(params: PageParams & SortParams = {}) {
  return Alova.Get('/llm/tasks', { params: withNoCacheParams(params) });
}

export function registerLlmTask(payload: LlmTaskPayload) {
  return Alova.Post('/llm/tasks/register', payload);
}

export function getLlmRoutingPolicies(params: PageParams & SortParams = {}) {
  return Alova.Get('/llm/routing-policies', { params: withNoCacheParams(params) });
}

export function saveLlmRoutingPolicy(payload: LlmRoutingPolicyPayload) {
  return Alova.Post('/llm/routing-policies', payload);
}

export function getLlmCallLogs(params: number | (PageParams & SortParams) = {}) {
  const requestParams = typeof params === 'number' ? { limit: params } : params;
  return Alova.Get('/llm/call-logs', {
    params: withNoCacheParams({
      page: requestParams.page ?? 1,
      page_size: requestParams.page_size ?? (typeof params === 'number' ? params : 20),
      sort_by: requestParams.sort_by,
      sort_dir: requestParams.sort_dir,
    }),
  });
}

export function getLlmOpenAIModels() {
  return Alova.Get('/llm/openai/v1/models', {
    params: withNoCacheParams(),
    meta: { isReturnNativeResponse: true },
  });
}

export function createLlmOpenAIChatCompletion(payload: OpenAIChatCompletionPayload) {
  return Alova.Post('/llm/openai/v1/chat/completions', payload, {
    meta: { isReturnNativeResponse: true },
  });
}

export function fetchLlmOpenAIChatCompletionStream(payload: OpenAIChatCompletionPayload) {
  return fetch(buildBusinessApiUrl('/llm/openai/v1/chat/completions'), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  }).catch((error) => {
    throw new Error(`LLM debug request failed to reach the backend: ${errorMessage(error)}`);
  });
}

function authHeaders() {
  const token = useUser().getToken;
  return token
    ? {
        token,
        Authorization: `Bearer ${token}`,
      }
    : {};
}

function buildBusinessApiUrl(path: string) {
  const { apiUrl, urlPrefix } = useGlobSetting();
  const base = trimTrailingSlashes(apiUrl || '');
  const prefix = normalizePathPart(urlPrefix || '');
  const endpoint = normalizePathPart(path);
  const relativeUrl = `/${[prefix, endpoint].filter(Boolean).join('/')}`;
  return base ? `${base}${relativeUrl}` : relativeUrl;
}

function trimTrailingSlashes(value: string) {
  return value.replace(/\/+$/, '');
}

function normalizePathPart(value: string) {
  return value.replace(/^\/+|\/+$/g, '');
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export interface SortParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

export interface PageParams {
  page?: number;
  page_size?: number;
}

export interface BusinessPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface BusinessListData<TItem = Recordable> {
  items: TItem[];
  pagination: BusinessPagination;
}

export function getApiKeys(params: PageParams & SortParams = {}) {
  return Alova.Get('/api-keys', { params: withNoCacheParams(params) });
}

export function createApiKey(payload: ApiKeyCreatePayload) {
  return Alova.Post('/api-keys', payload);
}

export function updateApiKey(keyId: number, payload: ApiKeyUpdatePayload) {
  return Alova.Put(`/api-keys/${keyId}`, payload);
}

export function revokeApiKey(keyId: number) {
  return Alova.Delete(`/api-keys/${keyId}`);
}

export function getTenants(params: { q?: string } & PageParams & SortParams = {}) {
  return Alova.Get('/tenants', { params: withNoCacheParams(params) });
}

export function createTenant(payload: TenantPayload) {
  return Alova.Post('/tenants', payload);
}

export function updateTenant(tenantId: number, payload: TenantPayload) {
  return Alova.Put(`/tenants/${tenantId}`, payload);
}

export function activateTenant(tenantId: number) {
  return Alova.Post(`/tenants/${tenantId}/activate`);
}

export function suspendTenant(tenantId: number) {
  return Alova.Post(`/tenants/${tenantId}/suspend`);
}

export function switchTenant(tenantId: number) {
  return Alova.Post('/auth/tenant/switch', { tenant_id: tenantId });
}

export function getTenantUsers(tenantId: number, params: PageParams & SortParams = {}) {
  return Alova.Get(`/tenants/${tenantId}/users`, { params: withNoCacheParams(params) });
}

export function getCurrentTenantUsers(params: PageParams & SortParams = {}) {
  return Alova.Get('/tenant/users', { params: withNoCacheParams(params) });
}

export function getCurrentTenantRoles(params: SortParams = {}) {
  return Alova.Get('/tenant/roles', { params: withNoCacheParams(params) });
}

export function createTenantUser(tenantId: number, payload: RbacUserCreatePayload & { is_tenant_admin?: boolean }) {
  return Alova.Post(`/tenants/${tenantId}/users`, payload);
}

export function createCurrentTenantUser(payload: RbacUserCreatePayload & { is_tenant_admin?: boolean }) {
  return Alova.Post('/tenant/users', payload);
}

export function updateTenantUser(
  tenantId: number,
  userId: number,
  payload: RbacUserUpdatePayload & { is_tenant_admin?: boolean }
) {
  return Alova.Put(`/tenants/${tenantId}/users/${userId}`, payload);
}

export function enableTenantUser(tenantId: number, userId: number) {
  return Alova.Post(`/tenants/${tenantId}/users/${userId}/enable`);
}

export function disableTenantUser(tenantId: number, userId: number) {
  return Alova.Post(`/tenants/${tenantId}/users/${userId}/disable`);
}

export function updateCurrentTenantUser(userId: number, payload: RbacUserUpdatePayload & { is_tenant_admin?: boolean }) {
  return Alova.Put(`/tenant/users/${userId}`, payload);
}

export function enableCurrentTenantUser(userId: number) {
  return Alova.Post(`/tenant/users/${userId}/enable`);
}

export function disableCurrentTenantUser(userId: number) {
  return Alova.Post(`/tenant/users/${userId}/disable`);
}

export function getTenantApiKeys(tenantId: number, params: PageParams & SortParams = {}) {
  return Alova.Get(`/tenants/${tenantId}/api-keys`, { params: withNoCacheParams(params) });
}

export function getCurrentTenantApiKeys(params: PageParams & SortParams = {}) {
  return Alova.Get('/tenant/api-keys', { params: withNoCacheParams(params) });
}

export function createTenantApiKey(tenantId: number, payload: ApiKeyCreatePayload) {
  return Alova.Post(`/tenants/${tenantId}/api-keys`, payload);
}

export function createCurrentTenantApiKey(payload: ApiKeyCreatePayload) {
  return Alova.Post('/tenant/api-keys', payload);
}

export function updateTenantApiKey(tenantId: number, keyId: number, payload: ApiKeyUpdatePayload) {
  return Alova.Put(`/tenants/${tenantId}/api-keys/${keyId}`, payload);
}

export function updateCurrentTenantApiKey(keyId: number, payload: ApiKeyUpdatePayload) {
  return Alova.Put(`/tenant/api-keys/${keyId}`, payload);
}

export function revokeTenantApiKey(tenantId: number, keyId: number) {
  return Alova.Delete(`/tenants/${tenantId}/api-keys/${keyId}`);
}

export function revokeCurrentTenantApiKey(keyId: number) {
  return Alova.Delete(`/tenant/api-keys/${keyId}`);
}

export function getRbacMenus(params: { scope?: 'platform' | 'tenant' } & SortParams = {}) {
  return Alova.Get('/rbac/menus', { params: withNoCacheParams(params) });
}

export function createRbacMenu(payload: RbacMenuPayload) {
  return Alova.Post('/rbac/menus', payload);
}

export function updateRbacMenu(menuId: number, payload: RbacMenuPayload) {
  return Alova.Put(`/rbac/menus/${menuId}`, payload);
}

export function deleteRbacMenu(menuId: number) {
  return Alova.Delete(`/rbac/menus/${menuId}`);
}

export function getRbacRoles(params: PageParams & SortParams = {}) {
  return Alova.Get('/rbac/roles', { params: withNoCacheParams(params) });
}

export function createRbacRole(payload: RbacRoleCreatePayload) {
  return Alova.Post('/rbac/roles', payload);
}

export function updateRbacRole(roleId: number, payload: RbacRoleUpdatePayload) {
  return Alova.Put(`/rbac/roles/${roleId}`, payload);
}

export function updateRbacRoleMenus(roleId: number, menuKeys: string[]) {
  return Alova.Put(`/rbac/roles/${roleId}/menus`, { menu_keys: menuKeys });
}

export function deleteRbacRole(roleId: number) {
  return Alova.Delete(`/rbac/roles/${roleId}`);
}

export function getRbacUsers(params: PageParams & SortParams = {}) {
  return Alova.Get('/rbac/users', { params: withNoCacheParams(params) });
}

export function createRbacUser(payload: RbacUserCreatePayload) {
  return Alova.Post('/rbac/users', payload);
}

export function updateRbacUser(userId: number, payload: RbacUserUpdatePayload) {
  return Alova.Put(`/rbac/users/${userId}`, payload);
}

export function enableRbacUser(userId: number) {
  return Alova.Post(`/rbac/users/${userId}/enable`);
}

export function disableRbacUser(userId: number) {
  return Alova.Post(`/rbac/users/${userId}/disable`);
}

export function getDepartments(params: { include_disabled?: boolean; tenant_id?: number | null } & SortParams = {}) {
  return Alova.Get('/organization/departments', { params: withNoCacheParams(params) });
}

export function createDepartment(payload: DepartmentPayload) {
  return Alova.Post('/organization/departments', payload);
}

export function updateDepartment(departmentId: number, payload: DepartmentPayload) {
  return Alova.Put(`/organization/departments/${departmentId}`, payload);
}

export function deleteDepartment(departmentId: number, params: { tenant_id?: number | null } = {}) {
  return Alova.Delete(`/organization/departments/${departmentId}`, { params: withNoCacheParams(params) });
}

export function getAuthorizationResources(params: SortParams = {}) {
  return Alova.Get('/authorization/resources', { params: withNoCacheParams(params) });
}

export function saveAuthorizationResource(resourceKey: string, payload: DataResourcePayload) {
  return Alova.Put(`/authorization/resources/${resourceKey}`, payload);
}

export function getDataAccessPolicies(
  params: { subject_type?: string; subject_id?: number; resource_key?: string; tenant_id?: number | null } & PageParams & SortParams = {}
) {
  return Alova.Get('/authorization/data-access-policies', { params: withNoCacheParams(params) });
}

export function saveDataAccessPolicy(payload: DataAccessPolicyPayload) {
  return Alova.Post('/authorization/data-access-policies', payload);
}

export function deleteDataAccessPolicy(policyId: number, params: { tenant_id?: number | null } = {}) {
  return Alova.Delete(`/authorization/data-access-policies/${policyId}`, { params: withNoCacheParams(params) });
}
