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

export interface SortParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
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

export interface Region {
  id: number;
  tenant_id: number;
  parent_id?: number | null;
  parent_code: string;
  code: string;
  name: string;
  short_name: string;
  level: 'province' | 'city' | 'district' | string;
  level_label?: string;
  path: string;
  status: string;
  sort_order: number;
  extra: Record<string, unknown>;
  children?: Region[];
  create_time?: string;
  update_time?: string;
}

export interface RegionPayload {
  id?: number;
  parent_id?: number | null;
  code: string;
  name: string;
  short_name?: string;
  level: string;
  status?: string;
  sort_order?: number;
  extra?: Record<string, unknown>;
}

export interface RegionImportSummary {
  created_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
  errors: Array<{ row?: number | null; message: string }>;
  warnings: Array<{ row?: number | null; message: string }>;
  dry_run: boolean;
  mode: string;
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
  params: { page?: number; page_size?: number; keyword?: string; status?: string | null; category?: string } & SortParams = {}
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
  params: { page?: number; page_size?: number; keyword?: string; status?: string | null } & SortParams = {}
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

export function getRegions(
  params: {
    page?: number;
    page_size?: number;
    keyword?: string;
    status?: string | null;
    level?: string | null;
    parent_id?: number | null;
  } & SortParams = {}
) {
  return Alova.Get<BasicDataListData<Region>>('/basic-data/regions', {
    params: withNoCacheParams(params),
  });
}

export function getRegionTree(params: { include_disabled?: boolean } & SortParams = {}) {
  return Alova.Get<{ items: Region[] }>('/basic-data/regions/tree', {
    params: withNoCacheParams(params),
  });
}

export function getRegionChildren(parentId?: number | null, params: { active_only?: boolean } = {}) {
  const path = parentId ? `/basic-data/regions/${parentId}/children` : '/basic-data/regions/children';
  return Alova.Get<{ items: Region[] }>(path, {
    params: withNoCacheParams(params),
  });
}

export function getRegionOptions(parentId?: number | null) {
  return Alova.Get<{ items: Array<{ label: string; value: number; code: string; level: string; is_leaf: boolean }> }>(
    '/basic-data/region-options',
    { params: withNoCacheParams({ parent_id: parentId }) }
  );
}

export function saveRegion(payload: Partial<RegionPayload> & { id?: number }) {
  const body: RegionPayload = {
    parent_id: payload.parent_id || null,
    code: String(payload.code || '').trim(),
    name: String(payload.name || '').trim(),
    short_name: payload.short_name || '',
    level: payload.level || 'province',
    status: payload.status || 'active',
    sort_order: Number(payload.sort_order || 0),
    extra: payload.extra || {},
  };
  if (payload.id) {
    return Alova.Put<{ item: Region }>(`/basic-data/regions/${payload.id}`, body);
  }
  return Alova.Post<{ item: Region }>('/basic-data/regions', body);
}

export function deleteRegion(regionId: number) {
  return Alova.Delete<{ id: number; deleted: boolean }>(`/basic-data/regions/${regionId}`);
}

export function importRegions(file: File, options: { dry_run?: boolean; mode?: string } = {}) {
  const form = new FormData();
  form.append('upload', file);
  return Alova.Post<RegionImportSummary>('/basic-data/regions/import', form, {
    params: withNoCacheParams({
      dry_run: options.dry_run !== false,
      mode: options.mode || 'upsert',
    }),
  });
}
