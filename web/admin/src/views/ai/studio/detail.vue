<template>
  <DetailPageRuntime :schema="detailPage">
    <n-spin :show="loading">
      <div ref="workbenchRef" class="studio-workbench" :style="workbenchStyle">
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

            <section v-if="runtimeVariableFields.length" class="variable-schema">
              <div class="variable-schema__header">
                <div>
                  <h4>变量</h4>
                  <span>定义模板中需要注入的变量 Schema。</span>
                </div>
                <n-button size="tiny" text @click="syncRuntimeVariableValues">同步 Schema</n-button>
              </div>
              <div class="variable-schema__table">
                <div class="variable-schema__row variable-schema__row--head">
                  <span>变量 KEY</span>
                  <span>变量名</span>
                  <span>类型</span>
                  <span>可选</span>
                </div>
                <div v-for="field in runtimeVariableFields" :key="field.key" class="variable-schema__row">
                  <div class="variable-schema__key">
                    <span>{{ field.key }}</span>
                  </div>
                  <n-input
                    v-model:value="variableLabelOverrides[field.key]"
                    size="small"
                    clearable
                    placeholder="用于调试表单展示"
                    @update:value="(value) => updateVariableLabel(field.key, value)"
                  />
                  <n-select
                    v-model:value="variableTypeOverrides[field.key]"
                    :options="variableTypeOptions"
                    size="small"
                    :consistent-menu-width="false"
                    class="variable-schema__type"
                    @update:value="(value) => updateVariableType(field.key, value as RuntimeVariableType)"
                  />
                  <n-switch
                    v-model:value="variableOptionalOverrides[field.key]"
                    size="small"
                    @update:value="(value) => updateVariableOptional(field.key, value)"
                  />
                </div>
              </div>
            </section>
          </div>
        </section>

        <button
          class="studio-resizer"
          type="button"
          :aria-label="previewWidthPercent > 52 ? '收起预览面板' : '拉宽预览面板'"
          :title="previewWidthPercent > 52 ? '收起预览面板' : '拉宽预览面板'"
          @click="togglePreviewWidth"
          @pointerdown="startPreviewResize"
        >
          <span></span>
        </button>

        <aside class="studio-preview">
          <div class="preview-panel">
            <header class="preview-panel__head">
              <div>
                <h3>调试与预览</h3>
                <span>{{ form.status === 'published' ? '已发布' : '草稿' }}</span>
              </div>
              <div class="preview-panel__actions">
                <div v-if="runStatusText" class="preview-run-status" :class="{ 'is-running': running }">
                  <span class="preview-run-status__dot"></span>
                  <span>{{ runStatusText }}</span>
                </div>
                <n-button type="primary" :loading="running" @click="runDraft">运行</n-button>
              </div>
            </header>

            <section v-if="runtimeVariableFields.length" class="runtime-variables">
              <div class="runtime-variables__header">
                <span>运行变量</span>
              </div>
              <div class="runtime-variable-list">
                <div v-for="field in runtimeVariableFields" :key="field.key" class="runtime-variable-item">
                  <div class="runtime-variable-label-row">
                    <span
                      class="runtime-variable-label"
                      :title="field.label !== field.key ? `${field.label} (${field.key})` : field.key"
                    >
                      <span class="runtime-variable-name">{{ field.label }}</span>
                      <span v-if="!field.required" class="runtime-variable-optional">选填</span>
                    </span>
                    <span v-if="field.required" class="runtime-variable-required">*</span>
                  </div>
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
                  <n-upload
                    v-else-if="isMediaVariableField(field)"
                    :accept="mediaVariableAccept(field)"
                    :default-upload="false"
                    :max="1"
                    @change="(options) => handleMediaVariableChange(field, options)"
                  >
                    <n-upload-dragger>
                      <div class="runtime-media-upload__title">{{ mediaVariableUploadTitle(field) }}</div>
                      <div class="runtime-media-upload__hint">{{ mediaVariableUploadHint(field) }}</div>
                    </n-upload-dragger>
                  </n-upload>
                  <n-input v-else v-model:value="runtimeVariableValues[field.key]" clearable :placeholder="field.placeholder" />
                  <div v-if="isMediaVariableField(field) && mediaVariableValue(field.key)" class="runtime-media-file">
                    <span>{{ mediaVariableValue(field.key)?.name }}</span>
                    <span>{{ formatBytes(mediaVariableValue(field.key)?.size || 0) }}</span>
                  </div>
                  <div v-if="field.description" class="runtime-variable-description">{{ field.description }}</div>
                </div>
              </div>
            </section>

            <div class="chat-preview">
              <div class="chat-preview__bubble">
                <n-collapse v-if="previewThinkText" class="think-collapse" arrow-placement="right">
                  <n-collapse-item name="think">
                    <template #header>
                      <span class="think-collapse__title">已生成思考过程</span>
                    </template>
                    <pre class="think-box">{{ previewThinkText }}</pre>
                  </n-collapse-item>
                </n-collapse>
                <div
                  v-if="previewAnswerText"
                  class="markdown-answer"
                  v-html="previewAnswerHtml"
                ></div>
                <div v-else class="chat-preview__empty">运行后将在这里预览模型输出。</div>
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
                  <dd>{{ formatElapsedSeconds(runResult.trace.elapsed_ms) }} 秒</dd>
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
  import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { SelectOption, UploadFileInfo } from 'naive-ui';
  import MarkdownIt from 'markdown-it';
  import { getLlmModels, getLlmRoutingPolicies } from '@/api/business';
  import { getPublishedPromptAsset, getPublishedPromptAssets, type PublishedPromptAsset, type PromptAsset } from '@/api/aiAssets';
  import { defineDetailPage, DetailPageRuntime } from '@/page-runtime';
  import {
    fetchAiApplicationDraftStream,
    getAiApplication,
    publishAiApplication,
    updateAiApplication,
    type AiApplication,
    type AiRunResult,
  } from '@/api/aiStudio';

  interface RuntimeVariableField {
    key: string;
    label: string;
    placeholder: string;
    description: string;
    type: RuntimeVariableType;
    required: boolean;
    options?: SelectOption[];
  }

  type SchemaRecord = Record<string, unknown>;
  type RuntimeVariableType = 'text' | 'number' | 'boolean' | 'image' | 'file' | 'audio' | 'video';
  type RuntimeVariableValue = string | number | boolean | RuntimeMediaVariableValue | null;

  interface RuntimeMediaVariableValue {
    type: 'image' | 'file' | 'audio' | 'video';
    name: string;
    mime_type: string;
    size: number;
    data_url: string;
    text?: string;
  }

  const TEMPLATE_VARIABLE_PATTERN = /\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g;
  const RESERVED_SCHEMA_KEYS = new Set(['type', 'title', 'label', 'description', 'properties', 'required', 'default', 'example']);
  const markdownRenderer = new MarkdownIt({
    html: false,
    linkify: true,
    breaks: true,
  });
  const route = useRoute();
  const router = useRouter();
  const message = useMessage();
  const loading = ref(false);
  const saving = ref(false);
  const publishing = ref(false);
  const running = ref(false);
  const workbenchRef = ref<HTMLElement | null>(null);
  const previewWidthPercent = ref(42);
  const previewResizeDragged = ref(false);
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
  const runtimeVariableValues = reactive<Record<string, RuntimeVariableValue>>({});
  const variableTypeOverrides = reactive<Record<string, RuntimeVariableType>>({});
  const variableLabelOverrides = reactive<Record<string, string>>({});
  const variableOptionalOverrides = reactive<Record<string, boolean>>({});
  const runResult = ref<AiRunResult | null>(null);
  const streamThinkText = ref('');
  const runningElapsedMs = ref(0);
  const lastRunElapsedMs = ref(0);
  let runStopwatchTimer: number | null = null;
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
  const variableTypeOptions: SelectOption[] = [
    { label: '文本', value: 'text' },
    { label: '数字', value: 'number' },
    { label: '开关', value: 'boolean' },
    { label: '图片', value: 'image' },
    { label: '音频', value: 'audio' },
    { label: '视频', value: 'video' },
    { label: '文件', value: 'file' },
  ];

  const parsedVariablesSchema = computed(() => parseJsonObjectSilently(variablesSchemaText.value));
  const templateVariableKeys = computed(() => extractTemplateVariableKeys(form.user_prompt_template || ''));
  const runtimeVariableFields = computed<RuntimeVariableField[]>(() =>
    buildRuntimeVariableFields(parsedVariablesSchema.value, templateVariableKeys.value)
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
  const parsedPreviewOutput = computed(() => splitThinkContent(runResult.value?.answer || ''));
  const previewThinkText = computed(() => streamThinkText.value || parsedPreviewOutput.value.think);
  const previewAnswerText = computed(() => parsedPreviewOutput.value.answer);
  const previewAnswerHtml = computed(() => markdownRenderer.render(previewAnswerText.value || ''));
  const runElapsedSeconds = computed(() => {
    const elapsedMs = Number(runResult.value?.trace?.elapsed_ms || 0);
    return elapsedMs > 0 ? formatElapsedSeconds(elapsedMs) : '';
  });
  const fallbackRunElapsedSeconds = computed(() =>
    !runElapsedSeconds.value && lastRunElapsedMs.value > 0 ? formatElapsedSeconds(lastRunElapsedMs.value) : ''
  );
  const runStatusText = computed(() => {
    if (running.value) {
      return `运行中 · ${formatStopwatchSeconds(runningElapsedMs.value)} 秒`;
    }
    const elapsedSeconds = runElapsedSeconds.value || fallbackRunElapsedSeconds.value;
    return elapsedSeconds ? `执行耗时 ${elapsedSeconds} 秒` : '';
  });
  const workbenchStyle = computed(() => ({
    '--studio-preview-width': `${previewWidthPercent.value}%`,
  }));

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
  watch(templateVariableKeys, syncVariablesSchemaFromTemplate);
  onBeforeUnmount(stopRunStopwatch);

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
    Object.keys(variableTypeOverrides).forEach((key) => delete variableTypeOverrides[key]);
    Object.keys(variableLabelOverrides).forEach((key) => delete variableLabelOverrides[key]);
    Object.keys(variableOptionalOverrides).forEach((key) => delete variableOptionalOverrides[key]);
    Object.keys(runtimeVariableValues).forEach((key) => delete runtimeVariableValues[key]);
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
    streamThinkText.value = '';
    syncRuntimeVariableValues();
  }

  async function saveCurrent(options: { silent?: boolean; refresh?: boolean } = {}) {
    if (!form.app_key || !form.name) {
      message.warning('应用 Key 和名称不能为空');
      return null;
    }
    if (!selectedModelKey.value) {
      message.warning('请选择模型配置');
      return null;
    }
    if (systemPromptSource.value === 'asset' && !selectedSystemPromptAssetKey.value) {
      message.warning('请选择已发布的提示词');
      return null;
    }
    if (!options.silent) saving.value = true;
    try {
      const saved = await updateAiApplication(form.app_key, buildPayload());
      if (!options.silent) message.success('AI 应用已保存');
      if (options.refresh !== false) {
        selectApp(saved as AiApplication);
      } else {
        activeApp.value = saved as AiApplication;
      }
      return saved as AiApplication;
    } finally {
      if (!options.silent) saving.value = false;
    }
  }

  async function publishCurrent() {
    publishing.value = true;
    try {
      const saved = await saveCurrent({ silent: true });
      if (!saved) return;
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
    startRunStopwatch();
    try {
      const saved = await saveCurrent({ silent: true, refresh: false });
      if (!saved) return;
      runResult.value = { answer: '', trace_id: '', usage: {} };
      streamThinkText.value = '';
      await runDraftStream({
        variables: buildRuntimeVariables(),
      });
    } finally {
      finishRunStopwatch();
      running.value = false;
    }
  }

  async function handleMediaVariableChange(field: RuntimeVariableField, options: { fileList: UploadFileInfo[] }) {
    const uploadFile = options.fileList[0]?.file as File | undefined;
    if (!uploadFile) {
      runtimeVariableValues[field.key] = null;
      return;
    }
    if (uploadFile.size > maxMediaVariableBytes(field)) {
      message.warning(`${field.label} 文件过大，请选择 ${formatBytes(maxMediaVariableBytes(field))} 以内的文件`);
      runtimeVariableValues[field.key] = null;
      return;
    }
    try {
      const [dataUrl, text] = await Promise.all([readFileAsDataUrl(uploadFile), readTextPreviewIfSupported(uploadFile)]);
      runtimeVariableValues[field.key] = {
        type: field.type as RuntimeMediaVariableValue['type'],
        name: uploadFile.name,
        mime_type: uploadFile.type || fallbackMimeType(field),
        size: uploadFile.size,
        data_url: dataUrl,
        ...(text ? { text } : {}),
      };
    } catch (error) {
      runtimeVariableValues[field.key] = null;
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  async function runDraftStream(payload: { variables: Record<string, unknown> }) {
    const response = await fetchAiApplicationDraftStream(form.app_key, payload);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }
    if (!response.body) {
      throw new Error('当前浏览器不支持流式响应');
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let content = '';
    let reasoning = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';
      for (const event of events) {
        const parsed = parseStreamEvent(event);
        if (!parsed.data || parsed.data === '[DONE]') continue;
        if (parsed.type === 'error') {
          const errorPayload = JSON.parse(parsed.data);
          throw new Error(errorPayload?.message || 'AI 应用运行失败');
        }
        const payloadData = JSON.parse(parsed.data);
        if (parsed.type === 'meta') {
          runResult.value = {
            ...(runResult.value || { answer: '', usage: {} }),
            trace_id: payloadData.trace_id || '',
          };
          continue;
        }
        if (parsed.type === 'trace') {
          runResult.value = {
            ...(runResult.value || { answer: content, trace_id: payloadData.trace_id || '', usage: {} }),
            trace_id: payloadData.trace_id || runResult.value?.trace_id || '',
            trace: payloadData.trace,
          };
          continue;
        }
        const delta = payloadData?.choices?.[0]?.delta || {};
        const reasoningDelta = delta.reasoning_content || delta.reasoning || delta.think || delta.thinking || '';
        const contentDelta = delta.content || '';
        if (reasoningDelta) {
          reasoning += reasoningDelta;
          streamThinkText.value = reasoning;
        }
        if (contentDelta) {
          content += contentDelta;
          const parsedContent = splitThinkContent(content);
          streamThinkText.value = reasoning || parsedContent.think;
          runResult.value = {
            ...(runResult.value || { trace_id: '', usage: {} }),
            answer: content,
          };
        }
      }
    }
  }

  function parseStreamEvent(event: string) {
    const type =
      event
        .split('\n')
        .find((line) => line.startsWith('event: '))
        ?.slice(7)
        .trim() || 'message';
    const data =
      event
        .split('\n')
        .find((line) => line.startsWith('data: '))
        ?.slice(6)
        .trim() || '';
    return { type, data };
  }

  function splitThinkContent(content: string) {
    const match = content.match(/<think\b[^>]*>([\s\S]*?)(?:<\/think>|$)/i);
    if (!match) {
      return { think: '', answer: content.trim() };
    }
    const answer = content.replace(match[0], '').trim();
    return {
      think: match[1].trim(),
      answer,
    };
  }

  function buildPayload() {
    return {
      ...form,
      model_preferences: { model: selectedModelKey.value, temperature: 0.2 },
      variables_schema: buildVariablesSchemaFromTemplate(parsedVariablesSchema.value, form.user_prompt_template),
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

  function generatePromptHint() {
    message.info('后续会接入提示词生成能力');
  }

  function togglePreviewWidth() {
    if (previewResizeDragged.value) {
      previewResizeDragged.value = false;
      return;
    }
    previewWidthPercent.value = previewWidthPercent.value > 52 ? 42 : 62;
  }

  function startPreviewResize(event: PointerEvent) {
    const target = event.currentTarget as HTMLElement;
    const container = workbenchRef.value;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const startX = event.clientX;
    previewResizeDragged.value = false;
    target.setPointerCapture?.(event.pointerId);

    const resize = (moveEvent: PointerEvent) => {
      const delta = Math.abs(moveEvent.clientX - startX);
      if (delta > 3) previewResizeDragged.value = true;
      const width = rect.right - moveEvent.clientX;
      const percent = (width / rect.width) * 100;
      previewWidthPercent.value = clampNumber(percent, 34, 68);
    };
    const stop = () => {
      target.releasePointerCapture?.(event.pointerId);
      window.removeEventListener('pointermove', resize);
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
    };
    window.addEventListener('pointermove', resize);
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
  }

  function clampNumber(value: number, min: number, max: number) {
    return Math.min(max, Math.max(min, value));
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

  function buildRuntimeVariableFields(schema: SchemaRecord | null, keys: string[]): RuntimeVariableField[] {
    const tokenKeys = new Set(keys);
    const { entries, requiredKeys } = collectSchemaEntries(schema || undefined);
    const activeKeys = [...new Set(keys)];

    return activeKeys.map((key) => {
      const raw = entries.get(key);
      const node = asSchemaRecord(raw);
      const rawLabel = typeof raw === 'string' ? raw : undefined;
      const label = String(node?.label || node?.title || node?.name || rawLabel || key);
      const description = String(node?.description || node?.help || '');
      const typeValue = String(node?.type || '').toLowerCase();
      const options = buildVariableOptions(node);
      const fieldType = variableTypeOverrides[key] || resolveRuntimeVariableType(typeValue);
      const optional = variableOptionalOverrides[key] ?? node?.required === false;

      return {
        key,
        label: variableLabelOverrides[key] || label,
        description,
        type: fieldType,
        required: !optional && (tokenKeys.has(key) || requiredKeys.has(key) || node?.required === true),
        placeholder: String(node?.placeholder || node?.example || `请输入${variableLabelOverrides[key] || label}`),
        options,
      };
    });
  }

  function buildVariablesSchemaFromTemplate(schema: SchemaRecord | null, template: string): Record<string, unknown> {
    const keys = extractTemplateVariableKeys(template || '');
    if (!keys.length) return {};
    const existingProperties = asSchemaRecord(schema?.properties);
    const requiredKeys = keys.filter((key) => variableOptionalOverrides[key] !== true);
    const properties = keys.reduce<Record<string, unknown>>((result, key) => {
      const existing = asSchemaRecord(existingProperties?.[key]) || {};
      const label = (variableLabelOverrides[key] || String(existing.label || existing.title || '')).trim();
      result[key] = {
        ...existing,
        type: schemaTypeFromRuntimeType(variableTypeOverrides[key] || resolveRuntimeVariableType(String(existing.type || ''))),
        ...(label ? { label } : {}),
        ...(variableOptionalOverrides[key] === true ? { required: false } : {}),
      };
      return result;
    }, {});
    return {
      type: 'object',
      required: requiredKeys,
      properties,
    };
  }

  function schemaTypeFromRuntimeType(type: RuntimeVariableType) {
    if (type === 'text') return 'string';
    return type;
  }

  function updateVariableType(key: string, type: RuntimeVariableType) {
    variableTypeOverrides[key] = type;
    refreshVariablesSchemaText();
    const currentValue = runtimeVariableValues[key];
    if (type === 'boolean') {
      runtimeVariableValues[key] = typeof currentValue === 'boolean' ? currentValue : false;
    } else if (type === 'number') {
      runtimeVariableValues[key] = typeof currentValue === 'number' ? currentValue : null;
    } else if (['image', 'audio', 'video', 'file'].includes(type)) {
      runtimeVariableValues[key] = isRuntimeMediaVariableValue(currentValue) && currentValue.type === type ? currentValue : null;
    } else if (isRuntimeMediaVariableValue(currentValue) || typeof currentValue === 'boolean' || typeof currentValue === 'number') {
      runtimeVariableValues[key] = null;
    }
  }

  function updateVariableLabel(key: string, value: string | null) {
    variableLabelOverrides[key] = String(value || '').trim();
    refreshVariablesSchemaText();
  }

  function updateVariableOptional(key: string, optional: boolean) {
    variableOptionalOverrides[key] = optional;
    refreshVariablesSchemaText();
  }

  function refreshVariablesSchemaText() {
    variablesSchemaText.value = stringifyJson(buildVariablesSchemaFromTemplate(parsedVariablesSchema.value || {}, form.user_prompt_template));
  }

  function syncVariablesSchemaFromTemplate() {
    syncRuntimeVariableValues();
    refreshVariablesSchemaText();
  }

  function resolveRuntimeVariableType(typeValue: string): RuntimeVariableType {
    if (typeValue === 'boolean') return 'boolean';
    if (typeValue === 'number' || typeValue === 'integer') return 'number';
    if (['image', 'file', 'audio', 'video'].includes(typeValue)) return typeValue as RuntimeVariableType;
    return 'text';
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
    Object.keys(variableTypeOverrides).forEach((key) => {
      if (!activeKeys.has(key)) delete variableTypeOverrides[key];
    });
    Object.keys(variableLabelOverrides).forEach((key) => {
      if (!activeKeys.has(key)) delete variableLabelOverrides[key];
    });
    Object.keys(variableOptionalOverrides).forEach((key) => {
      if (!activeKeys.has(key)) delete variableOptionalOverrides[key];
    });
    runtimeVariableFields.value.forEach((field) => {
      if (!variableTypeOverrides[field.key]) {
        variableTypeOverrides[field.key] = field.type;
      }
      if (typeof variableLabelOverrides[field.key] === 'undefined') {
        variableLabelOverrides[field.key] = field.label === field.key ? '' : field.label;
      }
      if (typeof variableOptionalOverrides[field.key] === 'undefined') {
        variableOptionalOverrides[field.key] = !field.required;
      }
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

  function isMediaVariableField(field: RuntimeVariableField) {
    return ['image', 'file', 'audio', 'video'].includes(field.type);
  }

  function mediaVariableValue(key: string) {
    const value = runtimeVariableValues[key];
    return isRuntimeMediaVariableValue(value) ? value : null;
  }

  function isRuntimeMediaVariableValue(value: unknown): value is RuntimeMediaVariableValue {
    return !!value && typeof value === 'object' && ['image', 'file', 'audio', 'video'].includes(String((value as any).type || ''));
  }

  function mediaVariableAccept(field: RuntimeVariableField) {
    if (field.type === 'image') return 'image/*';
    if (field.type === 'audio') return 'audio/*';
    if (field.type === 'video') return 'video/*';
    return '';
  }

  function mediaVariableUploadTitle(field: RuntimeVariableField) {
    const labels: Record<string, string> = {
      image: '上传图片',
      audio: '上传音频',
      video: '上传视频',
      file: '上传文件',
    };
    return labels[field.type] || '上传文件';
  }

  function mediaVariableUploadHint(field: RuntimeVariableField) {
    if (field.type === 'image') return '支持图片理解模型分析图片内容';
    if (field.type === 'audio') return '支持音频理解模型分析或转写音频';
    if (field.type === 'video') return '支持视频理解模型分析视频内容';
    return '文本类文件会作为内容传入，其他文件会作为附件传入';
  }

  function maxMediaVariableBytes(field: RuntimeVariableField) {
    if (field.type === 'image') return 8 * 1024 * 1024;
    if (field.type === 'audio') return 20 * 1024 * 1024;
    if (field.type === 'video') return 32 * 1024 * 1024;
    return 10 * 1024 * 1024;
  }

  function startRunStopwatch() {
    stopRunStopwatch();
    runningElapsedMs.value = 0;
    lastRunElapsedMs.value = 0;
    const startedAt = Date.now();
    runStopwatchTimer = window.setInterval(() => {
      runningElapsedMs.value = Date.now() - startedAt;
    }, 100);
  }

  function finishRunStopwatch() {
    lastRunElapsedMs.value = runningElapsedMs.value;
    stopRunStopwatch();
  }

  function stopRunStopwatch() {
    if (runStopwatchTimer === null) return;
    window.clearInterval(runStopwatchTimer);
    runStopwatchTimer = null;
  }

  function fallbackMimeType(field: RuntimeVariableField) {
    if (field.type === 'image') return 'image/png';
    if (field.type === 'audio') return 'audio/mpeg';
    if (field.type === 'video') return 'video/mp4';
    return 'application/octet-stream';
  }

  function readFileAsDataUrl(file: File) {
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('文件读取失败'));
      reader.readAsDataURL(file);
    });
  }

  function readTextPreviewIfSupported(file: File) {
    const textLike =
      file.type.startsWith('text/') || /\.(txt|md|json|csv|xml|yaml|yml|log)$/i.test(file.name || '');
    if (!textLike || file.size > 512 * 1024) return Promise.resolve('');
    return new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || '').slice(0, 20000));
      reader.onerror = () => resolve('');
      reader.readAsText(file);
    });
  }

  function formatBytes(value: number) {
    if (!value) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    return `${(value / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`;
  }

  function formatElapsedSeconds(elapsedMs: unknown) {
    const seconds = Number(elapsedMs || 0) / 1000;
    if (!Number.isFinite(seconds) || seconds <= 0) return '0.00';
    return seconds < 10 ? seconds.toFixed(2) : seconds.toFixed(1);
  }

  function formatStopwatchSeconds(elapsedMs: unknown) {
    const seconds = Number(elapsedMs || 0) / 1000;
    if (!Number.isFinite(seconds) || seconds <= 0) return '0.0';
    return seconds < 10 ? seconds.toFixed(1) : seconds.toFixed(0);
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
    grid-template-columns: minmax(360px, 1fr) 10px minmax(420px, var(--studio-preview-width, 42%));
    gap: 10px;
    align-items: start;
    min-width: 0;
  }

  .studio-resizer {
    position: sticky;
    top: 12px;
    display: grid;
    place-items: center;
    width: 10px;
    min-height: 72px;
    padding: 0;
    color: var(--app-text-color-3);
    cursor: col-resize;
    background: transparent;
    border: 0;
    border-radius: 999px;
  }

  .studio-resizer::before {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 4px;
    width: 2px;
    content: '';
    background: color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 999px;
  }

  .studio-resizer span {
    z-index: 1;
    width: 6px;
    height: 28px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 80%, transparent);
    border-radius: 999px;
    box-shadow: 0 1px 4px color-mix(in srgb, #000 10%, transparent);
  }

  .studio-resizer:hover::before,
  .studio-resizer:focus-visible::before {
    background: color-mix(in srgb, var(--app-primary-color) 55%, var(--app-border-color, #d9e1ec));
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
  .studio-form {
    min-width: 0;
  }

  .preview-panel__head {
    align-items: center;
  }

  .preview-panel__actions {
    display: inline-flex;
    flex: 0 0 auto;
    gap: 10px;
    align-items: center;
    margin-left: auto;
  }

  .preview-run-status {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    max-width: 180px;
    padding: 4px 9px;
    overflow: hidden;
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
    white-space: nowrap;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 64%, transparent);
    border-radius: 999px;
  }

  .preview-run-status span:last-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .preview-run-status__dot {
    flex: 0 0 auto;
    width: 6px;
    height: 6px;
    background: var(--app-success-color, #18a058);
    border-radius: 999px;
  }

  .preview-run-status.is-running .preview-run-status__dot {
    background: var(--app-primary-color);
    animation: preview-run-pulse 1s ease-in-out infinite;
  }

  @keyframes preview-run-pulse {
    0%,
    100% {
      opacity: 0.45;
    }

    50% {
      opacity: 1;
    }
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

  .variable-schema {
    display: grid;
    gap: 10px;
    min-width: 0;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
  }

  .variable-schema__header {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
  }

  .variable-schema__header h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 650;
    line-height: 1.35;
  }

  .variable-schema__header span {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
  }

  .variable-schema__table {
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .variable-schema__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(160px, 0.8fr) 112px 58px;
    gap: 12px;
    align-items: center;
    min-height: 44px;
    padding: 8px 10px;
    background: var(--app-surface-bg);
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 55%, transparent);
  }

  .variable-schema__row:first-child {
    border-top: 0;
  }

  .variable-schema__row--head {
    min-height: 34px;
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 600;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 82%, var(--app-surface-bg));
  }

  .variable-schema__key {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .variable-schema__key span,
  .variable-schema__key small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .variable-schema__key span {
    color: var(--app-text-color-1);
    font-weight: 600;
  }

  .variable-schema__key small {
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .variable-schema__type {
    width: 112px;
  }

  .variable-schema__row :deep(.n-switch) {
    justify-self: start;
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
    padding: 14px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 78%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: var(--app-card-radius);
  }

  .runtime-variables__header {
    align-items: center;
    margin-bottom: 12px;
    color: var(--app-text-color-1);
    font-size: 14px;
    font-weight: 650;
  }

  .runtime-variable-list {
    display: grid;
    gap: 12px;
  }

  .runtime-variable-item {
    display: grid;
    gap: 6px;
  }

  .runtime-variable-label {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
    max-width: 100%;
  }

  .runtime-variable-label-row {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    max-width: 100%;
    min-width: 0;
  }

  .runtime-variable-name {
    max-width: 260px;
    overflow: hidden;
    color: var(--app-text-color-1);
    font-size: 13px;
    font-weight: 520;
    line-height: 1.5;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .runtime-variable-optional,
  .runtime-variable-description {
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 400;
  }

  .runtime-variable-optional {
    padding: 0 6px;
    color: var(--app-text-color-3);
    line-height: 18px;
    background: color-mix(in srgb, var(--app-surface-bg) 70%, transparent);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 65%, transparent);
    border-radius: 999px;
  }

  .runtime-variable-required {
    color: var(--app-error-color, #d03050);
    font-weight: 650;
    line-height: 1;
  }

  .runtime-variable-description {
    margin-top: 6px;
    line-height: 1.5;
  }

  .runtime-variable-number {
    width: 100%;
  }

  .runtime-media-upload__title {
    color: var(--app-text-color-1);
    font-size: 13px;
    font-weight: 600;
    line-height: 1.5;
  }

  .runtime-media-upload__hint,
  .runtime-media-file {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
  }

  .runtime-media-file {
    display: flex;
    gap: 8px;
    justify-content: space-between;
    margin-top: 6px;
    min-width: 0;
  }

  .runtime-media-file span:first-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chat-preview {
    display: grid;
    gap: 8px;
    min-height: 150px;
    background: transparent;
  }

  .chat-preview__bubble {
    min-width: 0;
    max-height: min(560px, calc(100vh - 340px));
    padding: 10px 12px;
    overflow: auto;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 60%, transparent);
    border-radius: var(--app-card-radius);
  }

  .chat-preview__empty {
    color: var(--app-text-color-3);
    line-height: 1.7;
  }

  .think-collapse {
    margin: 0 0 12px;
    color: var(--app-text-color-3);
    font-size: 13px;
  }

  .think-collapse__title {
    color: var(--app-text-color-3);
    font-size: 13px;
    font-weight: 500;
  }

  .think-box {
    max-height: 160px;
    margin: 4px 0 2px;
    padding: 2px 0 2px 12px;
    overflow: auto;
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.7;
    background: transparent;
    border-left: 2px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 80%, transparent);
  }

  :deep(.think-collapse .n-collapse-item) {
    margin: 0;
  }

  :deep(.think-collapse .n-collapse-item__header) {
    min-height: 24px;
    padding: 0;
  }

  :deep(.think-collapse .n-collapse-item__header-main) {
    gap: 4px;
  }

  :deep(.think-collapse .n-collapse-item__content-inner) {
    padding: 0;
  }

  .markdown-answer {
    min-width: 0;
    color: var(--app-text-color-1);
    font-size: 14px;
    line-height: 1.75;
    overflow-wrap: anywhere;
  }

  :deep(.markdown-answer h1),
  :deep(.markdown-answer h2),
  :deep(.markdown-answer h3),
  :deep(.markdown-answer h4) {
    margin: 18px 0 8px;
    font-weight: 650;
    line-height: 1.35;
  }

  :deep(.markdown-answer h1:first-child),
  :deep(.markdown-answer h2:first-child),
  :deep(.markdown-answer h3:first-child),
  :deep(.markdown-answer h4:first-child),
  :deep(.markdown-answer p:first-child) {
    margin-top: 0;
  }

  :deep(.markdown-answer h1) {
    font-size: 20px;
  }

  :deep(.markdown-answer h2) {
    font-size: 18px;
  }

  :deep(.markdown-answer h3) {
    font-size: 16px;
  }

  :deep(.markdown-answer p),
  :deep(.markdown-answer ul),
  :deep(.markdown-answer ol),
  :deep(.markdown-answer blockquote),
  :deep(.markdown-answer pre) {
    margin: 0 0 10px;
  }

  :deep(.markdown-answer ul),
  :deep(.markdown-answer ol) {
    padding-left: 22px;
  }

  :deep(.markdown-answer li + li) {
    margin-top: 4px;
  }

  :deep(.markdown-answer code) {
    padding: 2px 5px;
    font-size: 12px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 86%, var(--app-surface-bg));
    border-radius: 4px;
  }

  :deep(.markdown-answer pre) {
    padding: 10px 12px;
    overflow: auto;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 86%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 58%, transparent);
    border-radius: 8px;
  }

  :deep(.markdown-answer pre code) {
    padding: 0;
    background: transparent;
  }

  :deep(.markdown-answer blockquote) {
    padding: 8px 12px;
    color: var(--app-text-color-2);
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
    border-left: 3px solid var(--app-primary-color);
    border-radius: 6px;
  }

  :deep(.markdown-answer table) {
    width: 100%;
    margin-bottom: 10px;
    border-collapse: collapse;
  }

  :deep(.markdown-answer th),
  :deep(.markdown-answer td) {
    padding: 8px;
    border: 1px solid var(--app-border-color, #d9e1ec);
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

    .studio-resizer {
      display: none;
    }

    .studio-preview {
      position: static;
    }
  }
</style>
