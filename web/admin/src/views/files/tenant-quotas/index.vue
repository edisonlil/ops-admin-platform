<template>
  <div class="tenant-quota-page">
    <ListPageRuntime :schema="quotaPage" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload" @filter-reset="resetFilters">
      <template #filters="{ submit }">
        <n-input
          v-model:value="query"
          clearable
          placeholder="搜索租户 Key / 名称"
          @keyup.enter="submit"
        />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="620">
      <n-drawer-content :title="activeRow ? `配置 ${activeRow.tenant_name} 文件配额` : '配置租户文件配额'">
        <n-form label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="总容量（MB）">
              <n-input-number v-model:value="quotaForm.quota_mb" :min="0" class="tenant-quota-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="单文件上限（MB）">
              <n-input-number v-model:value="quotaForm.max_file_size_mb" :min="0" class="tenant-quota-page__number" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="允许 MIME 类型">
            <n-dynamic-tags v-model:value="quotaForm.allowed_mime_types" />
          </n-form-item>
          <n-form-item label="禁止扩展名">
            <n-dynamic-tags v-model:value="quotaForm.blocked_extensions" />
          </n-form-item>
          <n-checkbox v-model:checked="quotaForm.enabled">启用租户文件存储</n-checkbox>
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
  import { formatToDateTime } from '@/utils/dateUtil';
  import { getTenants } from '@/api/business';
  import {
    getTenantFileQuota,
    saveTenantFileQuota,
    type StorageUsage,
    type TenantStorageQuota,
  } from '@/api/fileManagement';

  interface TenantRow {
    id: number;
    tenant_key: string;
    name: string;
    status: string;
    update_time?: string;
  }

  interface QuotaRow {
    tenant_id: number;
    tenant_key: string;
    tenant_name: string;
    tenant_status: string;
    quota: TenantStorageQuota | null;
    usage: StorageUsage;
  }

  const MB = 1024 * 1024;
  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const query = ref('');
  const activeRow = ref<QuotaRow | null>(null);
  const rows = ref<QuotaRow[]>([]);
  const paginationTotal = ref(0);
  const quotaForm = reactive({
    quota_mb: 0,
    max_file_size_mb: 0,
    allowed_mime_types: [] as string[],
    blocked_extensions: [] as string[],
    enabled: true,
  });

  const columns: DataTableColumns<QuotaRow> = [
    { title: '租户名称', key: 'tenant_name', minWidth: 180 },
    { title: '租户 Key', key: 'tenant_key', minWidth: 160 },
    { title: '租户 ID', key: 'tenant_id', width: 100 },
    {
      title: '租户状态',
      key: 'tenant_status',
      width: 110,
      render(row) {
        const active = row.tenant_status === 'active';
        return h(AppStatusTag, { tone: active ? 'success' : 'warning', label: active ? '启用' : '停用' });
      },
    },
    {
      title: '文件存储',
      key: 'enabled',
      width: 110,
      render(row) {
        const enabled = row.quota?.enabled ?? true;
        const label = row.quota ? (enabled ? '启用' : '停用') : '默认启用';
        return h(AppStatusTag, { tone: enabled ? 'success' : 'neutral', label });
      },
    },
    { title: '已用容量', key: 'used_bytes', width: 140, render: (row) => formatBytes(row.usage.used_bytes) },
    { title: '文件数', key: 'file_count', width: 120, render: (row) => row.usage.file_count },
    { title: '总容量', key: 'quota_bytes', width: 140, render: (row) => formatBytes(row.quota?.quota_bytes || 0) },
    { title: '单文件上限', key: 'max_file_size_bytes', width: 150, render: (row) => formatBytes(row.quota?.max_file_size_bytes || 0) },
    {
      title: '配额更新时间',
      key: 'update_time',
      width: 180,
      render: (row) => (row.quota?.update_time ? formatToDateTime(row.quota.update_time) : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '配置', show: hasPermission(['file:quota:manage']), onClick: () => openEdit(row) },
          ],
        });
      },
    },
  ];

  const quotaPage = defineListPage<QuotaRow>({
    id: 'files.tenant-quotas',
    title: '租户文件配额',
    description: '平台管理员按租户配置文件总容量、单文件大小和文件类型约束。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.tenant_id,
      scrollX: 1360,
      sort: { remote: true },
      columnRuntime: {
        columns: [
          { key: 'tenant_name', sortable: true, sortField: 'name' },
          { key: 'tenant_key', sortable: true },
          { key: 'tenant_id', sortable: true, sortField: 'id' },
          { key: 'tenant_status', sortable: true, sortField: 'status' },
          { key: 'enabled', sortable: false },
          { key: 'used_bytes', sortable: false },
          { key: 'file_count', sortable: false },
          { key: 'quota_bytes', sortable: false },
          { key: 'max_file_size_bytes', sortable: false },
          { key: 'update_time', sortable: false },
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
    quotaForm.quota_mb = bytesToMb(row.quota?.quota_bytes || 0);
    quotaForm.max_file_size_mb = bytesToMb(row.quota?.max_file_size_bytes || 0);
    quotaForm.allowed_mime_types = [...(row.quota?.allowed_mime_types || [])];
    quotaForm.blocked_extensions = [...(row.quota?.blocked_extensions || [])];
    quotaForm.enabled = row.quota?.enabled ?? true;
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
      await saveTenantFileQuota(id, {
        quota_bytes: mbToBytes(quotaForm.quota_mb),
        max_file_size_bytes: mbToBytes(quotaForm.max_file_size_mb),
        allowed_mime_types: quotaForm.allowed_mime_types,
        blocked_extensions: quotaForm.blocked_extensions,
        enabled: quotaForm.enabled,
      });
      message.success('租户文件配额已保存');
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
    const payload = await getTenantFileQuota(tenant.id);
    return {
      tenant_id: tenant.id,
      tenant_key: tenant.tenant_key,
      tenant_name: tenant.name,
      tenant_status: tenant.status,
      quota: payload.quota,
      usage: payload.usage,
    };
  }

  function normalizeTenant(tenant: TenantRow): TenantRow {
    return {
      id: Number(tenant.id),
      tenant_key: String(tenant.tenant_key || ''),
      name: String(tenant.name || ''),
      status: String(tenant.status || 'active'),
      update_time: tenant.update_time,
    };
  }

  function mbToBytes(value: number | null) {
    return Math.max(0, Number(value || 0)) * MB;
  }

  function bytesToMb(value: number) {
    return Math.round(Number(value || 0) / MB);
  }

  function formatBytes(value: number) {
    if (!value) return '不限';
    if (value < 1024) return `${value} B`;
    if (value < MB) return `${(value / 1024).toFixed(1)} KB`;
    if (value < 1024 * MB) return `${(value / MB).toFixed(1)} MB`;
    return `${(value / 1024 / MB).toFixed(1)} GB`;
  }

  reload();
</script>

<style lang="less" scoped>
  .tenant-quota-page {
    min-width: 0;
  }

  .tenant-quota-page__number {
    width: 100%;
  }
</style>
