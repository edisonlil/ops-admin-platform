import { Alova } from '@/utils/http/alova/index';

export interface AuditPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface AuditLogRow {
  id: number;
  tenant_id: number;
  category: AuditLogCategory;
  event_time: string;
  request_id: string;
  event_action: string;
  event_outcome: string;
  severity: string;
  source_module: string;
  actor_user_id?: number | null;
  actor_name: string;
  client_ip: string;
  request_method?: string;
  request_path?: string;
  status_code?: number;
  duration_ms?: number;
  sql_template?: string;
  database_backend?: string;
  resource_type?: string;
  resource_id?: string;
  risk_level?: string;
  summary: string;
  error_message?: string;
  create_time?: string;
}

export type AuditLogCategory = 'system' | 'operation' | 'api' | 'sql' | 'visitor';

export interface AuditLogListData {
  items: AuditLogRow[];
  pagination: AuditPagination;
}

export interface AuditLoggingSettings {
  id: number;
  tenant_id: number;
  api_log_enabled: boolean;
  operation_log_enabled: boolean;
  sql_log_enabled: boolean;
  visitor_log_enabled: boolean;
  system_log_enabled: boolean;
  slow_sql_threshold_ms: number;
  queue_max_size: number;
  batch_size: number;
  flush_interval_ms: number;
  plaintext_ip_retention_days: number;
  log_retention_days: number;
  include_request_headers: boolean;
  include_response_body: boolean;
  external_sink_enabled: boolean;
  external_sink_type: string;
  config: Record<string, unknown>;
  create_time?: string;
  update_time?: string;
}

export type AuditLoggingSettingsPayload = Omit<AuditLoggingSettings, 'id' | 'tenant_id' | 'create_time' | 'update_time'>;

const pathByCategory: Record<AuditLogCategory, string> = {
  system: '/audit-logs/system',
  operation: '/audit-logs/operations',
  api: '/audit-logs/apis',
  sql: '/audit-logs/sql',
  visitor: '/audit-logs/visitors',
};

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export function getAuditLogs(
  category: AuditLogCategory,
  params: { page?: number; page_size?: number; keyword?: string; outcome?: string; severity?: string } = {}
) {
  return Alova.Get<AuditLogListData>(pathByCategory[category], {
    params: withNoCacheParams(params),
  });
}

export function getAuditLoggingSettings() {
  return Alova.Get<{ items: AuditLoggingSettings[] }>('/audit-logs/settings', {
    params: withNoCacheParams(),
  });
}

export function getEffectiveAuditLoggingSettings(tenantId: number) {
  return Alova.Get<{ item: AuditLoggingSettings }>('/audit-logs/settings/effective', {
    params: withNoCacheParams({ tenant_id: tenantId }),
  });
}

export function saveAuditLoggingSettings(tenantId: number, payload: AuditLoggingSettingsPayload) {
  return Alova.Put<{ item: AuditLoggingSettings }>(`/audit-logs/settings/${tenantId}`, payload);
}
