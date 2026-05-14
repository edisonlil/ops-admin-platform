<template>
  <div class="prompt-binding-page">
    <ListPageRuntime :schema="pageSchema" :rows="filteredRows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-input v-model:value="contractFilter" clearable placeholder="过滤 Contract Key" class="prompt-binding-page__keyword" />
        <n-select v-model:value="environmentFilter" clearable placeholder="环境" :options="environmentOptions" class="prompt-binding-page__select" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="620">
      <n-drawer-content title="新增提示词绑定">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-form-item label="任务契约" path="contract_id">
            <n-select
              v-model:value="form.contract_id"
              :options="contractOptions"
              filterable
              placeholder="先选择 Contract Key"
              @update:value="loadCompatibleForSelectedContract"
            />
          </n-form-item>
          <n-form-item label="兼容提示词版本" path="prompt_version_id">
            <n-select
              v-model:value="form.prompt_version_id"
              :options="compatibleOptions"
              filterable
              placeholder="只展示兼容当前契约的版本"
              @update:value="syncPromptFromVersion"
            />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="绑定名称">
              <n-input v-model:value="form.binding_name" placeholder="默认绑定" />
            </n-form-item-gi>
            <n-form-item-gi label="优先级">
              <n-input-number v-model:value="form.priority" :min="1" />
            </n-form-item-gi>
            <n-form-item-gi label="环境">
              <n-select v-model:value="form.environment" :options="environmentOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="状态">
              <n-switch v-model:value="form.enabled">
                <template #checked>启用</template>
                <template #unchecked>停用</template>
              </n-switch>
            </n-form-item-gi>
          </n-grid>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存绑定</n-button>
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
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    createPromptBinding,
    disablePromptBinding,
    enablePromptBinding,
    getCompatiblePrompts,
    getPromptBindings,
    getPromptContracts,
    type CompatiblePrompt,
    type PromptBinding,
    type PromptTaskContract,
  } from '@/api/aiAssets';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const canManage = computed(() => hasPermission(['prompt:bindings:manage']));
  const loading = ref(false);
  const saving = ref(false);
  const rows = ref<PromptBinding[]>([]);
  const contracts = ref<PromptTaskContract[]>([]);
  const compatiblePrompts = ref<CompatiblePrompt[]>([]);
  const contractFilter = ref('');
  const environmentFilter = ref<string | null>(null);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);

  const form = reactive({
    contract_id: null as number | null,
    prompt_id: null as number | null,
    prompt_version_id: null as number | null,
    binding_name: '',
    priority: 100,
    environment: 'dev',
    enabled: true,
  });

  const rules: FormRules = {
    contract_id: [{ required: true, type: 'number', message: '请选择任务契约', trigger: ['blur', 'change'] }],
    prompt_version_id: [{ required: true, type: 'number', message: '请选择提示词版本', trigger: ['blur', 'change'] }],
  };
  const environmentOptions: SelectOption[] = [
    { label: 'dev', value: 'dev' },
    { label: 'test', value: 'test' },
    { label: 'prod', value: 'prod' },
  ];

  const filteredRows = computed(() => {
    const text = contractFilter.value.trim().toLowerCase();
    return rows.value.filter((row) => {
      const matchesContract = !text || row.contract_key.toLowerCase().includes(text);
      return matchesContract && (!environmentFilter.value || row.environment === environmentFilter.value);
    });
  });
  const contractOptions = computed<SelectOption[]>(() =>
    contracts.value.map((contract) => ({
      label: `${contract.display_name || contract.contract_key} · ${contract.contract_key}`,
      value: contract.id,
    }))
  );
  const compatibleOptions = computed<SelectOption[]>(() =>
    compatiblePrompts.value.map((item) => ({
      label: `${item.prompt.name} · ${item.prompt.prompt_key} · v${item.version.version}`,
      value: item.version.id,
    }))
  );

  const columns: DataTableColumns<PromptBinding> = [
    { title: 'Contract Key', key: 'contract_key', minWidth: 260, ellipsis: { tooltip: true } },
    { title: '提示词', key: 'prompt_name', minWidth: 180 },
    { title: 'Prompt Key', key: 'prompt_key', minWidth: 240, ellipsis: { tooltip: true } },
    { title: '版本', key: 'prompt_version', width: 100 },
    { title: '环境', key: 'environment', width: 90 },
    { title: '优先级', key: 'priority', width: 90 },
    { title: '状态', key: 'enabled', width: 100, render: (row) => h(AppStatusTag, { tone: row.enabled ? 'success' : 'neutral', label: row.enabled ? '启用' : '停用' }) },
    { title: '更新时间', key: 'update_time', width: 170, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            {
              label: row.enabled ? '停用' : '启用',
              show: canManage.value,
              tone: row.enabled ? 'danger' : 'primary',
              onClick: () => toggleBinding(row),
            },
          ],
        });
      },
    },
  ];

  const pageSchema = computed(() => defineListPage<PromptBinding>({
    id: 'prompts.bindings',
    title: '提示词绑定',
    description: '将任务契约绑定到兼容的提示词版本，执行时记录具体版本证据。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1260,
      tableProps: { size: 'small', pagination: false },
    },
    toolbar: {
      primaryAction: canManage.value
        ? { key: 'create', label: '新增绑定', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  }));

  function resetForm() {
    Object.assign(form, {
      contract_id: null,
      prompt_id: null,
      prompt_version_id: null,
      binding_name: '',
      priority: 100,
      environment: 'dev',
      enabled: true,
    });
    compatiblePrompts.value = [];
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  async function loadCompatibleForSelectedContract() {
    form.prompt_id = null;
    form.prompt_version_id = null;
    const contract = contracts.value.find((item) => item.id === form.contract_id);
    if (!contract) {
      compatiblePrompts.value = [];
      return;
    }
    const payload = await getCompatiblePrompts(contract.contract_key);
    compatiblePrompts.value = payload.items || [];
  }

  function syncPromptFromVersion() {
    const item = compatiblePrompts.value.find((entry) => entry.version.id === form.prompt_version_id);
    form.prompt_id = item?.prompt.id || null;
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    if (!form.contract_id || !form.prompt_id || !form.prompt_version_id) {
      message.warning('请选择完整的契约和提示词版本');
      return;
    }
    saving.value = true;
    try {
      await createPromptBinding({
        contract_id: form.contract_id,
        prompt_id: form.prompt_id,
        prompt_version_id: form.prompt_version_id,
        binding_name: form.binding_name,
        priority: form.priority,
        environment: form.environment,
        enabled: form.enabled,
      });
      message.success('提示词绑定已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function toggleBinding(row: PromptBinding) {
    if (row.enabled) {
      await disablePromptBinding(row.id);
      message.success('绑定已停用');
    } else {
      await enablePromptBinding(row.id);
      message.success('绑定已启用');
    }
    await reload();
  }

  async function reload() {
    loading.value = true;
    try {
      const [bindingPayload, contractPayload] = await Promise.all([
        getPromptBindings({ page: 1, page_size: 100 }),
        getPromptContracts({ page: 1, page_size: 100 }),
      ]);
      rows.value = bindingPayload.items || [];
      contracts.value = contractPayload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .prompt-binding-page {
    min-width: 0;
  }

  .prompt-binding-page__keyword {
    width: min(340px, 100%);
  }

  .prompt-binding-page__select {
    width: 140px;
  }
</style>
