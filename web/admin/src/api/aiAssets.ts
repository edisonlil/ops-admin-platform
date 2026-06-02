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

export interface PublishedPromptAsset {
  asset: PromptAsset;
  version: PromptVersion;
  prompt_key: string;
  asset_key: string;
  name: string;
  description: string;
  resolved_version: string;
  system_prompt: string;
  developer_prompt: string;
  user_prompt_template: string;
  variables_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  model_preferences: Record<string, unknown>;
  published_time?: string | null;
}

export interface PromptPolishResult {
  answer: string;
  trace_id: string;
  usage: Record<string, unknown>;
}

export interface SkillAsset {
  id: number;
  tenant_id: number;
  skill_key: string;
  name: string;
  description: string;
  tags: string[];
  status: string;
  source_type: string;
  version_count: number;
  create_time?: string;
  update_time?: string;
}

export interface SkillVersion {
  id: number;
  tenant_id: number;
  skill_id: number;
  version: string;
  manifest: Record<string, unknown>;
  content: string;
  content_sha256: string;
  entrypoint: string;
  runtime_constraints: Record<string, unknown>;
  validation_report: Record<string, unknown>;
  status: string;
  published_time?: string | null;
  create_time?: string;
  update_time?: string;
}

export interface SkillAssetPayload {
  skill_key?: string;
  name: string;
  description?: string;
  tags?: string[];
  status?: string;
  source_type?: string;
}

export interface SkillVersionPayload {
  version: string;
  file: File;
}

export interface SkillUploadPayload {
  skill_key?: string;
  version?: string;
  file: File;
}

export interface PublishedSkillAsset {
  asset: SkillAsset;
  version: SkillVersion;
  skill_key: string;
  asset_key: string;
  name: string;
  description: string;
  resolved_version: string;
  manifest: Record<string, unknown>;
  content: string;
  content_sha256: string;
  entrypoint: string;
  runtime_constraints: Record<string, unknown>;
  validation_report: Record<string, unknown>;
  published_time?: string | null;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

function normalizeAssetListParams<T extends { tags?: string[] } & Record<string, unknown>>(params: T) {
  const { tags, ...rest } = params;
  return {
    ...rest,
    tags: tags?.filter((tag) => tag.trim()).join(',') || undefined,
  };
}

export interface SortParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

export function getPromptAssets(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  status?: string;
  tags?: string[];
} & SortParams = {}) {
  return Alova.Get<PromptListData<PromptAsset>>('/prompts', {
    params: withNoCacheParams(normalizeAssetListParams(params)),
  });
}

export function getPromptAsset(promptId: number) {
  return Alova.Get<{ item: PromptAsset; versions: PromptVersion[] }>(`/prompts/${promptId}`, {
    params: withNoCacheParams(),
  });
}

export function getPublishedPromptAssets(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
} & SortParams = {}) {
  return Alova.Get<PromptListData<PromptAsset>>('/prompts/published', {
    params: withNoCacheParams(params),
  });
}

export function getPublishedPromptAsset(promptKey: string) {
  return Alova.Get<PublishedPromptAsset>(`/prompts/published/${encodeURIComponent(promptKey)}`, {
    params: withNoCacheParams(),
  });
}

export function copyPromptAsset(promptId: number) {
  return Alova.Post<{ item: PromptAsset }>(`/prompts/${promptId}/copy`);
}

export function polishPrompt(payload: { title?: string; prompt: string }) {
  return Alova.Post<PromptPolishResult>('/prompts/assist/polish', {
    title: String(payload.title || '').trim(),
    prompt: payload.prompt || '',
  });
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

export function getSkillAssets(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  status?: string;
  tags?: string[];
} & SortParams = {}) {
  return Alova.Get<PromptListData<SkillAsset>>('/skills', {
    params: withNoCacheParams(normalizeAssetListParams(params)),
  });
}

export function getSkillAsset(skillId: number) {
  return Alova.Get<{ item: SkillAsset; versions: SkillVersion[] }>(`/skills/${skillId}`, {
    params: withNoCacheParams(),
  });
}

export function getPublishedSkillAssets(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
} & SortParams = {}) {
  return Alova.Get<PromptListData<SkillAsset>>('/skills/published', {
    params: withNoCacheParams(params),
  });
}

export function getPublishedSkillAsset(skillKey: string) {
  return Alova.Get<PublishedSkillAsset>(`/skills/published/${encodeURIComponent(skillKey)}`, {
    params: withNoCacheParams(),
  });
}

export function saveSkillAsset(payload: Partial<SkillAssetPayload> & { id?: number }) {
  const body: SkillAssetPayload = {
    name: String(payload.name || '').trim(),
    description: payload.description || '',
    tags: payload.tags || [],
    status: payload.status || 'draft',
    source_type: payload.source_type || 'upload',
  };
  const skillKey = String(payload.skill_key || '').trim();
  if (skillKey) {
    body.skill_key = skillKey;
  }
  if (payload.id) {
    return Alova.Put<{ item: SkillAsset }>(`/skills/${payload.id}`, body);
  }
  return Alova.Post<{ item: SkillAsset }>('/skills', body);
}

export function uploadSkillAsset(payload: SkillUploadPayload) {
  const body = new FormData();
  body.append('package', payload.file);
  body.append('version', String(payload.version || '1.0.0').trim());
  const skillKey = String(payload.skill_key || '').trim();
  if (skillKey) {
    body.append('skill_key', skillKey);
  }
  return Alova.Post<{ item: SkillAsset; version: SkillVersion }>('/skills/upload', body);
}

export function deleteSkillAsset(skillId: number) {
  return Alova.Delete<{ id: number; archived: boolean; deleted: boolean }>(`/skills/${skillId}`);
}

export function getSkillVersions(skillId: number) {
  return Alova.Get<{ items: SkillVersion[] }>(`/skills/${skillId}/versions`, {
    params: withNoCacheParams(),
  });
}

export function saveSkillVersion(skillId: number, payload: Partial<SkillVersionPayload> & { id?: number }) {
  const body = new FormData();
  body.append('package', payload.file as File);
  body.append('version', String(payload.version || '').trim());
  if (payload.id) {
    return Alova.Put<{ item: SkillVersion }>(`/skills/${skillId}/versions/${payload.id}`, body);
  }
  return Alova.Post<{ item: SkillVersion }>(`/skills/${skillId}/versions`, body);
}

export function publishSkillVersion(skillId: number, versionId: number) {
  return Alova.Post<{ item: SkillVersion }>(`/skills/${skillId}/versions/${versionId}/publish`);
}

export function deprecateSkillVersion(skillId: number, versionId: number) {
  return Alova.Post<{ item: SkillVersion }>(`/skills/${skillId}/versions/${versionId}/deprecate`);
}
