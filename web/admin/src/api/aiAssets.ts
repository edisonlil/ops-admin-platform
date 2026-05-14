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
  binding_count: number;
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

export interface PromptTaskContract {
  id: number;
  tenant_id: number;
  contract_key: string;
  owner_context: string;
  task_kind: string;
  display_name: string;
  description: string;
  llm_task_key: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  required_capabilities: string[];
  allowed_prompt_scopes: Record<string, unknown>;
  enabled: boolean;
  create_time?: string;
  update_time?: string;
}

export interface PromptBinding {
  id: number;
  tenant_id: number;
  contract_id: number;
  contract_key: string;
  prompt_id: number;
  prompt_key: string;
  prompt_name: string;
  prompt_version_id: number;
  prompt_version: string;
  binding_name: string;
  priority: number;
  environment: string;
  enabled: boolean;
  effective_from?: string | null;
  effective_to?: string | null;
  create_time?: string;
  update_time?: string;
}

export interface PromptRun {
  id: number;
  tenant_id: number;
  contract_key: string;
  prompt_id?: number | null;
  prompt_version_id?: number | null;
  llm_task_key: string;
  input: Record<string, unknown>;
  rendered_messages: Array<{ role: string; content: string }>;
  output_text: string;
  output_json?: Record<string, unknown> | null;
  schema_valid: boolean;
  validation_errors: string[];
  status: string;
  elapsed_ms: number;
  request_id: string;
  correlation_id: string;
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

export interface PromptContractPayload {
  contract_key: string;
  owner_context?: string;
  task_kind?: string;
  display_name?: string;
  description?: string;
  llm_task_key?: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  required_capabilities?: string[];
  allowed_prompt_scopes?: Record<string, unknown>;
  enabled?: boolean;
}

export interface PromptBindingPayload {
  contract_id: number;
  prompt_id: number;
  prompt_version_id: number;
  binding_name?: string;
  priority?: number;
  environment?: string;
  enabled?: boolean;
  effective_from?: string | null;
  effective_to?: string | null;
}

export interface CompatiblePrompt {
  prompt: PromptAsset;
  version: PromptVersion;
  reasons: string[];
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
  return Alova.Delete<{ id: number; deleted: boolean }>(`/prompts/${promptId}`);
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

export function getPromptContracts(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  owner_context?: string;
  enabled?: boolean | null;
} = {}) {
  return Alova.Get<PromptListData<PromptTaskContract>>('/prompt-contracts', {
    params: withNoCacheParams(params),
  });
}

export function savePromptContract(payload: Partial<PromptContractPayload> & { original_contract_key?: string }) {
  const key = String(payload.contract_key || '').trim();
  const body: PromptContractPayload = {
    contract_key: key,
    owner_context: payload.owner_context || 'general',
    task_kind: payload.task_kind || 'single_call',
    display_name: payload.display_name || key,
    description: payload.description || '',
    llm_task_key: payload.llm_task_key || key,
    input_schema: payload.input_schema || {},
    output_schema: payload.output_schema || {},
    required_capabilities: payload.required_capabilities || [],
    allowed_prompt_scopes: payload.allowed_prompt_scopes || {},
    enabled: payload.enabled ?? true,
  };
  if (payload.original_contract_key) {
    return Alova.Put<{ item: PromptTaskContract }>(`/prompt-contracts/${encodeURIComponent(payload.original_contract_key)}`, body);
  }
  return Alova.Post<{ item: PromptTaskContract }>('/prompt-contracts', body);
}

export function getCompatiblePrompts(contractKey: string) {
  return Alova.Get<{ items: CompatiblePrompt[] }>(`/prompt-contracts/${encodeURIComponent(contractKey)}/compatible-prompts`, {
    params: withNoCacheParams(),
  });
}

export function getPromptBindings(params: {
  page?: number;
  page_size?: number;
  contract_key?: string;
  environment?: string;
} = {}) {
  return Alova.Get<PromptListData<PromptBinding>>('/prompt-bindings', {
    params: withNoCacheParams(params),
  });
}

export function createPromptBinding(payload: PromptBindingPayload) {
  return Alova.Post<{ item: PromptBinding }>('/prompt-bindings', {
    binding_name: payload.binding_name || '',
    priority: payload.priority || 100,
    environment: payload.environment || 'dev',
    enabled: payload.enabled ?? true,
    effective_from: payload.effective_from || null,
    effective_to: payload.effective_to || null,
    contract_id: payload.contract_id,
    prompt_id: payload.prompt_id,
    prompt_version_id: payload.prompt_version_id,
  });
}

export function enablePromptBinding(bindingId: number) {
  return Alova.Post<{ item: PromptBinding }>(`/prompt-bindings/${bindingId}/enable`);
}

export function disablePromptBinding(bindingId: number) {
  return Alova.Post<{ item: PromptBinding }>(`/prompt-bindings/${bindingId}/disable`);
}

export function testPrompt(payload: {
  contract_key: string;
  prompt_version_id?: number | null;
  environment?: string;
  variables: Record<string, unknown>;
  correlation_id?: string | null;
}) {
  return Alova.Post<{
    run: PromptRun;
    rendered_messages: Array<{ role: string; content: string }>;
    output_text: string;
    output_json?: Record<string, unknown> | null;
    schema_valid: boolean;
    validation_errors: string[];
  }>('/prompts/test', payload);
}

export function getPromptRuns(params: {
  page?: number;
  page_size?: number;
  contract_key?: string;
  status?: string;
} = {}) {
  return Alova.Get<PromptListData<PromptRun>>('/prompt-runs', {
    params: withNoCacheParams(params),
  });
}

export function getPromptRun(runId: number) {
  return Alova.Get<{ item: PromptRun }>(`/prompt-runs/${runId}`, {
    params: withNoCacheParams(),
  });
}
