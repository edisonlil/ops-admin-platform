import { Alova } from '@/utils/http/alova/index';
import { useGlobSetting } from '@/hooks/setting';
import { useUser } from '@/store/modules/user';

export interface AiPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface AiListData<TItem> {
  items: TItem[];
  pagination: AiPagination;
}

export interface AiQuota {
  tenant_id: number;
  max_applications: number;
  max_capabilities: number;
  max_assets: number;
  daily_run_limit: number;
  monthly_token_limit: number;
  enabled: boolean;
  usage: {
    applications: number;
    capabilities?: number;
  };
}

export interface AiApplication {
  id: number;
  tenant_id: number;
  app_key: string;
  name: string;
  description: string;
  app_type: string;
  status: string;
  endpoint_slug: string;
  system_prompt: string;
  developer_prompt: string;
  user_prompt_template: string;
  variables_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  model_preferences: Record<string, unknown>;
  auth_policy: Record<string, unknown>;
  quota_policy: Record<string, unknown>;
  trace_policy: Record<string, unknown>;
  runtime_config: Record<string, unknown>;
  published_time?: string | null;
  create_time?: string;
  update_time?: string;
}

export interface RuntimeTrace {
  trace_id: string;
  caller_type: string;
  caller_key: string;
  app_key: string;
  app_version: string;
  route_key: string;
  model_key: string;
  provider_key: string;
  status: string;
  input_variables: Record<string, unknown>;
  rendered_messages: Array<Record<string, unknown>>;
  rendered_prompt: string;
  answer: string;
  usage: Record<string, unknown>;
  elapsed_ms: number;
  error_code: string;
  error_message: string;
  request_id: string;
  correlation_id: string;
  create_time?: string;
}

export interface AiApplicationRunLog {
  run_id: string;
  trace_id: string;
  app_key: string;
  app_version: string;
  run_mode: string;
  status: string;
  model: string;
  input_variables: Record<string, unknown>;
  answer: string;
  usage: Record<string, unknown>;
  elapsed_ms: number;
  error_code: string;
  error_message: string;
  request_id: string;
  create_time?: string;
}

export interface AiStudioOverview {
  stats: {
    applications: number;
    published_applications: number;
    recent_runs: number;
  };
  quota: AiQuota;
  applications: AiApplication[];
  recent_traces: RuntimeTrace[];
  app_types: Array<{ type: string; label: string; enabled: boolean }>;
}

export interface AiApplicationPayload {
  app_key: string;
  name: string;
  icon?: string;
  description?: string;
  app_type?: string;
  status?: string;
  endpoint_slug?: string;
  system_prompt?: string;
  developer_prompt?: string;
  user_prompt_template?: string;
  variables_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  model_preferences?: Record<string, unknown>;
  auth_policy?: Record<string, unknown>;
  quota_policy?: Record<string, unknown>;
  trace_policy?: Record<string, unknown>;
  runtime_config?: Record<string, unknown>;
}

export interface AiCapability {
  id: number;
  tenant_id: number;
  capability_key: string;
  name: string;
  description: string;
  scope: string;
  binding_type: string;
  binding_key: string;
  call_method: string;
  system_prompt: string;
  developer_prompt: string;
  user_prompt_template: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  model_preferences: Record<string, unknown>;
  runtime_config: Record<string, unknown>;
  enabled: boolean;
  create_time?: string;
  update_time?: string;
}

export interface AiCapabilityPayload {
  capability_key: string;
  name: string;
  description?: string;
  scope?: string;
  binding_type?: string;
  binding_key?: string;
  call_method?: string;
  system_prompt?: string;
  developer_prompt?: string;
  user_prompt_template?: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  model_preferences?: Record<string, unknown>;
  runtime_config?: Record<string, unknown>;
  enabled?: boolean;
}

export interface AiRunPayload {
  variables: Record<string, unknown>;
  model?: string;
  temperature?: number;
  response_format?: Record<string, unknown>;
  extra_body?: Record<string, unknown>;
  enable_think_output?: boolean;
}

export interface AiRunResult {
  answer: string;
  trace_id: string;
  usage: Record<string, unknown>;
  trace?: RuntimeTrace;
}

export interface TenantAiQuotaPayload {
  max_applications: number;
  max_capabilities: number;
  max_assets: number;
  daily_run_limit: number;
  monthly_token_limit: number;
  enabled: boolean;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export function getAiStudioOverview() {
  return Alova.Get<AiStudioOverview>('/ai-studio/overview', { params: withNoCacheParams() });
}

export function getAiApplications() {
  return Alova.Get<AiListData<AiApplication>>('/ai-applications', { params: withNoCacheParams() });
}

export function getAiCapabilities() {
  return Alova.Get<AiListData<AiCapability>>('/ai-capabilities', { params: withNoCacheParams() });
}

export function getAiCapability(capabilityKey: string) {
  return Alova.Get<AiCapability>(`/ai-capabilities/${capabilityKey}`, { params: withNoCacheParams() });
}

export function getAiCapabilityModelOptions() {
  return Alova.Get<AiListData<Record<string, unknown>>>('/ai-capabilities/model-options', {
    params: withNoCacheParams(),
  });
}

export function getAiApplication(appKey: string) {
  return Alova.Get<AiApplication>(`/ai-applications/${appKey}`, { params: withNoCacheParams() });
}

export function getAiApplicationRunLogs(appKey: string, limit = 50) {
  return Alova.Get<AiListData<AiApplicationRunLog>>(`/ai-studio/applications/${appKey}/run-logs`, {
    params: withNoCacheParams({ limit }),
  });
}

export function getAiCapabilityRunLogs(capabilityKey: string, limit = 50) {
  return Alova.Get<AiListData<AiApplicationRunLog>>(`/ai-studio/capabilities/${capabilityKey}/run-logs`, {
    params: withNoCacheParams({ limit }),
  });
}

export function saveAiApplication(payload: AiApplicationPayload) {
  const runtimeConfig = {
    ...(payload.runtime_config || {}),
    icon: payload.icon || String(payload.runtime_config?.icon || 'robot'),
  };
  const body: AiApplicationPayload = {
    app_key: String(payload.app_key || '').trim(),
    name: String(payload.name || '').trim(),
    description: payload.description || '',
    app_type: payload.app_type || 'single_turn_generation',
    status: payload.status || 'draft',
    endpoint_slug: payload.endpoint_slug || payload.app_key,
    system_prompt: payload.system_prompt || '',
    developer_prompt: payload.developer_prompt || '',
    user_prompt_template: payload.user_prompt_template || '',
    variables_schema: payload.variables_schema || {},
    output_schema: payload.output_schema || {},
    model_preferences: payload.model_preferences || {},
    auth_policy: payload.auth_policy || {},
    quota_policy: payload.quota_policy || {},
    trace_policy: payload.trace_policy || { enabled: true },
    runtime_config: runtimeConfig,
  };
  return Alova.Post<AiApplication>('/ai-applications', body);
}

export function updateAiApplication(appKey: string, payload: AiApplicationPayload) {
  const body = {
    ...payload,
    runtime_config: {
      ...(payload.runtime_config || {}),
      icon: payload.icon || String(payload.runtime_config?.icon || 'robot'),
    },
  };
  return Alova.Put<AiApplication>(`/ai-applications/${appKey}`, body);
}

export function saveAiCapability(payload: AiCapabilityPayload) {
  const body: AiCapabilityPayload = {
    capability_key: String(payload.capability_key || '').trim(),
    name: String(payload.name || '').trim(),
    description: payload.description || '',
    scope: payload.scope || 'tenant',
    binding_type: payload.binding_type || 'prompt_runtime',
    binding_key: String(payload.binding_key || payload.capability_key || '').trim(),
    call_method: payload.call_method || 'aiService.execute',
    system_prompt: payload.system_prompt || '',
    developer_prompt: payload.developer_prompt || '',
    user_prompt_template: payload.user_prompt_template || '',
    input_schema: payload.input_schema || {},
    output_schema: payload.output_schema || {},
    model_preferences: payload.model_preferences || {},
    runtime_config: payload.runtime_config || {},
    enabled: payload.enabled ?? true,
  };
  return Alova.Post<AiCapability>('/ai-capabilities', body);
}

export function updateAiCapability(capabilityKey: string, payload: AiCapabilityPayload) {
  return Alova.Put<AiCapability>(`/ai-capabilities/${capabilityKey}`, payload);
}

export function publishAiApplication(appKey: string) {
  return Alova.Post<AiApplication>(`/ai-applications/${appKey}/publish`);
}

export function runAiApplicationDraft(appKey: string, payload: AiRunPayload) {
  return Alova.Post<AiRunResult>(`/ai-applications/${appKey}/run-draft`, payload);
}

export function fetchAiApplicationDraftStream(appKey: string, payload: AiRunPayload) {
  return fetch(buildAiStudioApiUrl(`/ai-applications/${encodeURIComponent(appKey)}/run-draft/stream`), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  }).catch((error) => {
    throw new Error(`AI application stream request failed: ${errorMessage(error)}`);
  });
}

export function fetchAiCapabilityStream(capabilityKey: string, payload: AiRunPayload) {
  return fetch(buildAiStudioApiUrl(`/ai-capabilities/${encodeURIComponent(capabilityKey)}/execute/stream`), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  }).catch((error) => {
    throw new Error(`AI capability stream request failed: ${errorMessage(error)}`);
  });
}

export function getAiRuntimeTraces(limit = 50) {
  return Alova.Get<AiListData<RuntimeTrace>>('/ai-runtime/prompt-runtime/traces', {
    params: withNoCacheParams({ limit }),
  });
}

export function getTenantAiQuota() {
  return Alova.Get<AiQuota>('/tenant-ai-quota', { params: withNoCacheParams() });
}

export function getAdminTenantAiQuota(tenantId: number) {
  return Alova.Get<AiQuota>(`/admin/tenants/${tenantId}/ai-quota`, { params: withNoCacheParams() });
}

export function saveAdminTenantAiQuota(tenantId: number, payload: TenantAiQuotaPayload) {
  return Alova.Put<AiQuota>(`/admin/tenants/${tenantId}/ai-quota`, payload);
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

function buildAiStudioApiUrl(path: string) {
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
