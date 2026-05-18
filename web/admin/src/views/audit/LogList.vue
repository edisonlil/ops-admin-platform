<template>
  <ListPageRuntime :schema="pageSchema" :rows="rows" :loading="loading" @refresh="reload">
    <template #filters>
      <n-input v-model:value="keyword" clearable placeholder="Search action, request ID, actor" class="audit-log-page__search" @keyup.enter="reload" />
      <n-select v-model:value="outcome" clearable placeholder="Outcome" :options="outcomeOptions" class="audit-log-page__select" />
      <n-select v-model:value="severity" clearable placeholder="Severity" :options="severityOptions" class="audit-log-page__select" />
      <n-button type="primary" @click="reload">Search</n-button>
    </template>
  </ListPageRuntime>
</template>

<script lang="ts" setup>
  import { computed, h, ref } from 'vue';
  import type { DataTableColumns } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { getAuditLogs, type AuditLogCategory, type AuditLogRow } from '@/api/auditLogging';

  const props = defineProps<{
    category: AuditLogCategory;
    title: string;
    description: string;
  }>();

  const loading = ref(false);
  const rows = ref<AuditLogRow[]>([]);
  const keyword = ref('');
  const outcome = ref<string | null>(null);
  const severity = ref<string | null>(null);

  const outcomeOptions = [
    { label: 'Success', value: 'success' },
    { label: 'Failed', value: 'failed' },
  ];
  const severityOptions = [
    { label: 'Info', value: 'info' },
    { label: 'Warning', value: 'warning' },
    { label: 'Error', value: 'error' },
  ];

  const baseColumns: DataTableColumns<AuditLogRow> = [
    { title: 'Time', key: 'event_time', width: 180, render: (row) => formatToDateTime(row.event_time) },
    {
      title: 'Outcome',
      key: 'event_outcome',
      width: 110,
      render(row) {
        return h(AppStatusTag, {
          tone: row.event_outcome === 'success' ? 'success' : 'error',
          label: row.event_outcome || '-',
        });
      },
    },
    {
      title: 'Severity',
      key: 'severity',
      width: 110,
      render(row) {
        const tone = row.severity === 'error' ? 'error' : row.severity === 'warning' ? 'warning' : 'info';
        return h(AppStatusTag, { tone, label: row.severity || '-' });
      },
    },
    { title: 'Action', key: 'event_action', minWidth: 220, ellipsis: { tooltip: true } },
    { title: 'Actor', key: 'actor_name', width: 140, ellipsis: { tooltip: true } },
    { title: 'Request ID', key: 'request_id', minWidth: 220, ellipsis: { tooltip: true } },
    { title: 'Summary', key: 'summary', minWidth: 260, ellipsis: { tooltip: true } },
  ];

  const apiColumns: DataTableColumns<AuditLogRow> = [
    { title: 'Method', key: 'request_method', width: 90 },
    { title: 'Path', key: 'request_path', minWidth: 260, ellipsis: { tooltip: true } },
    { title: 'Status', key: 'status_code', width: 90 },
    { title: 'Duration', key: 'duration_ms', width: 110, render: (row) => `${row.duration_ms || 0} ms` },
  ];

  const sqlColumns: DataTableColumns<AuditLogRow> = [
    { title: 'Backend', key: 'database_backend', width: 110 },
    { title: 'Duration', key: 'duration_ms', width: 110, render: (row) => `${row.duration_ms || 0} ms` },
    { title: 'SQL Template', key: 'sql_template', minWidth: 420, ellipsis: { tooltip: true } },
    { title: 'Error', key: 'error_message', minWidth: 220, ellipsis: { tooltip: true } },
  ];

  const operationColumns: DataTableColumns<AuditLogRow> = [
    { title: 'Resource', key: 'resource_type', width: 150, ellipsis: { tooltip: true } },
    { title: 'Resource ID', key: 'resource_id', width: 130, ellipsis: { tooltip: true } },
    { title: 'Risk', key: 'risk_level', width: 110 },
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
      const payload = await getAuditLogs(props.category, {
        page: 1,
        page_size: 50,
        keyword: keyword.value || undefined,
        outcome: outcome.value || undefined,
        severity: severity.value || undefined,
      });
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .audit-log-page__search {
    width: 280px;
  }

  .audit-log-page__select {
    width: 150px;
  }
</style>
