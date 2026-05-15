import { Alova } from '@/utils/http/alova/index';

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
  return Alova.Get<AiListData<AiApplication>>('/llm/ai-applications', { params: withNoCacheParams() });
}

export function getAiApplication(appKey: string) {
  return Alova.Get<AiApplication>(`/llm/ai-applications/${appKey}`, { params: withNoCacheParams() });
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
  return Alova.Post<AiApplication>('/llm/ai-applications', body);
}

export function updateAiApplication(appKey: string, payload: AiApplicationPayload) {
  const body = {
    ...payload,
    runtime_config: {
      ...(payload.runtime_config || {}),
      icon: payload.icon || String(payload.runtime_config?.icon || 'robot'),
    },
  };
  return Alova.Put<AiApplication>(`/llm/ai-applications/${appKey}`, body);
}

export function publishAiApplication(appKey: string) {
  return Alova.Post<AiApplication>(`/llm/ai-applications/${appKey}/publish`);
}

export function runAiApplicationDraft(appKey: string, payload: AiRunPayload) {
  return Alova.Post<AiRunResult>(`/llm/ai-applications/${appKey}/run-draft`, payload);
}

export function getAiRuntimeTraces(limit = 50) {
  return Alova.Get<AiListData<RuntimeTrace>>('/llm/prompt-runtime/traces', {
    params: withNoCacheParams({ limit }),
  });
}

export function getTenantAiQuota() {
  return Alova.Get<AiQuota>('/llm/tenant-ai-quota', { params: withNoCacheParams() });
}

export function getAdminTenantAiQuota(tenantId: number) {
  return Alova.Get<AiQuota>(`/llm/admin/tenants/${tenantId}/ai-quota`, { params: withNoCacheParams() });
}

export function saveAdminTenantAiQuota(tenantId: number, payload: TenantAiQuotaPayload) {
  return Alova.Put<AiQuota>(`/llm/admin/tenants/${tenantId}/ai-quota`, payload);
}
