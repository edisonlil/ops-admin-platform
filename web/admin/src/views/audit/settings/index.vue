<template>
  <div class="audit-settings-page">
    <ListPageRuntime :schema="settingsPage" :rows="rows" :loading="loading" @refresh="reload">
      <template #item-actions="{ row }">
        <n-button size="small" type="primary" @click="openEdit(row)">Edit</n-button>
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="620">
      <n-drawer-content :title="activeRow ? `Audit Settings: tenant ${activeRow.tenant_id}` : 'Audit Settings'">
        <n-form label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="Slow SQL threshold (ms)">
              <n-input-number v-model:value="form.slow_sql_threshold_ms" :min="50" :max="60000" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="Flush interval (ms)">
              <n-input-number v-model:value="form.flush_interval_ms" :min="100" :max="60000" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="Queue max size">
              <n-input-number v-model:value="form.queue_max_size" :min="1000" :max="1000000" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="Batch size">
              <n-input-number v-model:value="form.batch_size" :min="1" :max="10000" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="Plain IP retention days">
              <n-input-number v-model:value="form.plaintext_ip_retention_days" :min="0" :max="3650" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="Log retention days">
              <n-input-number v-model:value="form.log_retention_days" :min="1" :max="3650" class="audit-settings-page__number" />
            </n-form-item-gi>
          </n-grid>

          <n-space vertical>
            <n-checkbox v-model:checked="form.api_log_enabled">API logs</n-checkbox>
            <n-checkbox v-model:checked="form.operation_log_enabled">Operation logs</n-checkbox>
            <n-checkbox v-model:checked="form.sql_log_enabled">SQL logs</n-checkbox>
            <n-checkbox v-model:checked="form.visitor_log_enabled">Visitor logs</n-checkbox>
            <n-checkbox v-model:checked="form.system_log_enabled">System logs</n-checkbox>
          </n-space>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">Cancel</n-button>
            <n-button type="primary" :loading="saving" @click="submit">Save</n-button>
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
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    getAuditLoggingSettings,
    saveAuditLoggingSettings,
    type AuditLoggingSettings,
    type AuditLoggingSettingsPayload,
  } from '@/api/auditLogging';

  const message = useMessage();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const activeRow = ref<AuditLoggingSettings | null>(null);
  const rows = ref<AuditLoggingSettings[]>([]);
  const form = reactive<AuditLoggingSettingsPayload>({
    api_log_enabled: true,
    operation_log_enabled: true,
    sql_log_enabled: true,
    visitor_log_enabled: true,
    system_log_enabled: true,
    slow_sql_threshold_ms: 500,
    queue_max_size: 10000,
    batch_size: 100,
    flush_interval_ms: 1000,
    plaintext_ip_retention_days: 30,
    log_retention_days: 180,
    include_request_headers: false,
    include_response_body: false,
    external_sink_enabled: false,
    external_sink_type: '',
    config: {},
  });

  const columns: DataTableColumns<AuditLoggingSettings> = [
    { title: 'Tenant', key: 'tenant_id', width: 100 },
    {
      title: 'API',
      key: 'api_log_enabled',
      width: 90,
      render(row) {
        return h(AppStatusTag, { tone: row.api_log_enabled ? 'success' : 'neutral', label: row.api_log_enabled ? 'On' : 'Off' });
      },
    },
    { title: 'Slow SQL', key: 'slow_sql_threshold_ms', width: 120, render: (row) => `${row.slow_sql_threshold_ms} ms` },
    { title: 'Batch', key: 'batch_size', width: 100 },
    { title: 'Flush', key: 'flush_interval_ms', width: 100, render: (row) => `${row.flush_interval_ms} ms` },
    { title: 'Plain IP', key: 'plaintext_ip_retention_days', width: 120, render: (row) => `${row.plaintext_ip_retention_days} days` },
    { title: 'Retention', key: 'log_retention_days', width: 120, render: (row) => `${row.log_retention_days} days` },
    { title: 'Updated', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [{ label: 'Edit', onClick: () => openEdit(row) }],
        });
      },
    },
  ];

  const settingsPage = defineListPage<AuditLoggingSettings>({
    id: 'audit.settings',
    title: 'Audit Settings',
    description: 'Platform-managed logging collection, queue, SQL threshold, and retention settings.',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1060,
      tableProps: { size: 'small' },
    },
    toolbar: { rightTools: ['refresh'] },
    pagination: { pageSize: 20 },
  });

  function openEdit(row: AuditLoggingSettings) {
    activeRow.value = row;
    Object.assign(form, {
      api_log_enabled: row.api_log_enabled,
      operation_log_enabled: row.operation_log_enabled,
      sql_log_enabled: row.sql_log_enabled,
      visitor_log_enabled: row.visitor_log_enabled,
      system_log_enabled: row.system_log_enabled,
      slow_sql_threshold_ms: row.slow_sql_threshold_ms,
      queue_max_size: row.queue_max_size,
      batch_size: row.batch_size,
      flush_interval_ms: row.flush_interval_ms,
      plaintext_ip_retention_days: row.plaintext_ip_retention_days,
      log_retention_days: row.log_retention_days,
      include_request_headers: row.include_request_headers,
      include_response_body: row.include_response_body,
      external_sink_enabled: row.external_sink_enabled,
      external_sink_type: row.external_sink_type,
      config: row.config || {},
    });
    drawerVisible.value = true;
  }

  async function submit() {
    const tenantId = Number(activeRow.value?.tenant_id ?? 0);
    saving.value = true;
    try {
      await saveAuditLoggingSettings(tenantId, { ...form });
      message.success('Audit settings saved');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function reload() {
    loading.value = true;
    try {
      const payload = await getAuditLoggingSettings();
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .audit-settings-page {
    min-width: 0;
  }

  .audit-settings-page__number {
    width: 100%;
  }
</style>
