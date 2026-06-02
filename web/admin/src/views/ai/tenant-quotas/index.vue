<template>
  <div class="ai-quota-page">
    <ListPageRuntime :schema="quotaPage" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload" @filter-reset="resetFilters">
      <template #filters="{ submit }">
        <n-input v-model:value="query" clearable placeholder="搜索租户 Key / 名称" @keyup.enter="submit" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="560">
      <n-drawer-content :title="activeRow ? `配置 ${activeRow.tenant_name} AI 应用配额` : '配置 AI 应用配额'">
        <n-form label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="应用数量上限">
              <n-input-number v-model:value="quotaForm.max_applications" :min="0" class="ai-quota-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="日运行上限">
              <n-input-number v-model:value="quotaForm.daily_run_limit" :min="0" class="ai-quota-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="能力数量上限">
              <n-input-number v-model:value="quotaForm.max_capabilities" :min="0" class="ai-quota-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="资产数量上限">
              <n-input-number v-model:value="quotaForm.max_assets" :min="0" class="ai-quota-page__number" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="月 Token 上限">
            <n-input-number v-model:value="quotaForm.monthly_token_limit" :min="0" class="ai-quota-page__number" />
          </n-form-item>
          <n-checkbox v-model:checked="quotaForm.enabled">启用租户 AI Studio</n-checkbox>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存配额</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { getTenants } from '@/api/business';
  import { getAdminTenantAiQuota, saveAdminTenantAiQuota, type AiQuota } from '@/api/aiStudio';

  interface TenantRow {
    id: number;
    tenant_key: string;
    name: string;
    status: string;
  }

  interface QuotaRow {
    tenant_id: number;
    tenant_key: string;
    tenant_name: string;
    tenant_status: string;
    quota: AiQuota;
  }

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const query = ref('');
  const rows = ref<QuotaRow[]>([]);
  const paginationTotal = ref(0);
  const activeRow = ref<QuotaRow | null>(null);
  const quotaForm = reactive({
    max_applications: 5,
    max_capabilities: 50,
    max_assets: 200,
    daily_run_limit: 1000,
    monthly_token_limit: 1000000,
    enabled: true,
  });

  const columns: DataTableColumns<QuotaRow> = [
    { title: '租户名称', key: 'tenant_name', minWidth: 180 },
    { title: '租户 Key', key: 'tenant_key', minWidth: 160 },
    { title: '租户 ID', key: 'tenant_id', width: 100 },
    {
      title: 'AI Studio',
      key: 'enabled',
      width: 120,
      render(row) {
        return h(AppStatusTag, {
          tone: row.quota.enabled ? 'success' : 'neutral',
          label: row.quota.enabled ? '启用' : '停用',
        });
      },
    },
    {
      title: '应用数量',
      key: 'applications',
      width: 150,
      render(row) {
        return `${row.quota.usage?.applications || 0} / ${row.quota.max_applications}`;
      },
    },
    { title: '能力上限', key: 'max_capabilities', width: 120, render: (row) => row.quota.max_capabilities },
    { title: '资产上限', key: 'max_assets', width: 120, render: (row) => row.quota.max_assets },
    { title: '日运行上限', key: 'daily_run_limit', width: 130, render: (row) => row.quota.daily_run_limit },
    { title: '月 Token 上限', key: 'monthly_token_limit', width: 150, render: (row) => row.quota.monthly_token_limit },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [{ label: '配置', show: hasPermission(['ai_studio:quota:manage']), onClick: () => openEdit(row) }],
        });
      },
    },
  ];

  const quotaPage = defineListPage<QuotaRow>({
    id: 'ai.tenant-quotas',
    title: 'AI 应用配额',
    description: '平台管理员按租户配置 AI Studio 应用数量、运行和资产上限。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.tenant_id,
      scrollX: 1320,
      sort: { remote: true },
      columnRuntime: {
        columns: [
          { key: 'tenant_name', sortable: true, sortField: 'name' },
          { key: 'tenant_key', sortable: true },
          { key: 'tenant_id', sortable: true, sortField: 'id' },
          { key: 'enabled', sortable: false },
          { key: 'applications', sortable: false },
          { key: 'max_capabilities', sortable: false },
          { key: 'max_assets', sortable: false },
          { key: 'daily_run_limit', sortable: false },
          { key: 'monthly_token_limit', sortable: false },
          { key: 'actions', required: true, sortable: false },
        ],
      },
      tableProps: { size: 'small' },
    },
    toolbar: { rightTools: ['refresh'] },
    filterBar: { showSubmit: true, showReset: true },
    pagination: { pageSize: 20 },
  });

  function openEdit(row: QuotaRow) {
    activeRow.value = row;
    quotaForm.max_applications = row.quota.max_applications;
    quotaForm.max_capabilities = row.quota.max_capabilities;
    quotaForm.max_assets = row.quota.max_assets;
    quotaForm.daily_run_limit = row.quota.daily_run_limit;
    quotaForm.monthly_token_limit = row.quota.monthly_token_limit;
    quotaForm.enabled = row.quota.enabled;
    drawerVisible.value = true;
  }

  async function submit() {
    const id = Number(activeRow.value?.tenant_id || 0);
    if (!id) {
      message.warning('请先选择租户');
      return;
    }
    saving.value = true;
    try {
      await saveAdminTenantAiQuota(id, { ...quotaForm });
      message.success('租户 AI 应用配额已保存');
      drawerVisible.value = false;
      await refreshTenantQuota(id);
    } finally {
      saving.value = false;
    }
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await getTenants({ q: query.value || undefined, ...runtimeListParams(state) });
      const tenants = ((payload as { items?: TenantRow[] }).items || []).map(normalizeTenant);
      rows.value = await Promise.all(tenants.map(loadTenantQuotaRow));
      paginationTotal.value = payload.pagination?.total || rows.value.length;
    } finally {
      loading.value = false;
    }
  }

  function resetFilters() {
    query.value = '';
  }

  async function refreshTenantQuota(tenantId: number) {
    const current = rows.value.find((row) => row.tenant_id === tenantId);
    if (!current) {
      await reload();
      return;
    }
    const updated = await loadTenantQuotaRow({
      id: current.tenant_id,
      tenant_key: current.tenant_key,
      name: current.tenant_name,
      status: current.tenant_status,
    });
    rows.value = rows.value.map((row) => (row.tenant_id === tenantId ? updated : row));
    activeRow.value = updated;
  }

  async function loadTenantQuotaRow(tenant: TenantRow): Promise<QuotaRow> {
    const quota = await getAdminTenantAiQuota(tenant.id);
    return {
      tenant_id: tenant.id,
      tenant_key: tenant.tenant_key,
      tenant_name: tenant.name,
      tenant_status: tenant.status,
      quota,
    };
  }

  function normalizeTenant(tenant: TenantRow): TenantRow {
    return {
      id: Number(tenant.id),
      tenant_key: String(tenant.tenant_key || ''),
      name: String(tenant.name || ''),
      status: String(tenant.status || 'active'),
    };
  }

  reload();
</script>

<style lang="less" scoped>
  .ai-quota-page {
    min-width: 0;
  }

  .ai-quota-page__number {
    width: 100%;
  }
</style>
