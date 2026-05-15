<template>
  <DetailPageRuntime :schema="detailPage">
    <n-spin :show="loading">
      <nav class="studio-workspace-nav" aria-label="AI 应用工作区">
        <button
          v-for="item in workspaceTabs"
          :key="item.key"
          class="studio-workspace-nav__item"
          :class="{ 'is-active': activeWorkspace === item.key }"
          type="button"
          @click="switchWorkspace(item.key)"
        >
          <span>{{ item.label }}</span>
          <small>{{ item.description }}</small>
        </button>
      </nav>

      <div
        v-if="activeWorkspace === 'orchestration'"
        ref="workbenchRef"
        class="studio-workbench"
        :style="workbenchStyle"
      >
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

      <section v-else-if="activeWorkspace === 'api'" class="studio-workspace-panel">
        <header class="workspace-panel__head">
          <div>
            <h3>访问 API</h3>
            <span>外部系统可通过租户 API Key 调用已发布的 AI 应用能力。</span>
          </div>
        </header>
        <div class="api-doc-layout">
          <main class="api-doc-main">
            <section class="api-doc-hero">
              <div class="api-endpoint-line">
                <span class="api-method">POST</span>
                <code>{{ apiEndpoint }}</code>
                <n-button size="tiny" quaternary @click="copyText(apiEndpoint, '调用地址')">复制</n-button>
              </div>
              <p>同步执行当前应用，返回模型输出、Trace ID 和用量信息。应用必须处于已发布状态。</p>
            </section>

            <section class="api-doc-section">
              <h4>请求体</h4>
              <div class="api-field-table">
                <div class="api-field-row api-field-row--head">
                  <span>字段</span>
                  <span>类型</span>
                  <span>必填</span>
                  <span>说明</span>
                </div>
                <div class="api-field-row">
                  <code>variables</code>
                  <span>object</span>
                  <span>是</span>
                  <span>应用运行变量，字段由下方变量表定义。</span>
                </div>
                <div class="api-field-row">
                  <code>temperature</code>
                  <span>number</span>
                  <span>否</span>
                  <span>本次调用覆盖温度参数，不传则使用应用配置。</span>
                </div>
                <div class="api-field-row">
                  <code>enable_think_output</code>
                  <span>boolean</span>
                  <span>否</span>
                  <span>是否返回模型思考过程，取决于模型能力。</span>
                </div>
              </div>
            </section>

            <section class="api-doc-section">
              <h4>运行变量</h4>
              <div v-if="apiVariableRows.length" class="api-field-table">
                <div class="api-field-row api-field-row--head">
                  <span>变量</span>
                  <span>类型</span>
                  <span>状态</span>
                  <span>说明</span>
                </div>
                <div v-for="field in apiVariableRows" :key="field.key" class="api-field-row">
                  <code>{{ field.key }}</code>
                  <span>{{ field.typeLabel }}</span>
                  <span>{{ field.required ? '必填' : '可选' }}</span>
                  <span>{{ field.description || field.label || '-' }}</span>
                </div>
              </div>
              <n-empty v-else description="当前应用未定义运行变量" />
            </section>

            <section class="api-doc-section">
              <div class="api-doc-section__head">
                <h4>请求示例</h4>
                <n-button size="tiny" quaternary @click="copyText(apiRequestExample, '请求示例')">复制</n-button>
              </div>
              <pre class="api-code-block">{{ apiRequestExample }}</pre>
            </section>

            <section class="api-doc-section">
              <div class="api-doc-section__head">
                <h4>响应示例</h4>
                <n-button size="tiny" quaternary @click="copyText(apiResponseExample, '响应示例')">复制</n-button>
              </div>
              <pre class="api-code-block">{{ apiResponseExample }}</pre>
            </section>

            <section class="api-doc-section">
              <h4>错误说明</h4>
              <div class="api-field-table api-field-table--compact">
                <div class="api-field-row api-field-row--head">
                  <span>HTTP</span>
                  <span>场景</span>
                  <span>处理建议</span>
                </div>
                <div class="api-field-row">
                  <code>401</code>
                  <span>API Key 无效或缺失</span>
                  <span>检查租户 API Key 是否正确、是否已撤销。</span>
                </div>
                <div class="api-field-row">
                  <code>409</code>
                  <span>应用未发布</span>
                  <span>先在 AI Studio 发布应用后再调用。</span>
                </div>
                <div class="api-field-row">
                  <code>422</code>
                  <span>变量或模型配置不合法</span>
                  <span>检查请求体变量、模型路由和运行配置。</span>
                </div>
                <div class="api-field-row">
                  <code>502</code>
                  <span>模型执行失败</span>
                  <span>根据返回的 Trace ID 在运行日志中排查。</span>
                </div>
              </div>
            </section>
          </main>

          <aside class="api-doc-aside">
            <section class="api-info-panel">
              <h4>接口信息</h4>
              <dl>
                <dt>状态</dt>
                <dd>{{ form.status === 'published' ? '已发布' : '未发布' }}</dd>
                <dt>认证方式</dt>
                <dd><code>X-API-Key</code></dd>
                <dt>Content-Type</dt>
                <dd><code>application/json</code></dd>
                <dt>调用模式</dt>
                <dd>同步执行</dd>
              </dl>
            </section>

            <section class="api-info-panel">
              <div class="api-doc-section__head">
                <h4>cURL</h4>
                <n-button size="tiny" quaternary @click="copyText(apiCurlExample, 'cURL 示例')">复制</n-button>
              </div>
              <pre class="api-code-block api-code-block--curl">{{ apiCurlExample }}</pre>
            </section>

            <section class="api-info-panel">
              <h4>接入提示</h4>
              <ul class="api-note-list">
                <li>API Key 需在当前租户下创建，调用时会自动使用该租户的数据范围。</li>
                <li>每次调用都会生成 Trace，可在运行日志中查看输入、输出和耗时。</li>
                <li>生产环境建议在外部系统侧设置超时与重试策略。</li>
              </ul>
            </section>
          </aside>
        </div>
      </section>

      <section v-else-if="activeWorkspace === 'logs'" class="studio-workspace-panel">
        <header class="workspace-panel__head">
          <div>
            <h3>运行日志</h3>
            <span>查看当前 AI 应用的调试运行和 API 调用记录。</span>
          </div>
          <n-button size="small" :loading="runLogsLoading" @click="loadRunLogs">刷新</n-button>
        </header>
        <div class="run-log-layout">
          <div class="run-log-list">
            <button
              v-for="item in runLogs"
              :key="item.run_id"
              class="run-log-item"
              :class="{ 'is-active': selectedRunLog?.run_id === item.run_id }"
              type="button"
              @click="selectedRunLogId = item.run_id"
            >
              <span class="run-log-item__top">
                <n-tag size="small" :type="item.status === 'success' ? 'success' : 'error'">
                  {{ item.status === 'success' ? '成功' : '失败' }}
                </n-tag>
                <span>{{ formatDateTime(item.create_time) }}</span>
              </span>
              <strong>{{ runModeLabel(item.run_mode) }}</strong>
              <span class="run-log-item__meta">
                {{ item.model || '未记录模型' }} · {{ formatElapsedSeconds(item.elapsed_ms) }} 秒
              </span>
            </button>
            <n-empty v-if="!runLogsLoading && !runLogs.length" description="暂无运行日志" />
          </div>
          <div class="run-log-detail">
            <template v-if="selectedRunLog">
              <div class="run-log-detail__summary">
                <div>
                  <span>状态</span>
                  <strong>{{ selectedRunLog.status === 'success' ? '成功' : '失败' }}</strong>
                </div>
                <div>
                  <span>耗时</span>
                  <strong>{{ formatElapsedSeconds(selectedRunLog.elapsed_ms) }} 秒</strong>
                </div>
                <div>
                  <span>模型</span>
                  <strong>{{ selectedRunLog.model || '-' }}</strong>
                </div>
              </div>
              <div v-if="selectedRunLog.error_message" class="run-log-error">
                {{ selectedRunLog.error_message }}
              </div>
              <section>
                <h4>输入变量</h4>
                <pre>{{ stringifyJson(selectedRunLog.input_variables) }}</pre>
              </section>
              <section>
                <h4>输出结果</h4>
                <div
                  v-if="selectedRunLog.answer"
                  class="markdown-answer run-log-answer"
                  v-html="renderMarkdown(selectedRunLog.answer)"
                ></div>
                <n-empty v-else description="本次运行没有输出内容" />
              </section>
              <section>
                <h4>运行信息</h4>
                <dl class="trace-list">
                  <dt>Run ID</dt>
                  <dd>{{ selectedRunLog.run_id }}</dd>
                  <dt>Trace ID</dt>
                  <dd>{{ selectedRunLog.trace_id }}</dd>
                  <dt>Request ID</dt>
                  <dd>{{ selectedRunLog.request_id || '-' }}</dd>
                  <dt>Token</dt>
                  <dd>{{ tokenUsageText(selectedRunLog.usage) }}</dd>
                </dl>
              </section>
            </template>
            <n-empty v-else description="选择一条运行日志查看详情" />
          </div>
        </div>
      </section>

      <section v-else-if="activeWorkspace === 'monitoring'" class="studio-workspace-panel">
        <header class="workspace-panel__head">
          <div>
            <h3>监测</h3>
            <span>后续这里展示调用量、成功率、耗时和 Token 用量趋势。</span>
          </div>
        </header>
        <n-empty description="监测能力将在运行日志稳定后接入" />
      </section>

      <section v-else class="studio-workspace-panel">
        <header class="workspace-panel__head">
          <div>
            <h3>设置</h3>
            <span>应用基础信息、发布策略和危险操作会放在这里。</span>
          </div>
        </header>
        <n-empty description="设置工作区将在后续里程碑完善" />
      </section>
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
    getAiApplicationRunLogs,
    publishAiApplication,
    updateAiApplication,
    type AiApplication,
    type AiApplicationRunLog,
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
  type WorkspaceKey = 'orchestration' | 'api' | 'logs' | 'monitoring' | 'settings';

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
  const activeWorkspace = ref<WorkspaceKey>('orchestration');
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
  const runLogs = ref<AiApplicationRunLog[]>([]);
  const runLogsLoading = ref(false);
  const selectedRunLogId = ref('');
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
  const workspaceTabs: Array<{ key: WorkspaceKey; label: string; description: string }> = [
    { key: 'orchestration', label: '编排', description: 'Prompt 与调试' },
    { key: 'api', label: '访问 API', description: '调用方式' },
    { key: 'logs', label: '运行日志', description: '执行记录' },
    { key: 'monitoring', label: '监测', description: '指标趋势' },
    { key: 'settings', label: '设置', description: '应用信息' },
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
  const selectedRunLog = computed(() => runLogs.value.find((item) => item.run_id === selectedRunLogId.value) || runLogs.value[0] || null);
  const apiEndpoint = computed(() => `/runtime/apps/${form.app_key || '{app_key}'}/run`);
  const apiVariableRows = computed(() =>
    runtimeVariableFields.value.map((field) => ({
      ...field,
      typeLabel: variableTypeOptions.find((option) => option.value === field.type)?.label || field.type,
    }))
  );
  const apiRequestExample = computed(() => stringifyJson({ variables: sampleRuntimeVariables() }));
  const apiResponseExample = computed(() =>
    stringifyJson({
      answer: '模型输出内容',
      trace_id: 'trace_xxx',
      usage: {
        prompt_tokens: 128,
        completion_tokens: 256,
        total_tokens: 384,
      },
    })
  );
  const apiCurlExample = computed(
    () =>
      `curl -X POST "${apiEndpoint.value}" \\\n  -H "Content-Type: application/json" \\\n  -H "X-API-Key: $AI_STUDIO_API_KEY" \\\n  -d '${apiRequestExample.value.replace(/'/g, "'\\''")}'`
  );
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
  watch(activeWorkspace, (value) => {
    if (value === 'logs') void loadRunLogs();
  });
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

  async function loadRunLogs() {
    if (!form.app_key) return;
    runLogsLoading.value = true;
    try {
      const payload = await getAiApplicationRunLogs(form.app_key, 50);
      runLogs.value = payload.items || [];
      if (!runLogs.value.some((item) => item.run_id === selectedRunLogId.value)) {
        selectedRunLogId.value = runLogs.value[0]?.run_id || '';
      }
    } finally {
      runLogsLoading.value = false;
    }
  }

  function switchWorkspace(key: WorkspaceKey) {
    activeWorkspace.value = key;
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
    runLogs.value = [];
    selectedRunLogId.value = '';
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
      if (activeWorkspace.value === 'logs') {
        await loadRunLogs();
      }
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

  async function copyText(value: string, label = '内容') {
    const text = String(value || '');
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      message.success(`${label}已复制`);
    } catch {
      message.error('复制失败，请手动复制');
    }
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

  function sampleRuntimeVariables() {
    const variables: Record<string, unknown> = {};
    runtimeVariableFields.value.forEach((field) => {
      const value = field.type === 'number' ? 123 : field.type === 'boolean' ? true : isMediaVariableField(field) ? `<${field.type}>` : field.label;
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

  function formatDateTime(value: unknown) {
    const text = String(value || '').trim();
    if (!text) return '-';
    const date = new Date(text.includes('T') ? text : text.replace(' ', 'T'));
    if (Number.isNaN(date.getTime())) return text;
    const pad = (item: number) => String(item).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  }

  function formatStopwatchSeconds(elapsedMs: unknown) {
    const seconds = Number(elapsedMs || 0) / 1000;
    if (!Number.isFinite(seconds) || seconds <= 0) return '0.0';
    return seconds < 10 ? seconds.toFixed(1) : seconds.toFixed(0);
  }

  function runModeLabel(value: string) {
    if (value === 'studio_draft') return '调试运行';
    if (value === 'application_api') return 'API 调用';
    return value || '未知来源';
  }

  function tokenUsageText(usage: Record<string, unknown>) {
    const total = usage?.total_tokens ?? usage?.total ?? '';
    const prompt = usage?.prompt_tokens ?? '';
    const completion = usage?.completion_tokens ?? '';
    if (total || prompt || completion) {
      return `total ${total || '-'} / prompt ${prompt || '-'} / completion ${completion || '-'}`;
    }
    return '-';
  }

  function renderMarkdown(value: string) {
    return markdownRenderer.render(value || '');
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

  .studio-workspace-nav {
    display: flex;
    gap: 4px;
    align-items: center;
    min-width: 0;
    margin-bottom: 12px;
    padding: 4px;
    overflow-x: auto;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 74%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: var(--app-card-radius);
  }

  .studio-workspace-nav__item {
    display: grid;
    gap: 1px;
    min-width: 92px;
    padding: 7px 12px;
    color: var(--app-text-color-2);
    text-align: left;
    white-space: nowrap;
    cursor: pointer;
    background: transparent;
    border: 0;
    border-radius: 7px;
  }

  .studio-workspace-nav__item span {
    font-size: 13px;
    font-weight: 650;
    line-height: 1.35;
  }

  .studio-workspace-nav__item small {
    color: var(--app-text-color-3);
    font-size: 11px;
    line-height: 1.35;
  }

  .studio-workspace-nav__item:hover,
  .studio-workspace-nav__item.is-active {
    color: var(--app-primary-color);
    background: var(--app-surface-bg);
    box-shadow: 0 1px 3px color-mix(in srgb, #000 8%, transparent);
  }

  .studio-workspace-panel {
    min-width: 0;
    padding: 16px;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius);
  }

  .workspace-panel__head {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  .workspace-panel__head h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 650;
    line-height: 1.35;
  }

  .workspace-panel__head span {
    color: var(--app-text-color-3);
    font-size: 13px;
    line-height: 1.5;
  }

  .api-doc-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
    gap: 18px;
    align-items: start;
    min-width: 0;
  }

  .api-doc-main,
  .api-doc-aside {
    display: grid;
    gap: 14px;
    min-width: 0;
  }

  .api-doc-hero,
  .api-doc-section,
  .api-info-panel {
    min-width: 0;
    padding: 14px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .api-doc-hero {
    display: grid;
    gap: 10px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 52%, var(--app-surface-bg));
  }

  .api-doc-hero p {
    margin: 0;
    color: var(--app-text-color-3);
    font-size: 13px;
    line-height: 1.6;
  }

  .api-endpoint-line {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
  }

  .api-endpoint-line code {
    flex: 1;
    min-width: 0;
    padding: 8px 10px;
    overflow: hidden;
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 6px;
  }

  .api-method {
    padding: 5px 9px;
    color: var(--app-success-color, #18a058);
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
    background: color-mix(in srgb, var(--app-success-color, #18a058) 10%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-success-color, #18a058) 28%, transparent);
    border-radius: 5px;
  }

  .api-doc-section h4,
  .api-info-panel h4 {
    margin: 0 0 10px;
    color: var(--app-text-color-1);
    font-size: 14px;
    font-weight: 650;
    line-height: 1.4;
  }

  .api-doc-section__head {
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .api-doc-section__head h4 {
    margin: 0;
  }

  .api-field-table {
    display: grid;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 7px;
  }

  .api-field-row {
    display: grid;
    grid-template-columns: minmax(128px, 0.9fr) minmax(92px, 0.55fr) minmax(62px, 0.36fr) minmax(220px, 1.6fr);
    gap: 12px;
    align-items: center;
    min-width: 0;
    padding: 10px 12px;
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 62%, transparent);
  }

  .api-field-table--compact .api-field-row {
    grid-template-columns: 72px minmax(150px, 0.8fr) minmax(260px, 1.3fr);
  }

  .api-field-row:first-child {
    border-top: 0;
  }

  .api-field-row--head {
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 650;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
  }

  .api-field-row span,
  .api-field-row code {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 13px;
    line-height: 1.45;
  }

  .api-field-row code {
    color: var(--app-text-color-1);
    font-weight: 650;
  }

  .api-code-block {
    max-height: 360px;
    margin: 0;
    padding: 12px;
    overflow: auto;
    color: var(--app-text-color-1);
    font-size: 13px;
    line-height: 1.65;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 64%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 64%, transparent);
    border-radius: 7px;
  }

  .api-code-block--curl {
    max-height: 260px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .api-info-panel dl {
    display: grid;
    grid-template-columns: 86px minmax(0, 1fr);
    gap: 8px 10px;
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
  }

  .api-info-panel dt {
    color: var(--app-text-color-3);
  }

  .api-info-panel dd {
    min-width: 0;
    margin: 0;
    overflow-wrap: anywhere;
  }

  .api-note-list {
    display: grid;
    gap: 8px;
    margin: 0;
    padding-left: 18px;
    color: var(--app-text-color-2);
    font-size: 13px;
    line-height: 1.6;
  }

  .run-log-layout {
    display: grid;
    grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
    gap: 14px;
    min-width: 0;
  }

  .run-log-list {
    display: grid;
    align-content: start;
    gap: 8px;
    min-width: 0;
  }

  .run-log-item {
    display: grid;
    gap: 6px;
    width: 100%;
    padding: 10px 12px;
    color: var(--app-text-color-2);
    text-align: left;
    cursor: pointer;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 46%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .run-log-item:hover,
  .run-log-item.is-active {
    background: var(--app-surface-bg);
    border-color: color-mix(in srgb, var(--app-primary-color) 54%, var(--app-border-color, #d9e1ec));
  }

  .run-log-item__top,
  .run-log-item__meta {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    min-width: 0;
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .run-log-item strong {
    overflow: hidden;
    color: var(--app-text-color-1);
    font-size: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .run-log-detail {
    display: grid;
    gap: 14px;
    min-width: 0;
    padding: 14px;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .run-log-detail__summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .run-log-detail__summary > div {
    display: grid;
    gap: 3px;
    min-width: 0;
    padding: 10px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 64%, var(--app-surface-bg));
    border-radius: 7px;
  }

  .run-log-detail__summary span,
  .run-log-detail h4 {
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .run-log-detail__summary strong {
    overflow: hidden;
    color: var(--app-text-color-1);
    font-size: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .run-log-detail h4 {
    margin: 0 0 8px;
    font-weight: 650;
  }

  .run-log-error {
    padding: 9px 10px;
    color: var(--app-error-color, #d03050);
    background: color-mix(in srgb, var(--app-error-color, #d03050) 8%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-error-color, #d03050) 22%, transparent);
    border-radius: 7px;
  }

  .run-log-answer {
    max-height: 360px;
    padding: 10px 12px;
    overflow: auto;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 60%, transparent);
    border-radius: 7px;
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

    .run-log-layout {
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
