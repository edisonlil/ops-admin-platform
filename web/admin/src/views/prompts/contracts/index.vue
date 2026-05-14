<template>
  <div class="prompt-contract-page">
    <ListPageRuntime :schema="pageSchema" :rows="filteredRows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索契约 Key、名称、说明" class="prompt-contract-page__keyword" />
        <n-select v-model:value="ownerFilter" clearable placeholder="归属上下文" :options="ownerOptions" class="prompt-contract-page__select" />
        <n-select v-model:value="enabledFilter" clearable placeholder="状态" :options="enabledOptions" class="prompt-contract-page__select" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="760">
      <n-drawer-content :title="form.original_contract_key ? '编辑任务契约' : '新建任务契约'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-form-item label="Contract Key" path="contract_key">
            <n-input v-model:value="form.contract_key" placeholder="voice_analysis.transcript.summary" />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="显示名称">
              <n-input v-model:value="form.display_name" />
            </n-form-item-gi>
            <n-form-item-gi label="LLM Task Key">
              <n-input v-model:value="form.llm_task_key" placeholder="默认同 Contract Key" />
            </n-form-item-gi>
            <n-form-item-gi label="归属上下文">
              <n-input v-model:value="form.owner_context" placeholder="voice_analysis" />
            </n-form-item-gi>
            <n-form-item-gi label="任务类型">
              <n-select v-model:value="form.task_kind" :options="taskKindOptions" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="说明">
            <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
          </n-form-item>
          <n-form-item label="所需能力">
            <n-dynamic-tags v-model:value="form.required_capabilities" />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="输入 Schema JSON">
              <n-input v-model:value="inputSchemaText" type="textarea" :autosize="{ minRows: 7, maxRows: 12 }" />
            </n-form-item-gi>
            <n-form-item-gi label="输出 Schema JSON">
              <n-input v-model:value="outputSchemaText" type="textarea" :autosize="{ minRows: 7, maxRows: 12 }" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="允许的提示词范围 JSON">
            <n-input v-model:value="scopeText" type="textarea" :autosize="{ minRows: 5, maxRows: 9 }" />
          </n-form-item>
          <n-space align="center">
            <n-switch v-model:value="form.enabled">
              <template #checked>启用</template>
              <template #unchecked>停用</template>
            </n-switch>
          </n-space>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存契约</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusGroup from '@/components/Application/AppStatusGroup.vue';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { getPromptContracts, savePromptContract, type PromptTaskContract } from '@/api/aiAssets';

  type ContractForm = Partial<PromptTaskContract> & {
    original_contract_key?: string;
    required_capabilities: string[];
  };

  const message = useMessage();
  const { hasPermission } = usePermission();
  const canManage = computed(() => hasPermission(['prompt:contracts:manage']));
  const loading = ref(false);
  const saving = ref(false);
  const rows = ref<PromptTaskContract[]>([]);
  const keyword = ref('');
  const ownerFilter = ref<string | null>(null);
  const enabledFilter = ref<boolean | null>(null);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const inputSchemaText = ref('{}');
  const outputSchemaText = ref('{}');
  const scopeText = ref('{\n  "tags": [],\n  "prompt_keys": []\n}');

  const form = reactive<ContractForm>({
    contract_key: '',
    owner_context: 'general',
    task_kind: 'single_call',
    display_name: '',
    description: '',
    llm_task_key: '',
    required_capabilities: [],
    enabled: true,
  });

  const rules: FormRules = {
    contract_key: [{ required: true, message: '请输入 Contract Key', trigger: ['blur', 'input'] }],
  };
  const taskKindOptions: SelectOption[] = [
    { label: '单次调用', value: 'single_call' },
    { label: '工作流步骤', value: 'workflow_step' },
    { label: '工作流', value: 'workflow' },
  ];
  const enabledOptions: SelectOption[] = [
    { label: '启用', value: true },
    { label: '停用', value: false },
  ];

  const ownerOptions = computed<SelectOption[]>(() => uniqueOptions(rows.value.map((row) => row.owner_context)));
  const filteredRows = computed(() => {
    const text = keyword.value.trim().toLowerCase();
    return rows.value.filter((row) => {
      const matchesKeyword =
        !text ||
        row.contract_key.toLowerCase().includes(text) ||
        row.display_name.toLowerCase().includes(text) ||
        row.description.toLowerCase().includes(text);
      return matchesKeyword && (!ownerFilter.value || row.owner_context === ownerFilter.value) && (enabledFilter.value === null || row.enabled === enabledFilter.value);
    });
  });

  const columns: DataTableColumns<PromptTaskContract> = [
    { title: 'Contract Key', key: 'contract_key', minWidth: 260, ellipsis: { tooltip: true } },
    { title: '名称', key: 'display_name', minWidth: 160 },
    { title: '上下文', key: 'owner_context', width: 150 },
    { title: '类型', key: 'task_kind', width: 140, render: (row) => taskKindLabel(row.task_kind) },
    {
      title: '能力',
      key: 'required_capabilities',
      minWidth: 220,
      render(row) {
        return h(AppStatusGroup, {
          items: row.required_capabilities.map((item) => ({ key: item, label: item, tone: 'info' })),
        });
      },
    },
    { title: '状态', key: 'enabled', width: 100, render: (row) => h(AppStatusTag, { tone: row.enabled ? 'success' : 'neutral', label: row.enabled ? '启用' : '停用' }) },
    { title: '更新时间', key: 'update_time', width: 170, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [{ label: '编辑', show: canManage.value, onClick: () => openEdit(row) }],
        });
      },
    },
  ];

  const pageSchema = computed(() => defineListPage<PromptTaskContract>({
    id: 'prompts.contracts',
    title: '任务契约',
    description: '定义任务的输入、输出、能力要求和可用提示词范围。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1320,
      tableProps: { size: 'small', pagination: false },
    },
    toolbar: {
      primaryAction: canManage.value
        ? { key: 'create', label: '新建契约', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  }));

  function uniqueOptions(values: string[]) {
    return Array.from(new Set(values.filter(Boolean))).map((value) => ({ label: value, value }));
  }

  function resetForm() {
    Object.assign(form, {
      original_contract_key: undefined,
      contract_key: '',
      owner_context: 'general',
      task_kind: 'single_call',
      display_name: '',
      description: '',
      llm_task_key: '',
      required_capabilities: [],
      enabled: true,
    });
    inputSchemaText.value = '{}';
    outputSchemaText.value = '{}';
    scopeText.value = '{\n  "tags": [],\n  "prompt_keys": []\n}';
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: PromptTaskContract) {
    Object.assign(form, {
      ...row,
      original_contract_key: row.contract_key,
      required_capabilities: [...(row.required_capabilities || [])],
    });
    inputSchemaText.value = stringifyJson(row.input_schema);
    outputSchemaText.value = stringifyJson(row.output_schema);
    scopeText.value = stringifyJson(row.allowed_prompt_scopes);
    drawerVisible.value = true;
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    const inputSchema = parseJsonObject(inputSchemaText.value, '输入 Schema');
    const outputSchema = parseJsonObject(outputSchemaText.value, '输出 Schema');
    const allowedPromptScopes = parseJsonObject(scopeText.value, '允许范围');
    if (!inputSchema || !outputSchema || !allowedPromptScopes) return;
    saving.value = true;
    try {
      await savePromptContract({
        ...form,
        input_schema: inputSchema,
        output_schema: outputSchema,
        allowed_prompt_scopes: allowedPromptScopes,
      });
      message.success('任务契约已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function reload() {
    loading.value = true;
    try {
      const payload = await getPromptContracts({ page: 1, page_size: 100 });
      rows.value = payload.items || [];
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

  function taskKindLabel(value: string) {
    return ({ single_call: '单次调用', workflow_step: '工作流步骤', workflow: '工作流' } as Record<string, string>)[value] || value;
  }

  reload();
</script>

<style lang="less" scoped>
  .prompt-contract-page {
    min-width: 0;
  }

  .prompt-contract-page__keyword {
    width: min(360px, 100%);
  }

  .prompt-contract-page__select {
    width: 160px;
  }
</style>
