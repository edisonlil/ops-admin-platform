import { Alova } from '@/utils/http/alova/index';

export interface TableColumnPreference {
  id?: number;
  tenant_id?: number;
  user_id?: number;
  view_key: string;
  visible_column_keys: string[];
  column_order_keys: string[];
  settings?: Record<string, unknown>;
  create_time?: string;
  update_time?: string;
}

export interface SaveTableColumnPreferencePayload {
  visible_column_keys: string[];
  column_order_keys: string[];
  settings?: Record<string, unknown>;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return { ...params, _t: Date.now() };
}

function encodeViewKey(viewKey: string) {
  return viewKey
    .split('/')
    .map((part) => encodeURIComponent(part))
    .join('/');
}

export function getTableColumnPreference(viewKey: string) {
  return Alova.Get<{ item: TableColumnPreference | null }>(`/personalization/table-columns/${encodeViewKey(viewKey)}`, {
    params: withNoCacheParams(),
  });
}

export function saveTableColumnPreference(viewKey: string, payload: SaveTableColumnPreferencePayload) {
  return Alova.Put<{ item: TableColumnPreference }>(`/personalization/table-columns/${encodeViewKey(viewKey)}`, payload);
}

export function resetTableColumnPreference(viewKey: string) {
  return Alova.Delete<{ deleted: boolean }>(`/personalization/table-columns/${encodeViewKey(viewKey)}`);
}
