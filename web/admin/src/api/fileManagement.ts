import { Alova } from '@/utils/http/alova/index';
import { useGlobSetting } from '@/hooks/setting';
import { useUser } from '@/store/modules/user';

export interface FilePagination {
  page: number;
  page_size: number;
  total: number;
}

export interface FileListData<TItem> {
  items: TItem[];
  pagination: FilePagination;
}

export interface FileLibrary {
  id: number;
  tenant_id: number;
  name: string;
  description: string;
  library_type: string;
  visibility: string;
  status: string;
  create_time?: string;
  update_time?: string;
}

export interface FileFolder {
  id: number;
  tenant_id: number;
  library_id: number;
  parent_id?: number | null;
  name: string;
  description: string;
  status: string;
  size_bytes?: number;
  file_count?: number;
  create_time?: string;
  update_time?: string;
}

export interface ManagedFile {
  id: number;
  tenant_id: number;
  library_id?: number | null;
  folder_id?: number | null;
  original_name: string;
  display_name: string;
  extension: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  storage_provider: string;
  storage_bucket: string;
  status: string;
  visibility: string;
  metadata: Record<string, unknown>;
  indexed_at?: string | null;
  create_time?: string;
  update_time?: string;
}

export type FilePreviewMode = 'image' | 'pdf' | 'text' | 'audio' | 'video' | 'external' | 'unsupported';

export interface FilePreviewMetadata {
  previewable: boolean;
  engine: string;
  mode: FilePreviewMode;
  mime_type: string;
  reason: string;
  url: string;
  max_inline_bytes?: number;
}

export interface TenantStorageQuota {
  id: number;
  tenant_id: number;
  quota_bytes: number;
  max_file_size_bytes: number;
  allowed_mime_types: string[];
  blocked_extensions: string[];
  enabled: boolean;
  create_time?: string;
  update_time?: string;
}

export interface StorageUsage {
  tenant_id: number;
  used_bytes: number;
  file_count: number;
}

export interface StorageProfile {
  id: number;
  tenant_id: number;
  provider: string;
  name: string;
  endpoint: string;
  region: string;
  bucket: string;
  access_key_id: string;
  path_style_enabled: boolean;
  tls_enabled: boolean;
  is_default: boolean;
  enabled: boolean;
  extra_config: Record<string, unknown>;
  secret_configured: boolean;
  create_time?: string;
  update_time?: string;
}

export interface StorageProviderOption {
  provider: string;
  label: string;
  supported: boolean;
  config_schema: Record<string, unknown>;
}

export interface PreviewProfile {
  id: number;
  tenant_id: number;
  provider: string;
  name: string;
  base_url: string;
  enabled: boolean;
  is_default: boolean;
  supported_extensions: string[];
  config: Record<string, unknown>;
  create_time?: string;
  update_time?: string;
}

export interface PreviewProviderOption {
  provider: string;
  label: string;
  supported: boolean;
  config_schema: Record<string, unknown>;
}

export interface FileAccessLog {
  id: number;
  tenant_id: number;
  file_id?: number | null;
  action: string;
  actor_user_id?: number | null;
  actor_name: string;
  client_ip: string;
  user_agent: string;
  result: string;
  detail: Record<string, unknown>;
  create_time?: string;
}

export interface FileSearchIndexJob {
  id: number;
  tenant_id: number;
  file_id?: number | null;
  job_type: string;
  status: string;
  attempts: number;
  last_error: string;
  scheduled_time: string;
  finished_time?: string | null;
  payload: Record<string, unknown>;
  create_time?: string;
  update_time?: string;
}

export interface FileLibraryPayload {
  name: string;
  description?: string;
  library_type?: string;
  visibility?: string;
  status?: string;
}

export interface FileFolderPayload {
  id?: number;
  library_id: number;
  parent_id?: number | null;
  name: string;
  description?: string;
  status?: string;
}

export interface FileWorkspaceData {
  libraries: FileLibrary[];
  current_library: FileLibrary | null;
  current_folder: FileFolder | null;
  breadcrumbs: FileFolder[];
  folders: FileFolder[];
  files: ManagedFile[];
  items?: Array<(FileFolder & { kind: 'folder'; name: string }) | (ManagedFile & { kind: 'file'; name: string })>;
  usage: StorageUsage;
  current_usage?: StorageUsage;
}

export interface StorageProfilePayload {
  id?: number;
  provider: string;
  name: string;
  endpoint: string;
  region?: string;
  bucket: string;
  access_key_id?: string;
  secret_access_key?: string;
  path_style_enabled?: boolean;
  tls_enabled?: boolean;
  is_default?: boolean;
  enabled?: boolean;
  extra_config?: Record<string, unknown>;
}

export interface PreviewProfilePayload {
  id?: number;
  provider: string;
  name: string;
  base_url: string;
  enabled?: boolean;
  is_default?: boolean;
  supported_extensions?: string[];
  config?: Record<string, unknown>;
}

export interface TenantQuotaPayload {
  quota_bytes: number;
  max_file_size_bytes: number;
  allowed_mime_types: string[];
  blocked_extensions: string[];
  enabled: boolean;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export interface SortParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

export function getFileLibraries(params: { page?: number; page_size?: number } & SortParams = {}) {
  return Alova.Get<FileListData<FileLibrary>>('/files/libraries', {
    params: withNoCacheParams(params),
  });
}

export function saveFileLibrary(payload: Partial<FileLibraryPayload> & { id?: number }) {
  const body: FileLibraryPayload = {
    name: String(payload.name || '').trim(),
    description: payload.description || '',
    library_type: payload.library_type || 'general',
    visibility: payload.visibility || 'tenant',
    status: payload.status || 'active',
  };
  if (payload.id) {
    return Alova.Put<{ item: FileLibrary }>(`/files/libraries/${payload.id}`, body);
  }
  return Alova.Post<{ item: FileLibrary }>('/files/libraries', body);
}

export function deleteFileLibrary(libraryId: number) {
  return Alova.Delete<{ id: number; deleted: boolean }>(`/files/libraries/${libraryId}`);
}

export function getFileWorkspace(params: { library_id?: number; folder_id?: number; keyword?: string } & SortParams = {}) {
  return Alova.Get<FileWorkspaceData>('/files/workspace', {
    params: withNoCacheParams(params),
  });
}

export function getFileLibraryTree(libraryId: number) {
  return Alova.Get<{ library: FileLibrary; items: FileFolder[] }>(`/files/libraries/${libraryId}/tree`, {
    params: withNoCacheParams(),
  });
}

export function saveFileFolder(payload: FileFolderPayload) {
  const body = {
    library_id: payload.library_id,
    parent_id: payload.parent_id ?? null,
    name: String(payload.name || '').trim(),
    description: payload.description || '',
    status: payload.status || 'active',
  };
  if (payload.id) {
    return Alova.Put<{ item: FileFolder }>(`/files/folders/${payload.id}`, body);
  }
  return Alova.Post<{ item: FileFolder }>('/files/folders', body);
}

export function deleteFileFolder(folderId: number) {
  return Alova.Delete<{ id: number; deleted: boolean }>(`/files/folders/${folderId}`);
}

export function getFiles(params: {
  page?: number;
  page_size?: number;
  library_id?: number;
  folder_id?: number;
  current_folder_only?: boolean;
  keyword?: string;
  mime_type?: string;
  status?: string;
} & SortParams = {}) {
  return Alova.Get<FileListData<ManagedFile>>('/files', {
    params: withNoCacheParams(params),
  });
}

export function searchFiles(params: { keyword?: string; page?: number; page_size?: number } = {}) {
  return Alova.Get<FileListData<ManagedFile>>('/files/search', {
    params: withNoCacheParams(params),
  });
}

export function uploadManagedFile(payload: { file: File; library_id?: number | null; folder_id?: number | null; visibility?: string }) {
  const form = new FormData();
  form.append('upload', payload.file);
  if (payload.library_id) {
    form.append('library_id', String(payload.library_id));
  }
  if (payload.folder_id) {
    form.append('folder_id', String(payload.folder_id));
  }
  form.append('visibility', payload.visibility || 'tenant');
  return Alova.Post<{ item: ManagedFile }>('/files/upload', form);
}

export function deleteManagedFile(fileId: number) {
  return Alova.Delete<{ id: number; deleted: boolean }>(`/files/${fileId}`);
}

export function reindexManagedFile(fileId: number) {
  return Alova.Post<{ item: FileSearchIndexJob }>(`/files/${fileId}/reindex`);
}

export function getFilePreviewMetadata(fileId: number) {
  return Alova.Get<{ item: ManagedFile; preview: FilePreviewMetadata }>(`/files/${fileId}/preview-metadata`, {
    params: withNoCacheParams(),
  });
}

export function getAccessLogs(params: { page?: number; page_size?: number; file_id?: number; action?: string } & SortParams = {}) {
  return Alova.Get<FileListData<FileAccessLog>>('/files/access-logs', {
    params: withNoCacheParams(params),
  });
}

export function getIndexJobs(params: { page?: number; page_size?: number; file_id?: number; status?: string } & SortParams = {}) {
  return Alova.Get<FileListData<FileSearchIndexJob>>('/files/index-jobs', {
    params: withNoCacheParams(params),
  });
}

export function getStorageProfiles(params: SortParams = {}) {
  return Alova.Get<{ items: StorageProfile[] }>('/files/admin/storage-profiles', {
    params: withNoCacheParams(params),
  });
}

export function getStorageProviderOptions() {
  return Alova.Get<{ items: StorageProviderOption[] }>('/files/admin/storage-provider-options', {
    params: withNoCacheParams(),
  });
}

export function saveStorageProfile(payload: StorageProfilePayload) {
  if (payload.id) {
    return Alova.Put<{ item: StorageProfile }>(`/files/admin/storage-profiles/${payload.id}`, payload);
  }
  return Alova.Post<{ item: StorageProfile }>('/files/admin/storage-profiles', payload);
}

export function testStorageProfile(profileId: number) {
  return Alova.Post<{ ok: boolean; provider: string; message?: string; bucket?: string }>(
    `/files/admin/storage-profiles/${profileId}/test`
  );
}

export function setDefaultStorageProfile(profileId: number) {
  return Alova.Post<{ item: StorageProfile }>(`/files/admin/storage-profiles/${profileId}/default`);
}

export function getPreviewProfiles(params: SortParams = {}) {
  return Alova.Get<{ items: PreviewProfile[] }>('/files/admin/preview-profiles', {
    params: withNoCacheParams(params),
  });
}

export function getPreviewProviderOptions() {
  return Alova.Get<{ items: PreviewProviderOption[] }>('/files/admin/preview-provider-options', {
    params: withNoCacheParams(),
  });
}

export function savePreviewProfile(payload: PreviewProfilePayload) {
  if (payload.id) {
    return Alova.Put<{ item: PreviewProfile }>(`/files/admin/preview-profiles/${payload.id}`, payload);
  }
  return Alova.Post<{ item: PreviewProfile }>('/files/admin/preview-profiles', payload);
}

export function setDefaultPreviewProfile(profileId: number) {
  return Alova.Post<{ item: PreviewProfile }>(`/files/admin/preview-profiles/${profileId}/default`);
}

export function getTenantFileQuota(tenantId: number) {
  return Alova.Get<{ quota: TenantStorageQuota | null; usage: StorageUsage }>(`/files/admin/tenants/${tenantId}/quota`, {
    params: withNoCacheParams(),
  });
}

export function saveTenantFileQuota(tenantId: number, payload: TenantQuotaPayload) {
  return Alova.Put<{ quota: TenantStorageQuota; usage: StorageUsage }>(`/files/admin/tenants/${tenantId}/quota`, payload);
}

export async function downloadManagedFile(file: ManagedFile) {
  const response = await fetch(apiUrl(`/files/${file.id}/download`), {
    method: 'GET',
    credentials: 'include',
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Download failed');
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = file.original_name || file.display_name || `file-${file.id}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function fetchFilePreviewBlob(fileId: number) {
  const response = await fetch(apiUrl(`/files/${fileId}/preview`), {
    method: 'GET',
    credentials: 'include',
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Preview failed');
  }
  return response.blob();
}

export async function fetchFilePreviewText(fileId: number) {
  const response = await fetch(apiUrl(`/files/${fileId}/preview`), {
    method: 'GET',
    credentials: 'include',
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Preview failed');
  }
  return response.text();
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

function apiUrl(path: string) {
  const { apiUrl: baseUrl, urlPrefix } = useGlobSetting();
  const prefix = `${baseUrl || ''}${urlPrefix || ''}`;
  return `${prefix}${path}`;
}
