import { Alova } from '@/utils/http/alova/index';

export interface DatasetPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface DatasetListData<TItem> {
  items: TItem[];
  pagination: DatasetPagination;
}

export interface DatasetField {
  id?: number;
  tenant_id?: number;
  dataset_id?: number;
  field_key: string;
  label: string;
  data_type: string;
  semantic_type?: string;
  unit?: string;
  precision?: number | null;
  nullable?: boolean;
  visible?: boolean;
  sort_order?: number;
  expression?: string;
  config?: Record<string, unknown>;
}

export interface Dataset {
  id: number;
  tenant_id: number;
  key: string;
  name: string;
  description: string;
  dataset_type: string;
  status: string;
  visibility: string;
  published_version_id?: number | null;
  field_count?: number;
  row_count?: number;
  create_time?: string;
  update_time?: string;
}

export interface DatasetPayload {
  id?: number;
  key: string;
  name: string;
  description?: string;
  dataset_type?: string;
  status?: string;
  visibility?: string;
}

export interface DatasetRuntimePayload {
  dataset: Dataset;
  fields: DatasetField[];
  items: Record<string, unknown>[];
  pagination: DatasetPagination;
  meta: Record<string, unknown>;
}

export interface PageParams {
  page?: number;
  page_size?: number;
}

export interface SortParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export function listDatasets(params: PageParams & SortParams & Record<string, unknown> = {}) {
  return Alova.Get<DatasetListData<Dataset>>('/datasets', {
    params: withNoCacheParams(params),
  });
}

export function getDataset(datasetId: number) {
  return Alova.Get<{ item: Dataset; fields: DatasetField[] }>(`/datasets/${datasetId}`, {
    params: withNoCacheParams(),
  });
}

export function saveDataset(payload: DatasetPayload) {
  const body = {
    key: payload.key,
    name: payload.name,
    description: payload.description || '',
    dataset_type: payload.dataset_type || 'manual',
    status: payload.status || 'draft',
    visibility: payload.visibility || 'platform',
  };
  if (payload.id) {
    return Alova.Put<{ item: Dataset }>(`/datasets/${payload.id}`, body);
  }
  return Alova.Post<{ item: Dataset }>('/datasets', body);
}

export function deleteDataset(datasetId: number) {
  return Alova.Delete<{ id: number; deleted: boolean }>(`/datasets/${datasetId}`);
}

export function saveDatasetFields(datasetId: number, fields: DatasetField[]) {
  return Alova.Put<{ items: DatasetField[] }>(`/datasets/${datasetId}/fields`, { fields });
}

export function saveDatasetRows(datasetId: number, rows: Record<string, unknown>[]) {
  return Alova.Put<{ count: number }>(`/datasets/${datasetId}/manual-rows`, { rows });
}

export function publishDataset(datasetId: number) {
  return Alova.Post<{ item: Record<string, unknown> }>(`/datasets/${datasetId}/publish`);
}

export function previewDataset(datasetId: number, params: PageParams = {}) {
  return Alova.Get<DatasetRuntimePayload>(`/datasets/${datasetId}/preview`, {
    params: withNoCacheParams(params),
  });
}

export function previewDatasetRuntime(datasetId: number, payload: { variables?: Record<string, unknown> } = {}, params: PageParams = {}) {
  return Alova.Post<DatasetRuntimePayload>(`/datasets/${datasetId}/runtime/preview`, payload, {
    params: withNoCacheParams(params),
  });
}
