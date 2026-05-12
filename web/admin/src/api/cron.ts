import { Alova } from '@/utils/http/alova/index';

export interface CronPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface CronSchedule {
  id: number;
  tenant_id: number;
  task_id: number;
  trigger_type: string;
  trigger_expression: string;
  timezone: string;
  start_time?: string | null;
  end_time?: string | null;
  next_fire_time?: string | null;
  create_time?: string;
  update_time?: string;
}

export interface CronTask {
  id: number;
  tenant_id: number;
  task_key: string;
  name: string;
  description: string;
  status: string;
  execution_target: string;
  payload_schema_version: number;
  default_payload: Record<string, unknown>;
  concurrency_policy: string;
  timeout_seconds: number;
  max_attempts: number;
  retry_delay_seconds: number;
  retry_backoff_multiplier: number;
  misfire_policy: string;
  schedule?: CronSchedule | null;
  create_time?: string;
  update_time?: string;
}

export interface CronRun {
  id: number;
  tenant_id: number;
  task_id: number;
  schedule_id?: number | null;
  fire_time: string;
  status: string;
  trigger_source: string;
  idempotency_key: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  started_time?: string | null;
  finished_time?: string | null;
  failure_code: string;
  failure_message: string;
  create_time?: string;
  update_time?: string;
}

export interface CronAttempt {
  id: number;
  tenant_id: number;
  run_id: number;
  attempt_number: number;
  status: string;
  worker_id: string;
  started_time: string;
  finished_time?: string | null;
  error_code: string;
  error_message: string;
  create_time?: string;
  update_time?: string;
}

export interface CronListData<TItem> {
  items: TItem[];
  pagination: CronPagination;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export function getCronTasks(params: { page?: number; page_size?: number; status?: string } = {}) {
  return Alova.Get<CronListData<CronTask>>('/cron/tasks', {
    params: withNoCacheParams(params),
  });
}

export function saveCronTask(payload: Partial<CronTask>) {
  if (payload.id) {
    return Alova.Put<{ item: CronTask }>(`/cron/tasks/${payload.id}`, payload);
  }
  return Alova.Post<{ item: CronTask }>('/cron/tasks', payload);
}

export function enableCronTask(taskId: number) {
  return Alova.Post<{ item: CronTask }>(`/cron/tasks/${taskId}/enable`);
}

export function disableCronTask(taskId: number) {
  return Alova.Post<{ item: CronTask }>(`/cron/tasks/${taskId}/disable`);
}

export function deleteCronTask(taskId: number) {
  return Alova.Delete<{ item: CronTask }>(`/cron/tasks/${taskId}`);
}

export function triggerCronTask(taskId: number, payload: Record<string, unknown> = {}) {
  return Alova.Post<{ item: CronRun }>(`/cron/tasks/${taskId}/trigger`, { payload });
}

export function getCronTaskRuns(taskId: number, params: { page?: number; page_size?: number } = {}) {
  return Alova.Get<CronListData<CronRun>>(`/cron/tasks/${taskId}/runs`, {
    params: withNoCacheParams(params),
  });
}

export function getCronRuns(params: { page?: number; page_size?: number } = {}) {
  return Alova.Get<CronListData<CronRun>>('/cron/runs', {
    params: withNoCacheParams(params),
  });
}

export function getCronRun(runId: number) {
  return Alova.Get<{ item: CronRun; attempts: CronAttempt[] }>(`/cron/runs/${runId}`, {
    params: withNoCacheParams(),
  });
}
