import { Alova } from '@/utils/http/alova/index';

export interface PromptPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface PromptListData<TItem> {
  items: TItem[];
  pagination: PromptPagination;
}

export interface PromptAsset {
  id: number;
  tenant_id: number;
  prompt_key: string;
  name: string;
  description: string;
  tags: string[];
  status: string;
  version_count: number;
  create_time?: string;
  update_time?: string;
}

export interface PromptVersion {
  id: number;
  tenant_id: number;
  prompt_id: number;
  version: string;
  system_prompt: string;
  developer_prompt: string;
  user_prompt_template: string;
  variables_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  example_inputs: Record<string, unknown>[];
  example_outputs: Record<string, unknown>[];
  model_preferences: Record<string, unknown>;
  render_engine: string;
  status: string;
  published_time?: string | null;
  create_time?: string;
  update_time?: string;
}

export interface PromptAssetPayload {
  prompt_key?: string;
  name: string;
  description?: string;
  tags?: string[];
  status?: string;
}

export interface PromptVersionPayload {
  version: string;
  system_prompt?: string;
  developer_prompt?: string;
  user_prompt_template?: string;
  variables_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  example_inputs?: Record<string, unknown>[];
  example_outputs?: Record<string, unknown>[];
  model_preferences?: Record<string, unknown>;
  render_engine?: string;
  status?: string;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export function getPromptAssets(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  status?: string;
} = {}) {
  return Alova.Get<PromptListData<PromptAsset>>('/prompts', {
    params: withNoCacheParams(params),
  });
}

export function getPromptAsset(promptId: number) {
  return Alova.Get<{ item: PromptAsset; versions: PromptVersion[] }>(`/prompts/${promptId}`, {
    params: withNoCacheParams(),
  });
}

export function copyPromptAsset(promptId: number) {
  return Alova.Post<{ item: PromptAsset }>(`/prompts/${promptId}/copy`);
}

export function savePromptAsset(payload: Partial<PromptAssetPayload> & { id?: number }) {
  const body: PromptAssetPayload = {
    name: String(payload.name || '').trim(),
    description: payload.description || '',
    tags: payload.tags || [],
    status: payload.status || 'draft',
  };
  const promptKey = String(payload.prompt_key || '').trim();
  if (promptKey) {
    body.prompt_key = promptKey;
  }
  if (payload.id) {
    return Alova.Put<{ item: PromptAsset }>(`/prompts/${payload.id}`, body);
  }
  return Alova.Post<{ item: PromptAsset }>('/prompts', body);
}

export function deletePromptAsset(promptId: number) {
  return Alova.Delete<{ id: number; archived: boolean; deleted: boolean }>(`/prompts/${promptId}`);
}

export function getPromptVersions(promptId: number) {
  return Alova.Get<{ items: PromptVersion[] }>(`/prompts/${promptId}/versions`, {
    params: withNoCacheParams(),
  });
}

export function savePromptVersion(promptId: number, payload: Partial<PromptVersionPayload> & { id?: number }) {
  const body: PromptVersionPayload = {
    version: String(payload.version || '').trim(),
    system_prompt: payload.system_prompt || '',
    developer_prompt: payload.developer_prompt || '',
    user_prompt_template: payload.user_prompt_template || '',
    variables_schema: payload.variables_schema || {},
    output_schema: payload.output_schema || {},
    example_inputs: payload.example_inputs || [],
    example_outputs: payload.example_outputs || [],
    model_preferences: payload.model_preferences || {},
    render_engine: payload.render_engine || 'simple',
    status: payload.status || 'draft',
  };
  if (payload.id) {
    return Alova.Put<{ item: PromptVersion }>(`/prompts/${promptId}/versions/${payload.id}`, body);
  }
  return Alova.Post<{ item: PromptVersion }>(`/prompts/${promptId}/versions`, body);
}

export function publishPromptVersion(promptId: number, versionId: number) {
  return Alova.Post<{ item: PromptVersion }>(`/prompts/${promptId}/versions/${versionId}/publish`);
}

export function deprecatePromptVersion(promptId: number, versionId: number) {
  return Alova.Post<{ item: PromptVersion }>(`/prompts/${promptId}/versions/${versionId}/deprecate`);
}
