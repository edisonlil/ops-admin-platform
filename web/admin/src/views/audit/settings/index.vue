<template>
  <div class="audit-settings-page">
    <n-alert v-if="loadError" type="error" class="audit-settings-page__error" closable @close="loadError = ''">
      {{ loadError }}
    </n-alert>
    <ListPageRuntime :schema="settingsPage" :rows="rows" :loading="loading" @refresh="reload">
      <template #item-actions="{ row }">
        <n-button size="small" type="primary" @click="openEdit(row)">编辑</n-button>
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="620">
      <n-drawer-content :title="activeRow ? `日志配置：租户 ${activeRow.tenant_id}` : '日志配置'">
        <n-form label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="慢 SQL 阈值（毫秒）">
              <n-input-number v-model:value="form.slow_sql_threshold_ms" :min="50" :max="60000" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="刷新间隔（毫秒）">
              <n-input-number v-model:value="form.flush_interval_ms" :min="100" :max="60000" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="队列最大长度">
              <n-input-number v-model:value="form.queue_max_size" :min="1000" :max="1000000" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="批量入库条数">
              <n-input-number v-model:value="form.batch_size" :min="1" :max="10000" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="明文 IP 保留天数">
              <n-input-number v-model:value="form.plaintext_ip_retention_days" :min="0" :max="3650" class="audit-settings-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="日志保留天数">
              <n-input-number v-model:value="form.log_retention_days" :min="1" :max="3650" class="audit-settings-page__number" />
            </n-form-item-gi>
          </n-grid>

          <n-space vertical>
            <n-checkbox v-model:checked="form.api_log_enabled">接口日志</n-checkbox>
            <n-checkbox v-model:checked="form.operation_log_enabled">操作日志</n-checkbox>
            <n-checkbox v-model:checked="form.sql_log_enabled">SQL 日志</n-checkbox>
            <n-checkbox v-model:checked="form.visitor_log_enabled">访客日志</n-checkbox>
            <n-checkbox v-model:checked="form.system_log_enabled">系统日志</n-checkbox>
          </n-space>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存</n-button>
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
  const loadError = ref('');
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
    { title: '租户', key: 'tenant_id', width: 100 },
    {
      title: '接口',
      key: 'api_log_enabled',
      width: 90,
      render(row) {
        return h(AppStatusTag, { tone: row.api_log_enabled ? 'success' : 'neutral', label: row.api_log_enabled ? '开启' : '关闭' });
      },
    },
    { title: '慢 SQL', key: 'slow_sql_threshold_ms', width: 120, render: (row) => `${row.slow_sql_threshold_ms} ms` },
    { title: '批量条数', key: 'batch_size', width: 100 },
    { title: '刷新间隔', key: 'flush_interval_ms', width: 110, render: (row) => `${row.flush_interval_ms} ms` },
    { title: '明文 IP', key: 'plaintext_ip_retention_days', width: 120, render: (row) => `${row.plaintext_ip_retention_days} 天` },
    { title: '保留期', key: 'log_retention_days', width: 120, render: (row) => `${row.log_retention_days} 天` },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [{ label: '编辑', onClick: () => openEdit(row) }],
        });
      },
    },
  ];

  const settingsPage = defineListPage<AuditLoggingSettings>({
    id: 'audit.settings',
    title: '日志配置',
    description: '由平台统一管理日志采集、队列、SQL 阈值和保留策略。',
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
      message.success('日志配置已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function reload() {
    loading.value = true;
    loadError.value = '';
    try {
      const payload = await getAuditLoggingSettings();
      rows.value = payload.items || [];
    } catch (error) {
      rows.value = [];
      loadError.value = error instanceof Error ? error.message : '日志配置加载失败，请稍后重试';
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .audit-settings-page {
    display: grid;
    gap: 12px;
    min-width: 0;
  }

  .audit-settings-page__error {
    min-width: 0;
  }

  .audit-settings-page__number {
    width: 100%;
  }
</style>
