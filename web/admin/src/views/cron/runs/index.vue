<template>
  <ListPageRuntime :schema="runPage" :rows="runRows" :loading="loadingRuns" :pagination-total="paginationTotal" @refresh="reloadRuns" />
</template>

<script lang="ts" setup>
  import { computed, h, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import type { DataTableColumns } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { getCronRuns, getCronTaskRuns, type CronRun } from '@/api/cron';

  const route = useRoute();
  const loadingRuns = ref(false);
  const runRows = ref<CronRun[]>([]);
  const paginationTotal = ref(0);
  const listState = ref<ListRuntimeState>({});

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
        const label = row.status === 'succeeded' ? '成功' : row.status === 'failed' ? '失败' : row.status === 'running' ? '运行中' : '等待中';
        return h(AppStatusTag, {
          tone: row.status === 'succeeded' ? 'success' : row.status === 'failed' ? 'error' : row.status === 'running' ? 'info' : 'neutral',
          label,
        });
      },
    },
    {
      title: '来源',
      key: 'trigger_source',
      width: 110,
      render(row) {
        return row.trigger_source === 'manual' ? '手动' : row.trigger_source === 'schedule' ? '计划' : row.trigger_source;
      },
    },
    { title: '幂等键', key: 'idempotency_key', minWidth: 240 },
    { title: '开始时间', key: 'started_time', width: 190, render: (row) => formatToDateTime(row.started_time || '') },
    { title: '结束时间', key: 'finished_time', width: 190, render: (row) => formatToDateTime(row.finished_time || '') },
    { title: '失败原因', key: 'failure_message', minWidth: 220, ellipsis: { tooltip: true } },
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
        scrollX: 1420,
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

  watch(taskId, () => reloadRuns());
  reloadRuns();
</script>
