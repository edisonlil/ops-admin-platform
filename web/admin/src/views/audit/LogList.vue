<template>
  <ListPageRuntime :schema="pageSchema" :rows="rows" :loading="loading" @refresh="reload">
    <template #filters>
      <n-select
        v-if="isPlatformAdmin"
        v-model:value="selectedTenantId"
        clearable
        filterable
        placeholder="全部租户"
        :loading="tenantLoading"
        :options="tenantOptions"
        class="audit-log-page__tenant"
        @update:value="reload"
      />
      <n-input v-model:value="keyword" clearable placeholder="搜索动作、请求 ID、操作人" class="audit-log-page__search" @keyup.enter="reload" />
      <n-select v-model:value="outcome" clearable placeholder="执行结果" :options="outcomeOptions" class="audit-log-page__select" />
      <n-select v-model:value="severity" clearable placeholder="日志级别" :options="severityOptions" class="audit-log-page__select" />
      <n-button type="primary" @click="reload">查询</n-button>
    </template>
  </ListPageRuntime>
</template>

<script lang="ts" setup>
  import { computed, h, ref } from 'vue';
  import type { DataTableColumns, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { getTenants } from '@/api/business';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { useUserStore } from '@/store/modules/user';
  import { getAuditLogs, type AuditLogCategory, type AuditLogRow } from '@/api/auditLogging';

  const props = defineProps<{
    category: AuditLogCategory;
    title: string;
    description: string;
  }>();

  const loading = ref(false);
  const tenantLoading = ref(false);
  const rows = ref<AuditLogRow[]>([]);
  const userStore = useUserStore();
  const selectedTenantId = ref<number | null>(null);
  const tenantOptions = ref<SelectOption[]>([]);
  const keyword = ref('');
  const outcome = ref<string | null>(null);
  const severity = ref<string | null>(null);

  const outcomeOptions = [
    { label: '成功', value: 'success' },
    { label: '失败', value: 'failed' },
  ];
  const severityOptions = [
    { label: '信息', value: 'info' },
    { label: '警告', value: 'warning' },
    { label: '错误', value: 'error' },
  ];
  const outcomeLabel: Record<string, string> = {
    success: '成功',
    failed: '失败',
  };
  const severityLabel: Record<string, string> = {
    info: '信息',
    warning: '警告',
    error: '错误',
  };

  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);

  const baseColumns: DataTableColumns<AuditLogRow> = [
    { title: '时间', key: 'event_time', width: 180, render: (row) => formatToDateTime(row.event_time) },
    {
      title: '结果',
      key: 'event_outcome',
      width: 110,
      render(row) {
        return h(AppStatusTag, {
          tone: row.event_outcome === 'success' ? 'success' : 'error',
          label: outcomeLabel[row.event_outcome] || row.event_outcome || '-',
        });
      },
    },
    {
      title: '级别',
      key: 'severity',
      width: 110,
      render(row) {
        const tone = row.severity === 'error' ? 'error' : row.severity === 'warning' ? 'warning' : 'info';
        return h(AppStatusTag, { tone, label: severityLabel[row.severity] || row.severity || '-' });
      },
    },
    { title: '动作', key: 'event_action', minWidth: 220, ellipsis: { tooltip: true } },
    { title: '操作人', key: 'actor_name', width: 140, ellipsis: { tooltip: true } },
    { title: '请求 ID', key: 'request_id', minWidth: 220, ellipsis: { tooltip: true } },
    { title: '摘要', key: 'summary', minWidth: 260, ellipsis: { tooltip: true } },
  ];

  const apiColumns: DataTableColumns<AuditLogRow> = [
    { title: '方法', key: 'request_method', width: 90 },
    { title: '路径', key: 'request_path', minWidth: 260, ellipsis: { tooltip: true } },
    { title: '状态码', key: 'status_code', width: 90 },
    { title: '耗时', key: 'duration_ms', width: 110, render: (row) => `${row.duration_ms || 0} ms` },
  ];

  const sqlColumns: DataTableColumns<AuditLogRow> = [
    { title: '数据库', key: 'database_backend', width: 110 },
    { title: '耗时', key: 'duration_ms', width: 110, render: (row) => `${row.duration_ms || 0} ms` },
    { title: 'SQL 模板', key: 'sql_template', minWidth: 420, ellipsis: { tooltip: true } },
    { title: '错误信息', key: 'error_message', minWidth: 220, ellipsis: { tooltip: true } },
  ];

  const operationColumns: DataTableColumns<AuditLogRow> = [
    { title: '资源类型', key: 'resource_type', width: 150, ellipsis: { tooltip: true } },
    { title: '资源 ID', key: 'resource_id', width: 130, ellipsis: { tooltip: true } },
    { title: '风险级别', key: 'risk_level', width: 110 },
  ];

  const columns = computed<DataTableColumns<AuditLogRow>>(() => {
    if (props.category === 'api') return [...baseColumns.slice(0, 3), ...apiColumns, ...baseColumns.slice(3)];
    if (props.category === 'sql') return [...baseColumns.slice(0, 3), ...sqlColumns, ...baseColumns.slice(3)];
    if (props.category === 'operation') return [...baseColumns.slice(0, 3), ...operationColumns, ...baseColumns.slice(3)];
    return baseColumns;
  });

  const pageSchema = computed(() =>
    defineListPage<AuditLogRow>({
      id: `audit.${props.category}`,
      title: props.title,
      description: props.description,
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'table',
        columns: columns.value,
        rowKey: (row) => row.id,
        scrollX: props.category === 'sql' ? 1580 : 1420,
        tableProps: { size: 'small' },
      },
      toolbar: { rightTools: ['refresh'] },
      pagination: { pageSize: 20 },
    })
  );

  async function reload() {
    loading.value = true;
    try {
      await ensureTenantOptions();
      const payload = await getAuditLogs(props.category, {
        page: 1,
        page_size: 50,
        tenant_id: selectedTenantForRequest(),
        keyword: keyword.value || undefined,
        outcome: outcome.value || undefined,
        severity: severity.value || undefined,
      });
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  async function ensureTenantOptions() {
    if (!isPlatformAdmin.value || tenantOptions.value.length) return;
    tenantLoading.value = true;
    try {
      const payload = await getTenants();
      tenantOptions.value = (payload.items || []).map((tenant) => ({
        label: `${tenant.name || tenant.tenant_key} (${tenant.tenant_key})`,
        value: Number(tenant.id),
      }));
    } finally {
      tenantLoading.value = false;
    }
  }

  function selectedTenantForRequest() {
    return isPlatformAdmin.value ? selectedTenantId.value || undefined : undefined;
  }

  reload();
</script>

<style lang="less" scoped>
  .audit-log-page__search {
    width: 280px;
  }

  .audit-log-page__tenant {
    width: min(280px, 100%);
  }

  .audit-log-page__select {
    width: 150px;
  }
</style>
