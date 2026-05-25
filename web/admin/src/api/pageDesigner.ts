import { Alova } from '@/utils/http/alova/index';

export interface PageDesignerPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface PageDesignerListData<TItem> {
  items: TItem[];
  pagination: PageDesignerPagination;
}

export interface DashboardLayoutItem {
  id: string;
  type?: string;
  x: number;
  y: number;
  w: number;
  h: number;
  props?: Record<string, unknown>;
}

export interface DashboardLayout {
  cols: number;
  rowHeight: number;
  items: DashboardLayoutItem[];
}

export interface PageComponentConfig {
  id: string;
  type: string;
  title?: string;
  props?: Record<string, unknown>;
}

export interface PageVersion {
  id: number;
  page_id: number;
  version_no: number;
  schema_version: string;
  layout: DashboardLayout;
  components: PageComponentConfig[];
  data_bindings: Record<string, unknown>;
  interactions: Record<string, unknown>;
  status: string;
  create_time?: string;
  update_time?: string;
}

export interface PageDefinition {
  id: number;
  tenant_id: number;
  page_key: string;
  name: string;
  description: string;
  page_type: string;
  status: string;
  current_version_id?: number | null;
  thumbnail_file_id?: number | null;
  settings: Record<string, unknown>;
  menu_mounted: boolean;
  menu_key: string;
  version?: PageVersion | null;
  create_time?: string;
  update_time?: string;
}

export interface PageDesignerRuntime {
  preview: boolean;
  page_key: string;
  page_type: string;
  schema_version: string;
  layout: DashboardLayout;
  components: PageComponentConfig[];
  data_bindings: Record<string, unknown>;
  interactions: Record<string, unknown>;
}

export interface PageRuntimePayload {
  item: {
    page: PageDefinition;
    version: PageVersion;
    runtime: PageDesignerRuntime;
  };
}

export interface PagePayload {
  page_key: string;
  name: string;
  description?: string;
  page_type?: string;
  thumbnail_file_id?: number | null;
  settings?: Record<string, unknown>;
}

export interface PageDraftPayload {
  schema_version?: string;
  layout: DashboardLayout;
  components: PageComponentConfig[];
  data_bindings?: Record<string, unknown>;
  interactions?: Record<string, unknown>;
}

export interface PageMenuMountPayload {
  label?: string;
  menu_key?: string;
  parent_key?: string;
  path?: string;
  route_name?: string;
  icon?: string;
  permission_code?: string;
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

export function getPageDesignerPages(
  params: { page?: number; page_size?: number; keyword?: string; type?: string | null; status?: string | null } = {}
) {
  return Alova.Get<PageDesignerListData<PageDefinition>>('/page-designer/pages', {
    params: withNoCacheParams(params),
  });
}

export function createPageDesignerPage(payload: PagePayload) {
  return Alova.Post<{ item: PageDefinition }>('/page-designer/pages', normalizePagePayload(payload));
}

export function updatePageDesignerPage(pageId: number, payload: PagePayload) {
  return Alova.Put<{ item: PageDefinition }>(`/page-designer/pages/${pageId}`, normalizePagePayload(payload));
}

export function getPageDesignerPage(pageId: number) {
  return Alova.Get<{ item: PageDefinition }>(`/page-designer/pages/${pageId}`, {
    params: withNoCacheParams(),
  });
}

export function deletePageDesignerPage(pageId: number) {
  return Alova.Delete<{ id: number; deleted: boolean }>(`/page-designer/pages/${pageId}`);
}

export function savePageDesignerDraft(pageId: number, payload: PageDraftPayload) {
  return Alova.Put<{ item: PageDefinition }>(`/page-designer/pages/${pageId}/draft`, normalizeDraftPayload(payload));
}

export function previewPageDesignerPage(pageId: number, payload: PageDraftPayload) {
  return Alova.Post<PageRuntimePayload>(`/page-designer/pages/${pageId}/preview`, normalizeDraftPayload(payload));
}

export function publishPageDesignerPage(pageId: number) {
  return Alova.Post<{ item: PageDefinition }>(`/page-designer/pages/${pageId}/publish`);
}

export function unpublishPageDesignerPage(pageId: number) {
  return Alova.Post<{ item: PageDefinition }>(`/page-designer/pages/${pageId}/unpublish`);
}

export function mountPageDesignerMenu(pageId: number, payload: PageMenuMountPayload = {}) {
  return Alova.Post<{ item: { mount: Record<string, unknown>; menu: Record<string, unknown> } }>(
    `/page-designer/pages/${pageId}/menu-mount`,
    payload
  );
}

export function unmountPageDesignerMenu(pageId: number) {
  return Alova.Delete<{ item: { unmounted: boolean } }>(`/page-designer/pages/${pageId}/menu-mount`);
}

export function getPageDesignerRuntime(pageKey: string) {
  return Alova.Get<PageRuntimePayload>(`/page-designer/runtime/${pageKey}`, {
    params: withNoCacheParams(),
  });
}

function normalizePagePayload(payload: PagePayload): PagePayload {
  return {
    page_key: String(payload.page_key || '').trim(),
    name: String(payload.name || '').trim(),
    description: payload.description || '',
    page_type: payload.page_type || 'dashboard',
    thumbnail_file_id: payload.thumbnail_file_id || null,
    settings: payload.settings || {},
  };
}

function normalizeDraftPayload(payload: PageDraftPayload): PageDraftPayload {
  return {
    schema_version: payload.schema_version || '1.0',
    layout: payload.layout || { cols: 24, rowHeight: 64, items: [] },
    components: payload.components || [],
    data_bindings: payload.data_bindings || {},
    interactions: payload.interactions || {},
  };
}
