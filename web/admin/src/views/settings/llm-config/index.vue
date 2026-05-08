<template>
  <div class="llm-console">
    <n-card :bordered="false" size="small" class="proCard llm-header">
      <div class="header-grid">
        <div>
          <div class="eyebrow">LLM Runtime</div>
          <h2>模型路由中心</h2>
          <p>统一维护供应商、模型目录、业务任务、fallback 路由和调用观测。</p>
        </div>
        <n-space justify="end" align="center" class="header-actions">
          <n-statistic label="供应商" :value="providers.length" />
          <n-statistic label="模型" :value="models.length" />
          <n-statistic label="任务" :value="tasks.length" />
          <n-button secondary :loading="loading" @click="reloadAll">刷新</n-button>
        </n-space>
      </div>
    </n-card>

    <n-tabs v-model:value="activeTab" type="line" animated class="llm-tabs">
      <n-tab-pane name="providers" tab="供应商">
        <n-card :bordered="false" size="small" class="proCard">
          <template #header>供应商连接</template>
          <template #header-extra>
            <n-button type="primary" @click="openProvider()">新增供应商</n-button>
          </template>
          <n-data-table size="small" :columns="providerColumns" :data="providers" :loading="loading" :pagination="{ pageSize: 10 }" />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="models" tab="模型">
        <n-card :bordered="false" size="small" class="proCard">
          <template #header>模型目录</template>
          <template #header-extra>
            <n-button type="primary" @click="openModel()">新增模型</n-button>
          </template>
          <n-data-table size="small" :columns="modelColumns" :data="models" :loading="loading" :pagination="{ pageSize: 10 }" />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="tasks" tab="任务">
        <n-card :bordered="false" size="small" class="proCard">
          <template #header>业务 LLM 任务</template>
          <template #header-extra>
            <n-button type="primary" @click="openTask()">注册任务</n-button>
          </template>
          <n-data-table size="small" :columns="taskColumns" :data="tasks" :loading="loading" :pagination="{ pageSize: 12 }" />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="routes" tab="路由策略">
        <n-card :bordered="false" size="small" class="proCard">
          <template #header>优先级 fallback 路由</template>
          <template #header-extra>
            <n-button type="primary" @click="openPolicy()">新增策略</n-button>
          </template>
          <n-data-table size="small" :columns="policyColumns" :data="policies" :loading="loading" :pagination="{ pageSize: 8 }" />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="logs" tab="调用日志">
        <n-card :bordered="false" size="small" class="proCard">
          <template #header>最近调用</template>
          <template #header-extra>
            <n-button secondary :loading="logsLoading" @click="loadLogs">刷新日志</n-button>
          </template>
          <n-data-table size="small" :columns="logColumns" :data="logs" :loading="logsLoading" :pagination="{ pageSize: 12 }" />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <n-modal v-model:show="providerModalVisible" preset="card" :title="providerFormTitle" :style="{ width: '720px' }" :bordered="false">
      <n-form label-placement="top" :model="providerForm">
        <n-grid :cols="2" :x-gap="16">
          <n-form-item-gi label="Provider Key">
            <n-input v-model:value="providerForm.provider_key" placeholder="dashscope / siliconflow" />
          </n-form-item-gi>
          <n-form-item-gi label="展示名称">
            <n-input v-model:value="providerForm.display_name" placeholder="通义百炼 / 硅基流动" />
          </n-form-item-gi>
        </n-grid>
        <n-form-item label="Base URL">
          <n-input v-model:value="providerForm.base_url" placeholder="https://.../v1" />
        </n-form-item>
        <n-form-item label="API Key">
          <n-input v-model:value="providerForm.api_key" type="password" show-password-on="click" placeholder="留空表示保留原密钥" />
        </n-form-item>
        <n-space align="center" class="form-row">
          <n-checkbox v-model:checked="providerForm.clear_api_key">保存时清空已配置密钥</n-checkbox>
          <n-switch v-model:value="providerForm.enabled">
            <template #checked>启用</template>
            <template #unchecked>停用</template>
          </n-switch>
        </n-space>
        <n-form-item label="Extra Body JSON">
          <n-input v-model:value="providerExtraBodyText" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
        </n-form-item>
        <n-space justify="end">
          <n-button @click="providerModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="saveProviderForm">保存</n-button>
        </n-space>
      </n-form>
    </n-modal>

    <n-modal v-model:show="modelModalVisible" preset="card" :title="modelFormTitle" :style="{ width: '720px' }" :bordered="false">
      <n-form label-placement="top" :model="modelForm">
        <n-grid :cols="2" :x-gap="16">
          <n-form-item-gi label="Model Key">
            <n-input v-model:value="modelForm.model_key" placeholder="dashscope.qwen-plus" />
          </n-form-item-gi>
          <n-form-item-gi label="供应商">
            <n-select v-model:value="modelForm.provider_key" :options="providerOptions" filterable placeholder="选择供应商" />
          </n-form-item-gi>
        </n-grid>
        <n-grid :cols="2" :x-gap="16">
          <n-form-item-gi label="供应商模型名">
            <n-input v-model:value="modelForm.model_name" placeholder="qwen-plus / Qwen/Qwen3-32B" />
          </n-form-item-gi>
          <n-form-item-gi label="展示名称">
            <n-input v-model:value="modelForm.display_name" />
          </n-form-item-gi>
        </n-grid>
        <n-grid :cols="2" :x-gap="16">
          <n-form-item-gi label="上下文长度">
            <n-input-number v-model:value="modelForm.context_window" clearable :min="1" />
          </n-form-item-gi>
          <n-form-item-gi label="状态">
            <n-switch v-model:value="modelForm.enabled">
              <template #checked>启用</template>
              <template #unchecked>停用</template>
            </n-switch>
          </n-form-item-gi>
        </n-grid>
        <n-form-item label="Capabilities JSON">
          <n-input v-model:value="modelCapabilitiesText" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
        </n-form-item>
        <n-space justify="end">
          <n-button @click="modelModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="saveModelForm">保存</n-button>
        </n-space>
      </n-form>
    </n-modal>

    <n-modal v-model:show="taskModalVisible" preset="card" :title="taskFormTitle" :style="{ width: '720px' }" :bordered="false">
      <n-form label-placement="top" :model="taskForm">
        <n-form-item label="Task Key">
          <n-input v-model:value="taskForm.task_key" placeholder="function_point.recommendation.rank" />
        </n-form-item>
        <n-alert type="info" :bordered="false" class="task-key-hint">
          只需要维护稳定的 Task Key。系统会按点号自动推导领域、场景和任务名。
        </n-alert>
        <n-form-item label="展示名称">
          <n-input v-model:value="taskForm.display_name" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="taskForm.description" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
        </n-form-item>
        <n-space justify="space-between" align="center">
          <n-switch v-model:value="taskForm.enabled">
            <template #checked>启用</template>
            <template #unchecked>停用</template>
          </n-switch>
          <n-space>
            <n-button @click="taskModalVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="saveTaskForm">保存</n-button>
          </n-space>
        </n-space>
      </n-form>
    </n-modal>

    <n-modal v-model:show="policyModalVisible" preset="card" :title="policyFormTitle" :style="{ width: '860px' }" :bordered="false">
      <n-form label-placement="top" :model="policyForm">
        <n-grid :cols="2" :x-gap="16">
          <n-form-item-gi label="Route Key">
            <n-select
              v-model:value="policyForm.route_key"
              :options="routeOptions"
              filterable
              placeholder="选择已注册任务或兜底路由"
              @update:value="syncPolicyDisplayName"
            />
          </n-form-item-gi>
          <n-form-item-gi label="展示名称">
            <n-input v-model:value="policyForm.display_name" />
          </n-form-item-gi>
        </n-grid>
        <n-space align="center" class="form-row">
          <n-tag type="info" size="small">priority</n-tag>
          <n-switch v-model:value="policyForm.enabled">
            <template #checked>启用</template>
            <template #unchecked>停用</template>
          </n-switch>
          <n-button size="small" secondary @click="addPolicyEntry">添加候选模型</n-button>
        </n-space>
        <div class="entry-list">
          <div v-for="(entry, index) in policyForm.entries" :key="index" class="entry-row">
            <n-grid :cols="12" :x-gap="10" responsive="screen">
              <n-form-item-gi :span="4" label="模型">
                <n-select v-model:value="entry.model_key" :options="modelOptions" filterable />
              </n-form-item-gi>
              <n-form-item-gi :span="2" label="优先级">
                <n-input-number v-model:value="entry.priority" :min="1" />
              </n-form-item-gi>
              <n-form-item-gi :span="2" label="温度">
                <n-input-number v-model:value="entry.temperature" :min="0" :max="2" :step="0.1" />
              </n-form-item-gi>
              <n-form-item-gi :span="2" label="超时">
                <n-input-number v-model:value="entry.timeout_seconds" :min="1" :max="600" />
              </n-form-item-gi>
              <n-form-item-gi :span="2" label="格式">
                <n-select v-model:value="entry.response_format" :options="responseFormatOptions" />
              </n-form-item-gi>
            </n-grid>
            <n-space justify="space-between" align="center">
              <n-checkbox v-model:checked="entry.enabled">启用候选</n-checkbox>
              <n-button size="small" text type="error" @click="removePolicyEntry(index)">移除</n-button>
            </n-space>
          </div>
        </div>
        <n-space justify="end">
          <n-button @click="policyModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="savePolicyForm">保存</n-button>
        </n-space>
      </n-form>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, onMounted, reactive, ref } from 'vue';
  import { NButton, NTag, NSpace, useMessage } from 'naive-ui';
  import type { DataTableColumns } from 'naive-ui';
  import {
    getLlmCallLogs,
    getLlmModels,
    getLlmProviders,
    getLlmRoutingPolicies,
    getLlmTasks,
    registerLlmTask,
    saveLlmModel,
    saveLlmProvider,
    saveLlmRoutingPolicy,
  } from '@/api/business';

  type JsonObject = Record<string, unknown>;
  type EntryForm = {
    model_key: string;
    priority: number;
    temperature: number;
    timeout_seconds: number;
    max_retries: number;
    response_format: string;
    extra_body: JsonObject;
    enabled: boolean;
  };

  const message = useMessage();
  const activeTab = ref('providers');
  const loading = ref(false);
  const logsLoading = ref(false);
  const saving = ref(false);
  const providers = ref<Recordable[]>([]);
  const models = ref<Recordable[]>([]);
  const tasks = ref<Recordable[]>([]);
  const policies = ref<Recordable[]>([]);
  const logs = ref<Recordable[]>([]);

  const providerModalVisible = ref(false);
  const modelModalVisible = ref(false);
  const taskModalVisible = ref(false);
  const policyModalVisible = ref(false);
  const editingProvider = ref(false);
  const editingModel = ref(false);
  const editingTask = ref(false);
  const editingPolicy = ref(false);

  const providerExtraBodyText = ref('{}');
  const modelCapabilitiesText = ref('{}');

  const providerForm = reactive({
    provider_key: '',
    display_name: '',
    base_url: '',
    api_key: '',
    clear_api_key: false,
    auth_type: 'bearer',
    extra_body: {} as JsonObject,
    enabled: true,
  });

  const modelForm = reactive({
    model_key: '',
    provider_key: '',
    model_name: '',
    display_name: '',
    capabilities: {} as JsonObject,
    context_window: null as number | null,
    enabled: true,
  });

  const taskForm = reactive({
    task_key: '',
    context_key: '',
    scene_key: '',
    task_name: '',
    display_name: '',
    description: '',
    owner_context: '',
    enabled: true,
  });

  const policyForm = reactive({
    route_key: '',
    display_name: '',
    strategy: 'priority',
    enabled: true,
    entries: [] as EntryForm[],
  });

  const providerFormTitle = computed(() => (editingProvider.value ? '编辑供应商' : '新增供应商'));
  const modelFormTitle = computed(() => (editingModel.value ? '编辑模型' : '新增模型'));
  const taskFormTitle = computed(() => (editingTask.value ? '编辑任务' : '注册任务'));
  const policyFormTitle = computed(() => (editingPolicy.value ? '编辑路由策略' : '新增路由策略'));

  const providerOptions = computed(() =>
    providers.value.map((item) => ({ label: `${item.display_name || item.provider_key} (${item.provider_key})`, value: item.provider_key }))
  );
  const modelOptions = computed(() =>
    models.value.map((item) => ({ label: `${item.display_name || item.model_name} (${item.model_key})`, value: item.model_key }))
  );
  const routeOptions = computed(() => {
    const options: { label: string; value: string }[] = [];
    const seen = new Set<string>();
    const push = (value: string, label?: string) => {
      if (!value || seen.has(value)) return;
      seen.add(value);
      options.push({ value, label: label || value });
    };

    tasks.value.forEach((task) => {
      const key = String(task.task_key || '').trim();
      if (!key) return;
      push(key, `${task.display_name || key} - ${key}`);
      routeFallbackKeys(key).forEach((fallback) => push(fallback, `${fallback}（兜底）`));
    });
    push('default', 'default（全局兜底）');
    return options;
  });
  const responseFormatOptions = [
    { label: 'text', value: 'text' },
    { label: 'json', value: 'json' },
  ];

  const providerColumns: DataTableColumns<Recordable> = [
    { title: 'Provider Key', key: 'provider_key', minWidth: 160 },
    { title: '名称', key: 'display_name', minWidth: 140 },
    { title: 'Base URL', key: 'base_url', minWidth: 260, ellipsis: { tooltip: true } },
    {
      title: '密钥',
      key: 'api_key_configured',
      width: 120,
      render(row) {
        return h(NTag, { size: 'small', type: row.api_key_configured ? 'success' : 'warning' }, () =>
          row.api_key_configured ? row.api_key_mask || '已配置' : '未配置'
        );
      },
    },
    { title: '状态', key: 'enabled', width: 100, render: renderStatus },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right',
      render(row) {
        return h(NButton, { size: 'small', secondary: true, onClick: () => openProvider(row) }, () => '编辑');
      },
    },
  ];

  const modelColumns: DataTableColumns<Recordable> = [
    { title: 'Model Key', key: 'model_key', minWidth: 190 },
    { title: '供应商', key: 'provider_key', width: 130 },
    { title: '模型名', key: 'model_name', minWidth: 190 },
    { title: '展示名称', key: 'display_name', minWidth: 150 },
    { title: '上下文', key: 'context_window', width: 110 },
    { title: '状态', key: 'enabled', width: 100, render: renderStatus },
    { title: '操作', key: 'actions', width: 100, fixed: 'right', render: (row) => h(NButton, { size: 'small', secondary: true, onClick: () => openModel(row) }, () => '编辑') },
  ];

  const taskColumns: DataTableColumns<Recordable> = [
    { title: 'Task Key', key: 'task_key', minWidth: 260 },
    { title: '领域', key: 'context_key', width: 140 },
    { title: '场景', key: 'scene_key', width: 150 },
    { title: '任务', key: 'task_name', width: 130 },
    { title: '名称', key: 'display_name', minWidth: 160 },
    { title: '状态', key: 'enabled', width: 100, render: renderStatus },
    { title: '操作', key: 'actions', width: 100, fixed: 'right', render: (row) => h(NButton, { size: 'small', secondary: true, onClick: () => openTask(row) }, () => '编辑') },
  ];

  const policyColumns: DataTableColumns<Recordable> = [
    { title: 'Route Key', key: 'route_key', minWidth: 260 },
    { title: '名称', key: 'display_name', minWidth: 160 },
    { title: '策略', key: 'strategy', width: 100 },
    {
      title: '候选模型',
      key: 'entries',
      minWidth: 260,
      render(row) {
        const entries = Array.isArray(row.entries) ? row.entries : [];
        return h(
          NSpace,
          { size: 4 },
          () =>
            entries.map((entry: Recordable) =>
              h(NTag, { size: 'small', type: 'info' }, () => `${entry.priority}. ${entry.model_key}`)
            )
        );
      },
    },
    { title: '操作', key: 'actions', width: 100, fixed: 'right', render: (row) => h(NButton, { size: 'small', secondary: true, onClick: () => openPolicy(row) }, () => '编辑') },
  ];

  const logColumns: DataTableColumns<Recordable> = [
    { title: '时间', key: 'created_at', width: 180, render: (row) => formatDateTime(row.created_at) },
    { title: '任务', key: 'task_key', minWidth: 260, ellipsis: { tooltip: true } },
    { title: 'Route', key: 'route_key', minWidth: 220, ellipsis: { tooltip: true } },
    { title: '模型', key: 'model_key', minWidth: 190 },
    { title: '状态', key: 'status', width: 100, render: renderLogStatus },
    { title: 'fallback', key: 'is_fallback', width: 90, render: (row) => (row.is_fallback ? '是' : '否') },
    { title: '耗时(秒)', key: 'elapsed_ms', width: 100, render: (row) => formatElapsedSeconds(row.elapsed_ms) },
    { title: 'Tokens', key: 'total_tokens', width: 100 },
    { title: '错误', key: 'error_message', minWidth: 220, ellipsis: { tooltip: true } },
  ];

  function padTime(value: number) {
    return String(value).padStart(2, '0');
  }

  function formatDateFromObject(date: Date) {
    return [
      date.getFullYear(),
      padTime(date.getMonth() + 1),
      padTime(date.getDate()),
    ].join('-') + ` ${padTime(date.getHours())}:${padTime(date.getMinutes())}:${padTime(date.getSeconds())}`;
  }

  function formatDateTime(value: unknown) {
    if (!value) return '-';
    const raw = String(value).trim();
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
    if (hasTimezone) {
      const date = new Date(raw);
      return Number.isNaN(date.getTime()) ? raw : formatDateFromObject(date);
    }
    const localMatch = raw.match(/^(\d{4}-\d{2}-\d{2})[T\s](\d{2}:\d{2}:\d{2})/);
    if (localMatch) return `${localMatch[1]} ${localMatch[2]}`;
    const date = new Date(raw);
    return Number.isNaN(date.getTime()) ? raw : formatDateFromObject(date);
  }

  function formatElapsedSeconds(value: unknown) {
    const elapsedMs = Number(value ?? 0);
    if (!Number.isFinite(elapsedMs)) return '-';
    const seconds = elapsedMs / 1000;
    return `${seconds.toFixed(2).replace(/\.?0+$/, '')}s`;
  }

  function renderStatus(row: Recordable) {
    return h(NTag, { size: 'small', type: row.enabled ? 'success' : 'default' }, () => (row.enabled ? '启用' : '停用'));
  }

  function renderLogStatus(row: Recordable) {
    const success = row.status === 'success';
    return h(NTag, { size: 'small', type: success ? 'success' : 'error' }, () => (success ? '成功' : '失败'));
  }

  async function reloadAll() {
    loading.value = true;
    try {
      const [providerPayload, modelPayload, taskPayload, policyPayload] = await Promise.all([
        getLlmProviders(),
        getLlmModels(),
        getLlmTasks(),
        getLlmRoutingPolicies(),
      ]);
      providers.value = providerPayload.items || [];
      models.value = modelPayload.items || [];
      tasks.value = taskPayload.items || [];
      policies.value = policyPayload.items || [];
    } finally {
      loading.value = false;
    }
  }

  async function loadLogs() {
    logsLoading.value = true;
    try {
      const payload = await getLlmCallLogs(80);
      logs.value = payload.items || [];
    } finally {
      logsLoading.value = false;
    }
  }

  function openProvider(row?: Recordable) {
    editingProvider.value = Boolean(row);
    Object.assign(providerForm, {
      provider_key: row?.provider_key || '',
      display_name: row?.display_name || '',
      base_url: row?.base_url || '',
      api_key: '',
      clear_api_key: false,
      auth_type: row?.auth_type || 'bearer',
      extra_body: row?.extra_body || {},
      enabled: row?.enabled ?? true,
    });
    providerExtraBodyText.value = JSON.stringify(providerForm.extra_body || {}, null, 2);
    providerModalVisible.value = true;
  }

  function openModel(row?: Recordable) {
    editingModel.value = Boolean(row);
    Object.assign(modelForm, {
      model_key: row?.model_key || '',
      provider_key: row?.provider_key || '',
      model_name: row?.model_name || '',
      display_name: row?.display_name || '',
      capabilities: row?.capabilities || {},
      context_window: row?.context_window ?? null,
      enabled: row?.enabled ?? true,
    });
    modelCapabilitiesText.value = JSON.stringify(modelForm.capabilities || {}, null, 2);
    modelModalVisible.value = true;
  }

  function openTask(row?: Recordable) {
    editingTask.value = Boolean(row);
    Object.assign(taskForm, {
      task_key: row?.task_key || '',
      context_key: row?.context_key || '',
      scene_key: row?.scene_key || '',
      task_name: row?.task_name || '',
      display_name: row?.display_name || '',
      description: row?.description || '',
      owner_context: row?.owner_context || '',
      enabled: row?.enabled ?? true,
    });
    taskModalVisible.value = true;
  }

  function openPolicy(row?: Recordable) {
    editingPolicy.value = Boolean(row);
    Object.assign(policyForm, {
      route_key: row?.route_key || '',
      display_name: row?.display_name || '',
      strategy: row?.strategy || 'priority',
      enabled: row?.enabled ?? true,
      entries: Array.isArray(row?.entries)
        ? row.entries.map((entry: Recordable) => ({
            model_key: entry.model_key || '',
            priority: Number(entry.priority || 100),
            temperature: Number(entry.temperature ?? 0.1),
            timeout_seconds: Number(entry.timeout_seconds || 120),
            max_retries: Number(entry.max_retries || 0),
            response_format: entry.response_format || 'text',
            extra_body: entry.extra_body || {},
            enabled: entry.enabled ?? true,
          }))
        : [],
    });
    if (!policyForm.entries.length) {
      addPolicyEntry();
    }
    policyModalVisible.value = true;
  }

  function routeFallbackKeys(taskKey: string) {
    const parts = taskKey.split('.').filter(Boolean);
    const keys: string[] = [];
    if (parts.length >= 2) {
      keys.push([...parts.slice(0, -1), 'default'].join('.'));
    }
    if (parts.length) {
      keys.push(`${parts[0]}.default`);
    }
    return keys;
  }

  function deriveTaskParts(taskKey: string) {
    const parts = taskKey.split('.').map((item) => item.trim()).filter(Boolean);
    return {
      context_key: parts[0] || '',
      scene_key: parts[1] || '',
      task_name: parts[parts.length - 1] || '',
      owner_context: parts[0] || '',
    };
  }

  function syncPolicyDisplayName() {
    if (policyForm.display_name) return;
    const task = tasks.value.find((item) => item.task_key === policyForm.route_key);
    policyForm.display_name = task?.display_name || policyForm.route_key;
  }

  function addPolicyEntry() {
    policyForm.entries.push({
      model_key: '',
      priority: policyForm.entries.length + 1,
      temperature: 0.1,
      timeout_seconds: 120,
      max_retries: 0,
      response_format: 'text',
      extra_body: {},
      enabled: true,
    });
  }

  function removePolicyEntry(index: number) {
    policyForm.entries.splice(index, 1);
  }

  function parseJson(text: string, label: string): JsonObject | null {
    try {
      const payload = JSON.parse(text || '{}');
      if (!payload || Array.isArray(payload) || typeof payload !== 'object') {
        message.error(`${label} 必须是 JSON object`);
        return null;
      }
      return payload;
    } catch {
      message.error(`${label} 不是合法 JSON`);
      return null;
    }
  }

  async function saveProviderForm() {
    const extraBody = parseJson(providerExtraBodyText.value, 'Extra Body');
    if (!extraBody) return;
    saving.value = true;
    try {
      await saveLlmProvider({ ...providerForm, extra_body: extraBody });
      message.success('供应商已保存');
      providerModalVisible.value = false;
      await reloadAll();
    } finally {
      saving.value = false;
    }
  }

  async function saveModelForm() {
    const capabilities = parseJson(modelCapabilitiesText.value, 'Capabilities');
    if (!capabilities) return;
    saving.value = true;
    try {
      await saveLlmModel({ ...modelForm, capabilities });
      message.success('模型已保存');
      modelModalVisible.value = false;
      await reloadAll();
    } finally {
      saving.value = false;
    }
  }

  async function saveTaskForm() {
    const taskParts = deriveTaskParts(taskForm.task_key);
    saving.value = true;
    try {
      await registerLlmTask({ ...taskForm, ...taskParts });
      message.success('任务已保存');
      taskModalVisible.value = false;
      await reloadAll();
    } finally {
      saving.value = false;
    }
  }

  async function savePolicyForm() {
    if (!policyForm.entries.length || policyForm.entries.some((entry) => !entry.model_key)) {
      message.warning('请至少配置一个候选模型');
      return;
    }
    saving.value = true;
    try {
      await saveLlmRoutingPolicy({ ...policyForm, strategy: 'priority' });
      message.success('路由策略已保存');
      policyModalVisible.value = false;
      await reloadAll();
    } finally {
      saving.value = false;
    }
  }

  onMounted(async () => {
    await reloadAll();
    await loadLogs();
  });
</script>

<style scoped>
  .llm-console {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .llm-header {
    overflow: hidden;
  }

  .header-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 24px;
    align-items: center;
  }

  .eyebrow {
    color: #667085;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0;
    text-transform: uppercase;
  }

  h2 {
    margin: 4px 0 6px;
    font-size: 24px;
    line-height: 1.25;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: #667085;
  }

  .header-actions {
    min-width: 360px;
  }

  .llm-tabs :deep(.n-tabs-nav) {
    padding: 0 4px;
  }

  .form-row {
    margin-bottom: 16px;
  }

  .entry-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin: 4px 0 18px;
  }

  .entry-row {
    border: 1px solid #eaecf0;
    border-radius: 8px;
    padding: 12px;
    background: #fcfcfd;
  }

  @media (max-width: 900px) {
    .header-grid {
      grid-template-columns: 1fr;
    }

    .header-actions {
      justify-content: flex-start !important;
      min-width: 0;
    }
  }
</style>
