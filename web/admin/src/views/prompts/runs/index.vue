<template>
  <div class="prompt-run-page">
    <ListPageRuntime :schema="pageSchema" :rows="filteredRows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-input v-model:value="contractFilter" clearable placeholder="过滤 Contract Key" class="prompt-run-page__keyword" />
        <n-select v-model:value="statusFilter" clearable placeholder="状态" :options="statusOptions" class="prompt-run-page__select" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="testDrawerVisible" width="720">
      <n-drawer-content title="测试运行">
        <n-form label-placement="top">
          <n-form-item label="Contract Key">
            <n-select v-model:value="testForm.contract_key" :options="contractOptions" filterable placeholder="选择任务契约" />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="环境">
              <n-select v-model:value="testForm.environment" :options="environmentOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="指定版本 ID">
              <n-input-number v-model:value="testForm.prompt_version_id" clearable :min="1" placeholder="为空时使用有效绑定" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="变量 JSON">
            <n-input v-model:value="variablesText" type="textarea" :autosize="{ minRows: 10, maxRows: 16 }" />
          </n-form-item>
        </n-form>
        <section v-if="testResult" class="test-result">
          <div class="test-result__summary">
            <AppStatusTag :tone="testResult.schema_valid ? 'success' : 'error'" :label="testResult.schema_valid ? 'Schema 通过' : 'Schema 未通过'" />
            <span>Run #{{ testResult.run.id }}</span>
          </div>
          <n-tabs type="line" animated>
            <n-tab-pane name="messages" tab="渲染消息">
              <pre>{{ stringifyJson(testResult.rendered_messages) }}</pre>
            </n-tab-pane>
            <n-tab-pane name="output" tab="模型输出">
              <pre>{{ testResult.output_text || stringifyJson(testResult.output_json || {}) }}</pre>
            </n-tab-pane>
            <n-tab-pane name="errors" tab="校验错误">
              <pre>{{ stringifyJson(testResult.validation_errors || []) }}</pre>
            </n-tab-pane>
          </n-tabs>
        </section>
        <template #footer>
          <n-space justify="end">
            <n-button @click="testDrawerVisible = false">关闭</n-button>
            <n-button type="primary" :loading="testing" @click="submitTest">执行测试</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="detailDrawerVisible" width="820">
      <n-drawer-content :title="selectedRun ? `运行记录 #${selectedRun.id}` : '运行记录'">
        <section v-if="selectedRun" class="run-detail">
          <dl class="run-detail__meta">
            <div>
              <dt>Contract</dt>
              <dd>{{ selectedRun.contract_key }}</dd>
            </div>
            <div>
              <dt>LLM Task</dt>
              <dd>{{ selectedRun.llm_task_key }}</dd>
            </div>
            <div>
              <dt>耗时</dt>
              <dd>{{ formatElapsed(selectedRun.elapsed_ms) }}</dd>
            </div>
            <div>
              <dt>请求 ID</dt>
              <dd>{{ selectedRun.request_id }}</dd>
            </div>
          </dl>
          <n-tabs type="line" animated>
            <n-tab-pane name="input" tab="输入">
              <pre>{{ stringifyJson(selectedRun.input) }}</pre>
            </n-tab-pane>
            <n-tab-pane name="messages" tab="渲染消息">
              <pre>{{ stringifyJson(selectedRun.rendered_messages) }}</pre>
            </n-tab-pane>
            <n-tab-pane name="output" tab="输出">
              <pre>{{ selectedRun.output_text || stringifyJson(selectedRun.output_json || {}) }}</pre>
            </n-tab-pane>
            <n-tab-pane name="errors" tab="错误">
              <pre>{{ stringifyJson(selectedRun.validation_errors || []) }}</pre>
            </n-tab-pane>
          </n-tabs>
        </section>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { getPromptContracts, getPromptRun, getPromptRuns, testPrompt, type PromptRun, type PromptTaskContract } from '@/api/aiAssets';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const canTest = computed(() => hasPermission(['prompt:assets:manage']));
  const loading = ref(false);
  const testing = ref(false);
  const rows = ref<PromptRun[]>([]);
  const contracts = ref<PromptTaskContract[]>([]);
  const contractFilter = ref('');
  const statusFilter = ref<string | null>(null);
  const testDrawerVisible = ref(false);
  const detailDrawerVisible = ref(false);
  const selectedRun = ref<PromptRun | null>(null);
  const testResult = ref<Awaited<ReturnType<typeof testPrompt>> | null>(null);
  const variablesText = ref('{\n  "transcript": "这里填写测试输入"\n}');
  const testForm = reactive({
    contract_key: '',
    prompt_version_id: null as number | null,
    environment: 'prod',
  });

  const statusOptions: SelectOption[] = [
    { label: '成功', value: 'succeeded' },
    { label: '失败', value: 'failed' },
  ];
  const environmentOptions: SelectOption[] = [
    { label: 'dev', value: 'dev' },
    { label: 'test', value: 'test' },
    { label: 'prod', value: 'prod' },
  ];
  const contractOptions = computed<SelectOption[]>(() =>
    contracts.value.map((contract) => ({
      label: `${contract.display_name || contract.contract_key} · ${contract.contract_key}`,
      value: contract.contract_key,
    }))
  );
  const filteredRows = computed(() => {
    const text = contractFilter.value.trim().toLowerCase();
    return rows.value.filter((row) => {
      const matchesContract = !text || row.contract_key.toLowerCase().includes(text);
      return matchesContract && (!statusFilter.value || row.status === statusFilter.value);
    });
  });

  const columns: DataTableColumns<PromptRun> = [
    { title: '时间', key: 'create_time', width: 170, render: (row) => formatToDateTime(row.create_time || '') },
    { title: 'Contract Key', key: 'contract_key', minWidth: 260, ellipsis: { tooltip: true } },
    { title: 'LLM Task', key: 'llm_task_key', minWidth: 220, ellipsis: { tooltip: true } },
    { title: 'Prompt Version ID', key: 'prompt_version_id', width: 150 },
    { title: '状态', key: 'status', width: 100, render: (row) => h(AppStatusTag, { tone: row.status === 'succeeded' ? 'success' : 'error', label: row.status === 'succeeded' ? '成功' : '失败' }) },
    { title: 'Schema', key: 'schema_valid', width: 100, render: (row) => h(AppStatusTag, { tone: row.schema_valid ? 'success' : 'warning', label: row.schema_valid ? '通过' : '未通过' }) },
    { title: '耗时', key: 'elapsed_ms', width: 90, render: (row) => formatElapsed(row.elapsed_ms) },
    { title: 'Request ID', key: 'request_id', minWidth: 180, ellipsis: { tooltip: true } },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [{ label: '详情', onClick: () => openDetail(row) }],
        });
      },
    },
  ];

  const pageSchema = computed(() => defineListPage<PromptRun>({
    id: 'prompts.runs',
    title: '运行记录',
    description: '追踪提示词执行证据、渲染消息、模型输出和 Schema 校验结果。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1480,
      tableProps: { size: 'small', pagination: false },
    },
    toolbar: {
      primaryAction: canTest.value
        ? { key: 'test', label: '测试运行', type: 'primary', onClick: () => openTest() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  }));

  function openTest() {
    testResult.value = null;
    testForm.contract_key = contracts.value[0]?.contract_key || '';
    testForm.prompt_version_id = null;
    testForm.environment = 'prod';
    variablesText.value = '{\n  "transcript": "这里填写测试输入"\n}';
    testDrawerVisible.value = true;
  }

  async function submitTest() {
    if (!testForm.contract_key) {
      message.warning('请选择 Contract Key');
      return;
    }
    const variables = parseJsonObject(variablesText.value, '变量 JSON');
    if (!variables) return;
    testing.value = true;
    try {
      testResult.value = await testPrompt({
        contract_key: testForm.contract_key,
        prompt_version_id: testForm.prompt_version_id,
        environment: testForm.environment,
        variables,
      });
      message.success('测试运行已完成');
      await reload();
    } finally {
      testing.value = false;
    }
  }

  async function openDetail(row: PromptRun) {
    const payload = await getPromptRun(row.id);
    selectedRun.value = payload.item;
    detailDrawerVisible.value = true;
  }

  async function reload() {
    loading.value = true;
    try {
      const [runPayload, contractPayload] = await Promise.all([
        getPromptRuns({ page: 1, page_size: 100 }),
        getPromptContracts({ page: 1, page_size: 100 }),
      ]);
      rows.value = runPayload.items || [];
      contracts.value = contractPayload.items || [];
    } finally {
      loading.value = false;
    }
  }

  function parseJsonObject(text: string, label: string): Record<string, unknown> | null {
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

  function stringifyJson(value: unknown) {
    return JSON.stringify(value || {}, null, 2);
  }

  function formatElapsed(value: unknown) {
    const elapsed = Number(value || 0);
    if (!Number.isFinite(elapsed)) return '-';
    return `${(elapsed / 1000).toFixed(2).replace(/\.?0+$/, '')}s`;
  }

  reload();
</script>

<style lang="less" scoped>
  .prompt-run-page {
    min-width: 0;
  }

  .prompt-run-page__keyword {
    width: min(340px, 100%);
  }

  .prompt-run-page__select {
    width: 140px;
  }

  .test-result,
  .run-detail {
    display: grid;
    gap: 12px;
    margin-top: 16px;
  }

  .test-result__summary {
    display: flex;
    gap: 10px;
    align-items: center;
    color: var(--app-text-color-2);
    font-size: 13px;
  }

  .run-detail__meta {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin: 0;
  }

  .run-detail__meta div {
    display: grid;
    gap: 4px;
    min-width: 0;
    padding: 10px;
    background: var(--app-surface-muted-bg);
    border-radius: 8px;
  }

  .run-detail__meta dt {
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  .run-detail__meta dd {
    margin: 0;
    overflow-wrap: anywhere;
    color: var(--app-text-color);
    font-size: 13px;
  }

  pre {
    max-height: 420px;
    padding: 12px;
    overflow: auto;
    color: var(--app-text-color);
    background: var(--app-surface-muted-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: 8px;
  }

  @media (max-width: 760px) {
    .run-detail__meta {
      grid-template-columns: 1fr;
    }
  }
</style>
