import { Alova } from '@/utils/http/alova/index';

export interface BasicDataPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface BasicDataListData<TItem> {
  items: TItem[];
  pagination: BasicDataPagination;
}

export interface DictionaryType {
  id: number;
  tenant_id: number;
  parent_id?: number | null;
  code: string;
  name: string;
  category: string;
  description: string;
  status: string;
  sort_order: number;
  create_time?: string;
  update_time?: string;
}

export interface DictionaryItem {
  id: number;
  tenant_id: number;
  type_id: number;
  type_code: string;
  code: string;
  value: string;
  color: string;
  description: string;
  extra: Record<string, unknown>;
  status: string;
  sort_order: number;
  create_time?: string;
  update_time?: string;
}

export interface DictionaryTypePayload {
  id?: number;
  parent_id?: number | null;
  code: string;
  name: string;
  category?: string;
  description?: string;
  status?: string;
  sort_order?: number;
}

export interface DictionaryItemPayload {
  id?: number;
  code: string;
  value: string;
  color?: string;
  description?: string;
  extra?: Record<string, unknown>;
  status?: string;
  sort_order?: number;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  const cleaned = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== null && value !== undefined && value !== '')
  );
  return {
    ...cleaned,
    _t: Date.now(),
  };
}

export function getDictionaryTypes(
  params: { page?: number; page_size?: number; keyword?: string; status?: string | null; category?: string } = {}
) {
  return Alova.Get<BasicDataListData<DictionaryType>>('/basic-data/dictionary-types', {
    params: withNoCacheParams(params),
  });
}

export function saveDictionaryType(payload: Partial<DictionaryTypePayload> & { id?: number }) {
  const body: DictionaryTypePayload = {
    parent_id: payload.parent_id || null,
    code: String(payload.code || '').trim(),
    name: String(payload.name || '').trim(),
    category: payload.category || 'general',
    description: payload.description || '',
    status: payload.status || 'active',
    sort_order: Number(payload.sort_order || 0),
  };
  if (payload.id) {
    return Alova.Put<{ item: DictionaryType }>(`/basic-data/dictionary-types/${payload.id}`, body);
  }
  return Alova.Post<{ item: DictionaryType }>('/basic-data/dictionary-types', body);
}

export function deleteDictionaryType(typeId: number) {
  return Alova.Delete<{ id: number; deleted: boolean }>(`/basic-data/dictionary-types/${typeId}`);
}

export function getDictionaryItems(
  typeId: number,
  params: { page?: number; page_size?: number; keyword?: string; status?: string | null } = {}
) {
  return Alova.Get<BasicDataListData<DictionaryItem>>(`/basic-data/dictionary-types/${typeId}/items`, {
    params: withNoCacheParams(params),
  });
}

export function saveDictionaryItem(typeId: number, payload: Partial<DictionaryItemPayload> & { id?: number }) {
  const body: DictionaryItemPayload = {
    code: String(payload.code || '').trim(),
    value: String(payload.value || '').trim(),
    color: payload.color || '',
    description: payload.description || '',
    extra: payload.extra || {},
    status: payload.status || 'active',
    sort_order: Number(payload.sort_order || 0),
  };
  if (payload.id) {
    return Alova.Put<{ item: DictionaryItem }>(`/basic-data/dictionary-items/${payload.id}`, body);
  }
  return Alova.Post<{ item: DictionaryItem }>(`/basic-data/dictionary-types/${typeId}/items`, body);
}

export function deleteDictionaryItem(itemId: number) {
  return Alova.Delete<{ id: number; deleted: boolean }>(`/basic-data/dictionary-items/${itemId}`);
}
