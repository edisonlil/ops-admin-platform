<template>
  <DetailPageRuntime :schema="detailPage">
    <n-spin :show="loading">
      <div class="studio-workbench">
        <section class="studio-builder">
          <div class="studio-section studio-section--prompt">
            <header class="studio-section__head">
              <div>
                <h3>提示词</h3>
                <span>定义单轮生成应用的系统角色和用户输入模板。</span>
              </div>
              <n-button size="small" tertiary type="primary" @click="generatePromptHint">生成</n-button>
            </header>
            <n-form label-placement="top" class="studio-form">
              <n-form-item label="模型配置">
                <n-select
                  v-model:value="selectedModelKey"
                  :options="modelConfigOptions"
                  :loading="modelConfigLoading"
                  filterable
                  placeholder="选择模型或路由配置"
                />
              </n-form-item>
              <n-form-item label="系统提示词">
                <div class="system-prompt-source">
                  <n-radio-group v-model:value="systemPromptSource" size="small">
                    <n-radio-button value="inline">手动编写</n-radio-button>
                    <n-radio-button value="asset">引用提示词库</n-radio-button>
                  </n-radio-group>
                  <n-input
                    v-if="systemPromptSource === 'inline'"
                    v-model:value="form.system_prompt"
                    type="textarea"
                    :autosize="{ minRows: 5, maxRows: 9 }"
                  />
                  <template v-else>
                    <n-select
                      v-model:value="selectedSystemPromptAssetKey"
                      :options="publishedPromptOptions"
                      :loading="publishedPromptsLoading"
                      filterable
                      clearable
                      placeholder="选择已发布的提示词"
                    />
                    <div class="prompt-asset-preview">
                      <div class="prompt-asset-preview__meta">
                        <span>{{ selectedPublishedPrompt?.name || '未选择提示词' }}</span>
                        <n-tag v-if="selectedPublishedPrompt?.resolved_version" size="small" round>
                          {{ selectedPublishedPrompt.resolved_version }}
                        </n-tag>
                      </div>
                      <pre>{{ selectedPublishedPrompt?.system_prompt || '选择后将使用提示词库当前已发布版本作为系统提示词。' }}</pre>
                    </div>
                  </template>
                </div>
              </n-form-item>
              <n-form-item label="用户提示词模板">
                <n-input
                  v-model:value="form.user_prompt_template"
                  type="textarea"
                  placeholder="例如：请总结：{{question}}"
                  :autosize="{ minRows: 8, maxRows: 16 }"
                />
              </n-form-item>
            </n-form>
          </div>

          <div class="studio-section">
            <header class="studio-section__head">
              <div>
                <h3>变量</h3>
                <span>声明运行时需要注入的变量 Schema。</span>
              </div>
              <n-button size="small" text @click="resetVariablesSchema">重置</n-button>
            </header>
            <n-input v-model:value="variablesSchemaText" type="textarea" :autosize="{ minRows: 7, maxRows: 10 }" />
          </div>

          <div class="studio-section studio-section--muted">
            <header class="studio-section__head">
              <div>
                <h3>上下文</h3>
                <span>后续可接入知识库、会话上下文或业务上下文。</span>
              </div>
              <n-button size="small" text disabled>添加</n-button>
            </header>
            <p>当前版本暂未启用上下文，应用以变量和提示词作为输入。</p>
          </div>

          <div class="studio-section studio-section--muted">
            <header class="studio-section__head">
              <div>
                <h3>工具</h3>
                <span>后续可挂载 Skill、MCP、Plugin 或内部工具。</span>
              </div>
              <n-button size="small" text disabled>添加</n-button>
            </header>
            <p>Prompt Runtime v1 保留工具抽象入口，执行阶段暂不调用工具。</p>
          </div>

          <div class="studio-section">
            <header class="studio-section__head">
              <div>
                <h3>输出</h3>
                <span>定义返回结构，便于后续 API 发布和调用方集成。</span>
              </div>
              <n-button size="small" text @click="resetOutputSchema">清空</n-button>
            </header>
            <n-input v-model:value="outputSchemaText" type="textarea" :autosize="{ minRows: 7, maxRows: 10 }" />
          </div>
        </section>

        <aside class="studio-preview">
          <div class="preview-panel">
            <header class="preview-panel__head">
              <div>
                <h3>调试与预览</h3>
                <span>{{ form.status === 'published' ? '已发布' : '草稿' }}</span>
              </div>
              <n-button type="primary" :loading="running" @click="runDraft">Run Prompt</n-button>
            </header>

            <section class="runtime-variables">
              <div class="runtime-variables__header">
                <span>运行变量</span>
                <n-button size="tiny" text @click="syncRuntimeVariableValues">同步 Schema</n-button>
              </div>
              <n-empty v-if="!runtimeVariableFields.length" size="small" description="当前 Prompt 不需要变量" />
              <n-grid v-else :cols="1" responsive="screen">
                <n-form-item-gi v-for="field in runtimeVariableFields" :key="field.key" :show-require-mark="field.required">
                  <template #label>
                    <span class="runtime-variable-label">
                      <span>{{ field.label }}</span>
                      <span v-if="field.label !== field.key" class="runtime-variable-key">{{ field.key }}</span>
                    </span>
                  </template>
                  <n-select
                    v-if="field.options?.length"
                    v-model:value="runtimeVariableValues[field.key]"
                    clearable
                    :options="field.options"
                    :placeholder="field.placeholder"
                  />
                  <n-switch v-else-if="field.type === 'boolean'" v-model:value="runtimeVariableValues[field.key]" />
                  <n-input-number
                    v-else-if="field.type === 'number'"
                    v-model:value="runtimeVariableValues[field.key]"
                    clearable
                    :placeholder="field.placeholder"
                    class="runtime-variable-number"
                  />
                  <n-input v-else v-model:value="runtimeVariableValues[field.key]" clearable :placeholder="field.placeholder" />
                  <div v-if="field.description" class="runtime-variable-description">{{ field.description }}</div>
                </n-form-item-gi>
              </n-grid>
            </section>

            <div class="chat-preview">
              <div class="chat-preview__avatar">AI</div>
              <div class="chat-preview__bubble">
                <pre>{{ runResult?.answer || '运行后将在这里预览模型输出。' }}</pre>
              </div>
            </div>

            <n-collapse class="preview-collapse" arrow-placement="right">
              <n-collapse-item title="Trace" name="trace">
                <dl v-if="runResult?.trace" class="trace-list">
                  <dt>Trace ID</dt>
                  <dd>{{ runResult.trace.trace_id }}</dd>
                  <dt>Model</dt>
                  <dd>{{ runResult.trace.model_key || runResult.trace.route_key }}</dd>
                  <dt>Latency</dt>
                  <dd>{{ runResult.trace.elapsed_ms }} ms</dd>
                  <template v-if="tracePromptAsset">
                    <dt>Prompt Source</dt>
                    <dd>{{ tracePromptAsset.prompt_asset_name }} / {{ tracePromptAsset.prompt_version }}</dd>
                  </template>
                  <dt>Prompt</dt>
                  <dd><pre>{{ runResult.trace.rendered_prompt }}</pre></dd>
                </dl>
                <n-empty v-else description="运行后显示 Trace" />
              </n-collapse-item>
              <n-collapse-item title="发布 API" name="api">
                <code>POST /runtime/apps/{{ form.app_key }}/run</code>
              </n-collapse-item>
            </n-collapse>
          </div>
        </aside>
      </div>
    </n-spin>
  </DetailPageRuntime>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { SelectOption } from 'naive-ui';
  import { getLlmModels, getLlmRoutingPolicies } from '@/api/business';
  import { getPublishedPromptAsset, getPublishedPromptAssets, type PublishedPromptAsset, type PromptAsset } from '@/api/aiAssets';
  import { defineDetailPage, DetailPageRuntime } from '@/page-runtime';
  import {
    getAiApplication,
    publishAiApplication,
    runAiApplicationDraft,
    updateAiApplication,
    type AiApplication,
    type AiRunResult,
  } from '@/api/aiStudio';

  interface RuntimeVariableField {
    key: string;
    label: string;
    placeholder: string;
    description: string;
    type: 'text' | 'number' | 'boolean';
    required: boolean;
    options?: SelectOption[];
  }

  type SchemaRecord = Record<string, unknown>;

  const TEMPLATE_VARIABLE_PATTERN = /\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g;
  const RESERVED_SCHEMA_KEYS = new Set(['type', 'title', 'label', 'description', 'properties', 'required', 'default', 'example']);
  const route = useRoute();
  const router = useRouter();
  const message = useMessage();
  const loading = ref(false);
  const saving = ref(false);
  const publishing = ref(false);
  const running = ref(false);
  const modelConfigLoading = ref(false);
  const publishedPromptsLoading = ref(false);
  const activeApp = ref<AiApplication | null>(null);
  const models = ref<Recordable[]>([]);
  const policies = ref<Recordable[]>([]);
  const publishedPrompts = ref<PromptAsset[]>([]);
  const publishedPromptDetails = reactive<Record<string, PublishedPromptAsset>>({});
  const selectedModelKey = ref('');
  const systemPromptSource = ref<'inline' | 'asset'>('inline');
  const selectedSystemPromptAssetKey = ref('');
  const variablesSchemaText = ref('{\n  "type": "object",\n  "required": ["question"]\n}');
  const outputSchemaText = ref('{}');
  const runtimeVariableValues = reactive<Record<string, string | number | boolean | null>>({});
  const runResult = ref<AiRunResult | null>(null);
  const form = reactive({
    app_key: '',
    name: '',
    icon: 'robot',
    description: '',
    app_type: 'single_turn_generation',
    status: 'draft',
    endpoint_slug: '',
    system_prompt: '',
    developer_prompt: '',
    user_prompt_template: '',
  });

  const modelConfigOptions = computed<SelectOption[]>(() => {
    const options: SelectOption[] = [];
    const seen = new Set<string>();
    const push = (value: string, label: string) => {
      if (!value || seen.has(value)) return;
      seen.add(value);
      options.push({ value, label });
    };
    policies.value
      .filter((item) => item.enabled !== false)
      .forEach((item) => {
        const routeKey = String(item.route_key || '').trim();
        push(routeKey, `路由：${item.display_name || routeKey} (${routeKey})`);
      });
    models.value
      .filter((item) => item.enabled !== false)
      .forEach((item) => {
        const modelKey = String(item.model_key || '').trim();
        push(modelKey, `模型：${item.display_name || item.model_name || modelKey} (${modelKey})`);
      });
    return options;
  });

  const parsedVariablesSchema = computed(() => parseJsonObjectSilently(variablesSchemaText.value));
  const runtimeVariableFields = computed<RuntimeVariableField[]>(() =>
    buildRuntimeVariableFields(parsedVariablesSchema.value, form.user_prompt_template)
  );
  const publishedPromptOptions = computed<SelectOption[]>(() =>
    publishedPrompts.value.map((item) => ({
      label: `${item.name} (${item.prompt_key})`,
      value: item.prompt_key,
    }))
  );
  const selectedPublishedPrompt = computed(() => {
    const key = selectedSystemPromptAssetKey.value;
    return key ? publishedPromptDetails[key] : null;
  });
  const tracePromptAsset = computed(() => {
    const messages = runResult.value?.trace?.rendered_messages || [];
    const systemMessage = messages.find((item) => item.role === 'system' && item.prompt_source === 'prompt_asset');
    return systemMessage || null;
  });

  const detailPage = computed(() =>
    defineDetailPage<AiApplication>({
      id: 'ai.studio.detail',
      title: form.name || 'AI 应用配置',
      description: form.app_key ? `${form.app_key} · ${form.status === 'published' ? '已发布' : '草稿'}` : '配置应用运行时并在 Playground 调试。',
      kind: 'workspace-detail',
      variant: 'dense-data',
      density: 'compact',
      actions: [
        {
          key: 'back',
          label: '返回',
          onClick: () => router.push({ name: 'ai-studio' }),
        },
        {
          key: 'save',
          label: '保存',
          loading: saving.value,
          onClick: saveCurrent,
        },
        {
          key: 'publish',
          label: '发布',
          type: 'primary',
          disabled: activeApp.value?.status === 'published',
          loading: publishing.value,
          onClick: publishCurrent,
        },
      ],
    })
  );

  watch(runtimeVariableFields, syncRuntimeVariableValues, { immediate: true });

  async function reload() {
    const appKey = String(route.params.appKey || '');
    if (!appKey) {
      message.error('应用 Key 缺失');
      return;
    }
    loading.value = true;
    try {
      const [app] = await Promise.all([getAiApplication(appKey), loadModelConfigs(), loadPublishedPrompts()]);
      selectApp(app);
    } finally {
      loading.value = false;
    }
  }

  async function loadModelConfigs() {
    modelConfigLoading.value = true;
    try {
      const [modelPayload, policyPayload] = await Promise.all([getLlmModels(), getLlmRoutingPolicies()]);
      models.value = modelPayload.items || [];
      policies.value = policyPayload.items || [];
    } finally {
      modelConfigLoading.value = false;
    }
  }

  async function loadPublishedPrompts() {
    publishedPromptsLoading.value = true;
    try {
      const payload = await getPublishedPromptAssets({ page: 1, page_size: 100 });
      publishedPrompts.value = payload.items || [];
    } finally {
      publishedPromptsLoading.value = false;
    }
  }

  async function loadPublishedPromptDetail(promptKey: string) {
    if (!promptKey || publishedPromptDetails[promptKey]) return;
    publishedPromptDetails[promptKey] = await getPublishedPromptAsset(promptKey);
  }

  function selectApp(app: AiApplication) {
    activeApp.value = app;
    form.app_key = app.app_key;
    form.name = app.name;
    form.icon = String(app.runtime_config?.icon || 'robot');
    form.description = app.description || '';
    form.app_type = app.app_type;
    form.status = app.status;
    form.endpoint_slug = app.endpoint_slug || app.app_key;
    form.system_prompt = app.system_prompt || '';
    form.developer_prompt = app.developer_prompt || '';
    form.user_prompt_template = app.user_prompt_template || '';
    systemPromptSource.value = app.runtime_config?.system_prompt_source === 'asset' ? 'asset' : 'inline';
    selectedSystemPromptAssetKey.value = String(app.runtime_config?.system_prompt_asset_key || '');
    if (selectedSystemPromptAssetKey.value) {
      void loadPublishedPromptDetail(selectedSystemPromptAssetKey.value);
    }
    selectedModelKey.value = String(app.model_preferences?.model || app.model_preferences?.route_key || '');
    variablesSchemaText.value = stringifyJson(app.variables_schema || {});
    outputSchemaText.value = stringifyJson(app.output_schema || {});
    runResult.value = null;
    syncRuntimeVariableValues();
  }

  async function saveCurrent() {
    if (!form.app_key || !form.name) {
      message.warning('应用 Key 和名称不能为空');
      return;
    }
    if (!selectedModelKey.value) {
      message.warning('请选择模型配置');
      return;
    }
    if (systemPromptSource.value === 'asset' && !selectedSystemPromptAssetKey.value) {
      message.warning('请选择已发布的提示词');
      return;
    }
    saving.value = true;
    try {
      const saved = await updateAiApplication(form.app_key, buildPayload());
      message.success('AI 应用已保存');
      selectApp(saved as AiApplication);
    } finally {
      saving.value = false;
    }
  }

  async function publishCurrent() {
    publishing.value = true;
    try {
      await saveCurrent();
      const published = await publishAiApplication(form.app_key);
      message.success('AI 应用已发布');
      selectApp(published as AiApplication);
    } finally {
      publishing.value = false;
    }
  }

  async function runDraft() {
    const missingRequired = findUnfilledRequiredVariables();
    if (missingRequired.length) {
      message.warning(`请填写运行变量：${missingRequired.join('、')}`);
      return;
    }
    running.value = true;
    try {
      await saveCurrent();
      runResult.value = await runAiApplicationDraft(form.app_key, {
        variables: buildRuntimeVariables(),
      });
    } finally {
      running.value = false;
    }
  }

  function buildPayload() {
    return {
      ...form,
      model_preferences: { model: selectedModelKey.value, temperature: 0.2 },
      variables_schema: parseJsonObject(variablesSchemaText.value),
      output_schema: parseJsonObject(outputSchemaText.value),
      trace_policy: { enabled: true },
      runtime_config: {
        ...(activeApp.value?.runtime_config || {}),
        icon: form.icon,
        system_prompt_source: systemPromptSource.value,
        system_prompt_asset_key: systemPromptSource.value === 'asset' ? selectedSystemPromptAssetKey.value : '',
      },
    };
  }

  function resetVariablesSchema() {
    variablesSchemaText.value = '{\n  "type": "object",\n  "required": ["question"]\n}';
  }

  function resetOutputSchema() {
    outputSchemaText.value = '{}';
  }

  function generatePromptHint() {
    message.info('后续会接入提示词生成能力');
  }

  function asSchemaRecord(value: unknown): SchemaRecord | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as SchemaRecord) : null;
  }

  function extractTemplateVariableKeys(template: string): string[] {
    const keys = new Set<string>();
    for (const match of template.matchAll(TEMPLATE_VARIABLE_PATTERN)) {
      keys.add(match[1]);
    }
    return [...keys];
  }

  function collectSchemaEntries(schema?: SchemaRecord): {
    entries: Map<string, unknown>;
    requiredKeys: Set<string>;
  } {
    const entries = new Map<string, unknown>();
    const requiredKeys = new Set<string>();
    if (!schema) return { entries, requiredKeys };

    const required = Array.isArray(schema.required) ? schema.required : [];
    required.forEach((key) => {
      if (typeof key === 'string') requiredKeys.add(key);
    });

    const properties = asSchemaRecord(schema.properties);
    if (properties) {
      Object.entries(properties).forEach(([key, value]) => entries.set(key, value));
      return { entries, requiredKeys };
    }

    const variables = Array.isArray(schema.variables) ? schema.variables : [];
    variables.forEach((item) => {
      if (typeof item === 'string') {
        entries.set(item, {});
      } else {
        const record = asSchemaRecord(item);
        const key = record && typeof record.key === 'string' ? record.key : record && typeof record.name === 'string' ? record.name : '';
        if (key) entries.set(key, record);
      }
    });

    Object.entries(schema).forEach(([key, value]) => {
      if (!RESERVED_SCHEMA_KEYS.has(key) && !entries.has(key)) {
        entries.set(key, value);
      }
    });
    return { entries, requiredKeys };
  }

  function buildRuntimeVariableFields(schema: SchemaRecord | null, template: string): RuntimeVariableField[] {
    const tokenKeys = new Set(extractTemplateVariableKeys(template || ''));
    const { entries, requiredKeys } = collectSchemaEntries(schema || undefined);
    const keys = [...new Set([...entries.keys(), ...tokenKeys])];

    return keys.map((key) => {
      const raw = entries.get(key);
      const node = asSchemaRecord(raw);
      const rawLabel = typeof raw === 'string' ? raw : undefined;
      const label = String(node?.label || node?.title || node?.name || rawLabel || key);
      const description = String(node?.description || node?.help || '');
      const typeValue = String(node?.type || '').toLowerCase();
      const options = buildVariableOptions(node);
      const fieldType: RuntimeVariableField['type'] =
        typeValue === 'boolean' ? 'boolean' : typeValue === 'number' || typeValue === 'integer' ? 'number' : 'text';

      return {
        key,
        label,
        description,
        type: fieldType,
        required: tokenKeys.has(key) || requiredKeys.has(key) || node?.required === true,
        placeholder: String(node?.placeholder || node?.example || `请输入${label}`),
        options,
      };
    });
  }

  function buildVariableOptions(node: SchemaRecord | null): SelectOption[] | undefined {
    const enumValues = Array.isArray(node?.enum) ? node?.enum : Array.isArray(node?.options) ? node?.options : [];
    const options = enumValues
      .map((item) => {
        const record = asSchemaRecord(item);
        if (record) {
          const value = record.value;
          if (typeof value !== 'string' && typeof value !== 'number') return null;
          return { label: String(record.label || value), value };
        }
        if (typeof item !== 'string' && typeof item !== 'number') return null;
        return { label: String(item), value: item };
      })
      .filter(Boolean) as SelectOption[];
    return options.length ? options : undefined;
  }

  function syncRuntimeVariableValues() {
    const activeKeys = new Set(runtimeVariableFields.value.map((field) => field.key));
    Object.keys(runtimeVariableValues).forEach((key) => {
      if (!activeKeys.has(key)) delete runtimeVariableValues[key];
    });
    runtimeVariableFields.value.forEach((field) => {
      if (typeof runtimeVariableValues[field.key] === 'undefined') {
        runtimeVariableValues[field.key] = field.type === 'boolean' ? false : null;
      }
    });
  }

  function buildRuntimeVariables() {
    const variables: Record<string, unknown> = {};
    runtimeVariableFields.value.forEach((field) => {
      const value = runtimeVariableValues[field.key];
      if (value === null || typeof value === 'undefined' || value === '') return;
      assignVariableValue(variables, field.key, value);
    });
    return variables;
  }

  function assignVariableValue(target: Record<string, unknown>, key: string, value: unknown) {
    const parts = key.split('.').filter(Boolean);
    let current = target;
    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        current[part] = value;
        return;
      }
      const next = asSchemaRecord(current[part]) || {};
      current[part] = next;
      current = next;
    });
  }

  function findUnfilledRequiredVariables() {
    return runtimeVariableFields.value
      .filter((field) => field.required)
      .filter((field) => {
        const value = runtimeVariableValues[field.key];
        return value === null || typeof value === 'undefined' || (typeof value === 'string' && !value.trim());
      })
      .map((field) => field.label);
  }

  function parseJsonObject(value: string): Record<string, unknown> {
    try {
      const payload = JSON.parse(value || '{}');
      return payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {};
    } catch {
      message.error('JSON 格式不正确');
      throw new Error('Invalid JSON');
    }
  }

  function parseJsonObjectSilently(value: string): Record<string, unknown> | null {
    try {
      const payload = JSON.parse(value || '{}');
      return payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : null;
    } catch {
      return null;
    }
  }

  function stringifyJson(value: unknown) {
    return JSON.stringify(value || {}, null, 2);
  }

  watch(selectedSystemPromptAssetKey, (key) => {
    if (key) void loadPublishedPromptDetail(key);
  });

  onMounted(reload);
</script>

<style lang="less" scoped>
  .studio-workbench {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(520px, 42%);
    gap: 16px;
    align-items: start;
    min-width: 0;
  }

  .studio-builder {
    display: grid;
    gap: 12px;
    min-width: 0;
  }

  .studio-section,
  .preview-panel {
    min-width: 0;
    padding: 14px;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius);
  }

  .studio-section--prompt {
    border-color: color-mix(in srgb, var(--app-primary-color) 70%, var(--app-border-color, #d9e1ec));
    box-shadow: 0 0 0 2px var(--app-primary-soft-bg);
  }

  .studio-section--muted {
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
  }

  .studio-section__head,
  .preview-panel__head,
  .runtime-variables__header {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .studio-section__head h3,
  .preview-panel__head h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 650;
    line-height: 1.35;
  }

  .studio-section__head span,
  .preview-panel__head span,
  .studio-section--muted p {
    color: var(--app-text-color-2);
    font-size: 12px;
    line-height: 1.5;
  }

  .studio-section--muted p {
    margin: 0;
  }

  .studio-form {
    min-width: 0;
  }

  .system-prompt-source {
    display: grid;
    width: 100%;
    gap: 10px;
    min-width: 0;
  }

  .prompt-asset-preview {
    min-width: 0;
    padding: 10px 12px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 76%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 8px;
  }

  .prompt-asset-preview__meta {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  .studio-preview {
    position: sticky;
    top: 12px;
    min-width: 0;
  }

  .preview-panel {
    display: grid;
    gap: 12px;
  }

  .runtime-variables {
    min-width: 0;
    padding: 12px 12px 0;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 78%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: var(--app-card-radius);
  }

  .runtime-variables__header {
    align-items: center;
    margin-bottom: 10px;
    color: var(--app-text-color-1);
    font-size: 13px;
    font-weight: 650;
  }

  .runtime-variable-label {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    max-width: 100%;
  }

  .runtime-variable-key,
  .runtime-variable-description {
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 400;
  }

  .runtime-variable-key {
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .runtime-variable-description {
    margin-top: 6px;
    line-height: 1.5;
  }

  .runtime-variable-number {
    width: 100%;
  }

  .chat-preview {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 10px;
    min-height: 150px;
    padding: 12px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 76%, var(--app-surface-bg));
    border-radius: var(--app-card-radius);
  }

  .chat-preview__avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    color: var(--app-primary-color);
    font-size: 12px;
    font-weight: 700;
    background: var(--app-primary-soft-bg);
    border-radius: 8px;
  }

  .chat-preview__bubble {
    min-width: 0;
    padding: 10px 12px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 60%, transparent);
    border-radius: var(--app-card-radius);
  }

  .preview-collapse {
    min-width: 0;
  }

  .trace-list {
    margin: 0;
  }

  .trace-list dt {
    margin-top: 8px;
    font-weight: 600;
  }

  .trace-list dd {
    margin: 4px 0 0;
  }

  pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }

  code {
    display: block;
    padding: 10px;
    overflow: auto;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 80%, var(--app-surface-bg));
    border-radius: 6px;
  }

  @media (max-width: 1180px) {
    .studio-workbench {
      grid-template-columns: 1fr;
    }

    .studio-preview {
      position: static;
    }
  }
</style>
