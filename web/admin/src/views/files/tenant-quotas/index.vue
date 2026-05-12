<template>
  <div class="tenant-quota-page">
    <ListPageRuntime :schema="quotaPage" :rows="rows" :loading="loading" @refresh="loadCurrentTenant">
      <template #filters>
        <n-input-number v-model:value="tenantId" :min="1" placeholder="租户 ID" class="tenant-quota-page__tenant" />
        <n-button type="primary" @click="loadCurrentTenant">读取配额</n-button>
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="620">
      <n-drawer-content title="配置租户文件配额">
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
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    getTenantFileQuota,
    saveTenantFileQuota,
    type StorageUsage,
    type TenantStorageQuota,
  } from '@/api/fileManagement';

  interface QuotaRow {
    tenant_id: number;
    quota: TenantStorageQuota | null;
    usage: StorageUsage;
  }

  const MB = 1024 * 1024;
  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const tenantId = ref<number | null>(1);
  const rows = ref<QuotaRow[]>([]);
  const quotaForm = reactive({
    quota_mb: 0,
    max_file_size_mb: 0,
    allowed_mime_types: [] as string[],
    blocked_extensions: [] as string[],
    enabled: true,
  });

  const columns: DataTableColumns<QuotaRow> = [
    { title: '租户 ID', key: 'tenant_id', width: 120 },
    {
      title: '状态',
      key: 'enabled',
      width: 110,
      render(row) {
        const enabled = row.quota?.enabled ?? true;
        return h(AppStatusTag, { tone: enabled ? 'success' : 'neutral', label: enabled ? '启用' : '停用' });
      },
    },
    { title: '已用容量', key: 'used_bytes', width: 140, render: (row) => formatBytes(row.usage.used_bytes) },
    { title: '文件数', key: 'file_count', width: 120, render: (row) => row.usage.file_count },
    { title: '总容量', key: 'quota_bytes', width: 140, render: (row) => formatBytes(row.quota?.quota_bytes || 0) },
    { title: '单文件上限', key: 'max_file_size_bytes', width: 150, render: (row) => formatBytes(row.quota?.max_file_size_bytes || 0) },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.quota?.update_time || '') },
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
      scrollX: 1100,
      tableProps: { size: 'small' },
    },
    toolbar: { rightTools: ['refresh'] },
    pagination: { pageSize: 20 },
  });

  function openEdit(row: QuotaRow) {
    quotaForm.quota_mb = bytesToMb(row.quota?.quota_bytes || 0);
    quotaForm.max_file_size_mb = bytesToMb(row.quota?.max_file_size_bytes || 0);
    quotaForm.allowed_mime_types = [...(row.quota?.allowed_mime_types || [])];
    quotaForm.blocked_extensions = [...(row.quota?.blocked_extensions || [])];
    quotaForm.enabled = row.quota?.enabled ?? true;
    drawerVisible.value = true;
  }

  async function submit() {
    const id = Number(tenantId.value || rows.value[0]?.tenant_id || 0);
    if (!id) {
      message.warning('请先输入租户 ID');
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
      await loadTenant(id);
    } finally {
      saving.value = false;
    }
  }

  async function loadCurrentTenant() {
    const id = Number(tenantId.value || 0);
    if (!id) {
      message.warning('请输入租户 ID');
      return;
    }
    await loadTenant(id);
  }

  async function loadTenant(id: number) {
    loading.value = true;
    try {
      const payload = await getTenantFileQuota(id);
      rows.value = [{ tenant_id: id, quota: payload.quota, usage: payload.usage }];
    } finally {
      loading.value = false;
    }
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

  loadCurrentTenant();
</script>

<style lang="less" scoped>
  .tenant-quota-page {
    min-width: 0;
  }

  .tenant-quota-page__tenant {
    width: 180px;
  }

  .tenant-quota-page__number {
    width: 100%;
  }
</style>
