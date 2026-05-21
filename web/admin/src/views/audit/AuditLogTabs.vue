<template>
  <ListPageRuntime :schema="pageSchema" :rows="[]" :loading="loading" @refresh="reloadVisible">
    <template #filters>
      <n-select
        v-if="isPlatformAdmin"
        v-model:value="selectedTenantId"
        clearable
        filterable
        placeholder="选择租户"
        :loading="tenantLoading"
        :options="tenantOptions"
        class="audit-log-tabs__tenant"
        @update:value="reloadVisible"
      />
      <n-input v-model:value="keyword" clearable placeholder="搜索动作、请求 ID、操作人" class="audit-log-tabs__search" @keyup.enter="reloadVisible" />
      <n-select v-model:value="outcome" clearable placeholder="执行结果" :options="outcomeOptions" class="audit-log-tabs__select" />
      <n-select v-model:value="severity" clearable placeholder="日志级别" :options="severityOptions" class="audit-log-tabs__select" />
      <n-button type="primary" @click="reloadVisible">查询</n-button>
    </template>
  </ListPageRuntime>
</template>

<script lang="ts" setup>
  import { computed, h, onMounted, reactive, ref } from 'vue';
  import type { DataTableColumns, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { getTenants } from '@/api/business';
  import { getAuditLogs, type AuditLogCategory, type AuditLogRow } from '@/api/auditLogging';
  import { defineListPage, ListPageRuntime, runtimeListParams } from '@/page-runtime';
  import type { CollectionViewSchema, ListRuntimeState } from '@/page-runtime';
  import { useUserStore } from '@/store/modules/user';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { usePermission } from '@/hooks/web/usePermission';

  type CategoryConfig = {
    category: AuditLogCategory;
    label: string;
    title: string;
    description: string;
    permission: string;
  };

  const props = withDefaults(
    defineProps<{
      initialCategory?: AuditLogCategory;
    }>(),
    {
      initialCategory: 'system',
    }
  );

  const { hasPermission } = usePermission();
  const userStore = useUserStore();
  const tenantLoading = ref(false);
  const selectedTenantId = ref<number | null>(null);
  const tenantOptions = ref<SelectOption[]>([]);
  const keyword = ref('');
  const outcome = ref<string | null>(null);
  const severity = ref<string | null>(null);

  const rowsByCategory = reactive<Record<AuditLogCategory, AuditLogRow[]>>({
    system: [],
    operation: [],
    api: [],
    sql: [],
    visitor: [],
  });
  const totalsByCategory = reactive<Record<AuditLogCategory, number>>({
    system: 0,
    operation: 0,
    api: 0,
    sql: 0,
    visitor: 0,
  });
  const loadingByCategory = reactive<Record<AuditLogCategory, boolean>>({
    system: false,
    operation: false,
    api: false,
    sql: false,
    visitor: false,
  });

  const categoryConfigs: CategoryConfig[] = [
    {
      category: 'system',
      label: '系统日志',
      title: '系统日志',
      description: '查看平台与租户运行时系统事件。',
      permission: 'audit:system-log:view',
    },
    {
      category: 'operation',
      label: '操作日志',
      title: '操作日志',
      description: '查看用户操作和高风险配置变更。',
      permission: 'audit:operation-log:view',
    },
    {
      category: 'api',
      label: '接口日志',
      title: '接口日志',
      description: '查看应用内中间件异步采集的接口请求。',
      permission: 'audit:api-log:view',
    },
    {
      category: 'sql',
      label: 'SQL 日志',
      title: 'SQL 日志',
      description: '仅记录慢 SQL 和错误 SQL，保存去参数化后的 SQL 模板。',
      permission: 'audit:sql-log:view',
    },
    {
      category: 'visitor',
      label: '访问日志',
      title: '访问日志',
      description: '查看访客访问记录和 IP 保留策略相关信息。',
      permission: 'audit:visitor-log:view',
    },
  ];

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
  const resourceTypeLabel: Record<string, string> = {
    audit_logging_settings: '审计日志配置',
    audit_system_logs: '系统日志',
    audit_operation_logs: '操作日志',
    audit_api_logs: '接口日志',
    audit_sql_logs: 'SQL 日志',
    audit_visitor_logs: '访问日志',
    user: '用户',
    users: '用户',
    role: '角色',
    roles: '角色',
    permission: '权限',
    permissions: '权限',
    menu: '菜单',
    menus: '菜单',
    tenant: '租户',
    tenants: '租户',
    api_key: 'API 密钥',
    api_keys: 'API 密钥',
    appearance: '主题配置',
    llm_runtime: '模型运行时',
    file_object: '文件对象',
    file_library: '文件库',
    storage_profile: '存储配置',
  };
  const riskLevelLabel: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '严重',
  };

  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);
  const loading = computed(() => Object.values(loadingByCategory).some(Boolean));
  const visibleCategories = computed(() => {
    const allowed = categoryConfigs.filter((item) => hasPermission([item.permission]));
    const initial = allowed.find((item) => item.category === props.initialCategory);
    if (!initial) return allowed;
    return [initial, ...allowed.filter((item) => item.category !== props.initialCategory)];
  });

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
    {
      title: '资源类型',
      key: 'resource_type',
      width: 150,
      ellipsis: { tooltip: true },
      render: (row) => resourceTypeLabel[row.resource_type || ''] || row.resource_type || '-',
    },
    { title: '资源 ID', key: 'resource_id', width: 130, ellipsis: { tooltip: true } },
    {
      title: '风险级别',
      key: 'risk_level',
      width: 110,
      render(row) {
        const tone = row.risk_level === 'critical' || row.risk_level === 'high' ? 'error' : row.risk_level === 'medium' ? 'warning' : 'info';
        return h(AppStatusTag, { tone, label: riskLevelLabel[row.risk_level || ''] || row.risk_level || '-' });
      },
    },
  ];

  const pageSchema = computed(() =>
    defineListPage<AuditLogRow>({
      id: 'audit.logs',
      title: '审计日志',
      description: '集中查看系统日志、操作日志、接口日志、SQL 日志和访问日志。',
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'tabbed-list',
        tabs: visibleCategories.value.map((item) => ({
          name: item.category,
          label: item.label,
          count: totalsByCategory[item.category],
          title: item.title,
          description: item.description,
          rows: rowsByCategory[item.category],
          loading: loadingByCategory[item.category],
          refresh: (state) => loadCategory(item.category, state),
          paginationTotal: totalsByCategory[item.category],
          view: createTableView(item.category),
          pagination: { pageSize: 20, pageSizes: [20, 50, 100], showSizePicker: true },
        })),
      },
      toolbar: { rightTools: ['refresh'] },
      pagination: false,
    })
  );

  function createTableView(category: AuditLogCategory): CollectionViewSchema<AuditLogRow> {
    return {
      type: 'table',
      columns: columnsForCategory(category),
      rowKey: (row) => `${category}-${row.id}`,
      scrollX: category === 'sql' ? 1580 : 1420,
      sort: { remote: true },
      tableProps: { size: 'small', pagination: false },
    };
  }

  function columnsForCategory(category: AuditLogCategory): DataTableColumns<AuditLogRow> {
    if (category === 'api') return [...baseColumns.slice(0, 3), ...apiColumns, ...baseColumns.slice(4, 6)];
    if (category === 'sql') return [...baseColumns.slice(0, 3), ...sqlColumns, ...baseColumns.slice(3)];
    if (category === 'operation') return [...baseColumns.slice(0, 3), ...operationColumns, ...baseColumns.slice(3)];
    if (category === 'visitor') return [...baseColumns.slice(0, 3), ...baseColumns.slice(4)];
    return baseColumns;
  }

  async function reloadVisible() {
    await ensureTenantOptions();
    await Promise.all(visibleCategories.value.map((item) => loadCategory(item.category)));
  }

  async function loadCategory(category: AuditLogCategory, state?: ListRuntimeState) {
    loadingByCategory[category] = true;
    try {
      const payload = await getAuditLogs(category, {
        ...runtimeListParams(state),
        tenant_id: selectedTenantForRequest(),
        keyword: keyword.value || undefined,
        outcome: outcome.value || undefined,
        severity: severity.value || undefined,
      });
      rowsByCategory[category] = payload.items || [];
      totalsByCategory[category] = payload.pagination?.total || rowsByCategory[category].length;
    } finally {
      loadingByCategory[category] = false;
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

  onMounted(() => {
    reloadVisible();
  });
</script>

<style lang="less" scoped>
  .audit-log-tabs__search {
    width: 280px;
  }

  .audit-log-tabs__tenant {
    width: min(280px, 100%);
  }

  .audit-log-tabs__select {
    width: 150px;
  }
</style>
