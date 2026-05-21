<template>
  <div class="cron-run-page">
    <ListPageRuntime :schema="runPage" :rows="runRows" :loading="loadingRuns" :pagination-total="paginationTotal" @refresh="reloadRuns" />

    <n-drawer v-model:show="logDrawerVisible" width="min(920px, 96vw)">
      <n-drawer-content :title="selectedRun ? `运行日志 #${selectedRun.id}` : '运行日志'">
        <n-spin :show="loadingDetail">
          <div v-if="selectedRun" class="cron-run-log">
            <n-descriptions bordered :column="2" size="small">
              <n-descriptions-item label="运行 ID">{{ selectedRun.id }}</n-descriptions-item>
              <n-descriptions-item label="任务 ID">{{ selectedRun.task_id }}</n-descriptions-item>
              <n-descriptions-item label="状态">{{ runStatusLabel(selectedRun.status) }}</n-descriptions-item>
              <n-descriptions-item label="触发来源">{{ triggerSourceLabel(selectedRun.trigger_source) }}</n-descriptions-item>
              <n-descriptions-item label="触发时间">{{ formatToDateTime(selectedRun.fire_time) }}</n-descriptions-item>
              <n-descriptions-item label="开始时间">{{ formatToDateTime(selectedRun.started_time || '') }}</n-descriptions-item>
              <n-descriptions-item label="结束时间">{{ formatToDateTime(selectedRun.finished_time || '') }}</n-descriptions-item>
              <n-descriptions-item label="幂等键">{{ selectedRun.idempotency_key || '-' }}</n-descriptions-item>
              <n-descriptions-item label="失败编码">{{ selectedRun.failure_code || '-' }}</n-descriptions-item>
              <n-descriptions-item label="失败信息">{{ selectedRun.failure_message || '-' }}</n-descriptions-item>
            </n-descriptions>

            <n-tabs type="line" animated>
              <n-tab-pane name="result" tab="输出结果">
                <n-code :code="formatJson(selectedRun.result)" language="json" word-wrap />
              </n-tab-pane>
              <n-tab-pane name="payload" tab="输入参数">
                <n-code :code="formatJson(selectedRun.payload)" language="json" word-wrap />
              </n-tab-pane>
              <n-tab-pane name="attempts" tab="执行尝试">
                <n-data-table :columns="attemptColumns" :data="selectedAttempts" :pagination="false" size="small" />
              </n-tab-pane>
            </n-tabs>
          </div>
          <n-empty v-else description="请选择一条运行记录" />
        </n-spin>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { deleteCronRun, getCronRun, getCronRuns, getCronTaskRuns, stopCronRun, type CronAttempt, type CronRun } from '@/api/cron';

  const route = useRoute();
  const message = useMessage();
  const { hasPermission } = usePermission();
  const loadingRuns = ref(false);
  const loadingDetail = ref(false);
  const runRows = ref<CronRun[]>([]);
  const paginationTotal = ref(0);
  const listState = ref<ListRuntimeState>({});
  const logDrawerVisible = ref(false);
  const selectedRun = ref<CronRun | null>(null);
  const selectedAttempts = ref<CronAttempt[]>([]);
  const stoppingRunId = ref<number | null>(null);
  const deletingRunId = ref<number | null>(null);

  const taskId = computed(() => {
    const raw = Array.isArray(route.query.task_id) ? route.query.task_id[0] : route.query.task_id;
    const value = Number(raw || 0);
    return Number.isFinite(value) && value > 0 ? value : null;
  });

  const runColumns: DataTableColumns<CronRun> = [
    { title: '运行 ID', key: 'id', width: 90 },
    { title: '任务 ID', key: 'task_id', width: 90 },
    { title: '触发时间', key: 'fire_time', width: 190, render: (row) => formatToDateTime(row.fire_time) },
    {
      title: '状态',
      key: 'status',
      width: 110,
      render(row) {
        return h(AppStatusTag, {
          tone: runStatusTone(row.status),
          label: runStatusLabel(row.status),
        });
      },
    },
    {
      title: '来源',
      key: 'trigger_source',
      width: 110,
      render: (row) => triggerSourceLabel(row.trigger_source),
    },
    { title: '幂等键', key: 'idempotency_key', minWidth: 240 },
    { title: '开始时间', key: 'started_time', width: 190, render: (row) => formatToDateTime(row.started_time || '') },
    { title: '结束时间', key: 'finished_time', width: 190, render: (row) => formatToDateTime(row.finished_time || '') },
    { title: '失败原因', key: 'failure_message', minWidth: 220, ellipsis: { tooltip: true } },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '查看日志', show: hasPermission(['cron:runs:view']), onClick: () => openRunLog(row) },
            {
              label: '停止',
              tone: 'danger',
              show: canStopRun(row),
              loading: stoppingRunId.value === row.id,
              confirm: true,
              confirmTitle: '停止运行任务',
              confirmContent: `确认停止运行任务 #${row.id}？`,
              positiveText: '停止',
              onConfirm: () => stopRun(row),
            },
            {
              label: '删除',
              tone: 'danger',
              show: hasPermission(['cron:runs:delete']),
              loading: deletingRunId.value === row.id,
              confirm: true,
              confirmTitle: '删除运行记录',
              confirmContent: `确认删除运行记录 #${row.id}？关联执行尝试也会一并删除。`,
              positiveText: '删除',
              onConfirm: () => deleteRun(row),
            },
          ],
        });
      },
    },
  ];

  const attemptColumns: DataTableColumns<CronAttempt> = [
    { title: '尝试', key: 'attempt_number', width: 80 },
    {
      title: '状态',
      key: 'status',
      width: 110,
      render(row) {
        return h(AppStatusTag, {
          tone: attemptStatusTone(row.status),
          label: attemptStatusLabel(row.status),
        });
      },
    },
    { title: 'Worker', key: 'worker_id', minWidth: 160 },
    { title: '开始时间', key: 'started_time', width: 190, render: (row) => formatToDateTime(row.started_time || '') },
    { title: '结束时间', key: 'finished_time', width: 190, render: (row) => formatToDateTime(row.finished_time || '') },
    { title: '错误信息', key: 'error_message', minWidth: 220, ellipsis: { tooltip: true } },
  ];

  const runPage = computed(() =>
    defineListPage<CronRun>({
      id: 'cron.runs',
      title: '运行记录',
      description: taskId.value
        ? `查看任务 #${taskId.value} 的运行记录；自动运行需要 cron worker 进程保持启动。`
        : '查看所有定时任务运行记录；自动运行需要 cron worker 进程保持启动。',
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'table',
        columns: runColumns,
        sort: { remote: true },
        rowKey: (row) => row.id,
        scrollX: 1600,
        columnRuntime: {
          columns: [
            { key: 'id', label: '运行 ID', sortable: true },
            { key: 'task_id', label: '任务 ID', sortable: true },
            { key: 'fire_time', label: '触发时间', sortable: true },
            { key: 'status', label: '状态', sortable: true },
            { key: 'trigger_source', label: '触发来源', sortable: true },
            { key: 'idempotency_key', label: '幂等键' },
            { key: 'started_time', label: '开始时间', sortable: true },
            { key: 'finished_time', label: '结束时间', sortable: true },
            { key: 'failure_message', label: '失败信息' },
            { key: 'actions', label: '操作' },
          ],
        },
        tableProps: { size: 'small' },
      },
      toolbar: { rightTools: ['refresh'] },
      pagination: { pageSize: 20 },
    })
  );

  async function reloadRuns(state: ListRuntimeState = listState.value) {
    listState.value = state;
    loadingRuns.value = true;
    try {
      const payload = taskId.value
        ? await getCronTaskRuns(taskId.value, runtimeListParams(state))
        : await getCronRuns(runtimeListParams(state));
      runRows.value = payload.items || [];
      paginationTotal.value = payload.pagination?.total || runRows.value.length;
    } finally {
      loadingRuns.value = false;
    }
  }

  async function openRunLog(row: CronRun) {
    logDrawerVisible.value = true;
    loadingDetail.value = true;
    try {
      const payload = await getCronRun(row.id);
      selectedRun.value = payload.item;
      selectedAttempts.value = payload.attempts || [];
    } finally {
      loadingDetail.value = false;
    }
  }

  async function stopRun(row: CronRun) {
    stoppingRunId.value = row.id;
    try {
      const payload = await stopCronRun(row.id);
      selectedRun.value = payload.item;
      selectedAttempts.value = payload.attempts || [];
      message.success('运行任务已停止');
      await reloadRuns();
    } finally {
      stoppingRunId.value = null;
    }
  }

  async function deleteRun(row: CronRun) {
    deletingRunId.value = row.id;
    try {
      await deleteCronRun(row.id);
      if (selectedRun.value?.id === row.id) {
        selectedRun.value = null;
        selectedAttempts.value = [];
        logDrawerVisible.value = false;
      }
      message.success('运行记录已删除');
      await reloadRuns();
    } finally {
      deletingRunId.value = null;
    }
  }

  function canStopRun(row: CronRun) {
    return hasPermission(['cron:runs:stop']) && ['pending', 'running'].includes(row.status);
  }

  function runStatusLabel(status: string) {
    const labels: Record<string, string> = {
      pending: '等待中',
      running: '运行中',
      succeeded: '成功',
      failed: '失败',
      skipped: '已跳过',
      stopped: '已停止',
    };
    return labels[status] || status;
  }

  function runStatusTone(status: string) {
    if (status === 'succeeded') return 'success';
    if (status === 'failed') return 'error';
    if (status === 'stopped' || status === 'skipped') return 'warning';
    if (status === 'running') return 'info';
    return 'neutral';
  }

  function attemptStatusLabel(status: string) {
    const labels: Record<string, string> = {
      running: '运行中',
      succeeded: '成功',
      failed: '失败',
      stopped: '已停止',
    };
    return labels[status] || status;
  }

  function attemptStatusTone(status: string) {
    if (status === 'succeeded') return 'success';
    if (status === 'failed') return 'error';
    if (status === 'stopped') return 'warning';
    if (status === 'running') return 'info';
    return 'neutral';
  }

  function triggerSourceLabel(source: string) {
    return source === 'manual' ? '手动' : source === 'schedule' ? '计划' : source;
  }

  function formatJson(value: Record<string, unknown>) {
    return JSON.stringify(value || {}, null, 2);
  }

  watch(taskId, () => reloadRuns());
  reloadRuns();
</script>

<style lang="less" scoped>
  .cron-run-page {
    min-width: 0;
  }

  .cron-run-log {
    display: flex;
    flex-direction: column;
    gap: 16px;

    :deep(.n-code) {
      max-height: 420px;
      overflow: auto;
      border: 1px solid var(--app-border-color, #e5e7eb);
      border-radius: 6px;
    }
  }
</style>
