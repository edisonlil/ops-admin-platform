<template>
  <div class="cron-task-page">
    <ListPageRuntime :schema="taskPage" :rows="taskRows" :loading="loadingTasks" @refresh="reloadTasks" />

    <n-drawer v-model:show="drawerVisible" width="720">
      <n-drawer-content :title="form.id ? '编辑定时任务' : '新增定时任务'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="任务标识" path="task_key">
              <n-input v-model:value="form.task_key" placeholder="system.health_snapshot" />
            </n-form-item-gi>
            <n-form-item-gi label="任务名称" path="name">
              <n-input v-model:value="form.name" placeholder="系统健康快照" />
            </n-form-item-gi>
            <n-form-item-gi label="执行命令" path="execution_target">
              <n-input v-model:value="form.execution_target" placeholder="system.health.snapshot" />
            </n-form-item-gi>
            <n-form-item-gi label="状态" path="status">
              <n-select v-model:value="form.status" :options="statusOptions" :disabled="isEditingEnabledTask" />
            </n-form-item-gi>
            <n-form-item-gi label="触发类型" path="schedule.trigger_type">
              <n-select v-model:value="form.schedule.trigger_type" :options="triggerOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="触发表达式" path="schedule.trigger_expression">
              <n-input v-model:value="form.schedule.trigger_expression" placeholder="*/5 * * * * 或 60" />
            </n-form-item-gi>
            <n-form-item-gi label="时区" path="schedule.timezone">
              <n-input v-model:value="form.schedule.timezone" placeholder="UTC" />
            </n-form-item-gi>
            <n-form-item-gi label="并发策略" path="concurrency_policy">
              <n-select v-model:value="form.concurrency_policy" :options="concurrencyOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="超时秒数" path="timeout_seconds">
              <n-input-number v-model:value="form.timeout_seconds" :min="1" :max="86400" class="cron-task-page__number" />
            </n-form-item-gi>
            <n-form-item-gi label="最大尝试" path="max_attempts">
              <n-input-number v-model:value="form.max_attempts" :min="1" :max="100" class="cron-task-page__number" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="默认 Payload JSON">
            <n-input v-model:value="payloadText" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" :disabled="isEditingEnabledTask" @click="submit">保存任务</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    disableCronTask,
    enableCronTask,
    getCronTasks,
    saveCronTask,
    triggerCronTask,
    type CronTask,
  } from '@/api/cron';

  type CronTaskForm = Partial<CronTask> & {
    schedule: {
      trigger_type: string;
      trigger_expression: string;
      timezone: string;
    };
  };

  const message = useMessage();
  const router = useRouter();
  const { hasPermission } = usePermission();
  const loadingTasks = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const taskRows = ref<CronTask[]>([]);
  const payloadText = ref('{}');
  const isEditingEnabledTask = computed(() => Boolean(form.id && form.status === 'enabled'));

  const form = reactive<CronTaskForm>({
    task_key: '',
    name: '',
    description: '',
    status: 'draft',
    execution_target: 'system.health.snapshot',
    payload_schema_version: 1,
    default_payload: {},
    concurrency_policy: 'forbid',
    timeout_seconds: 300,
    max_attempts: 1,
    retry_delay_seconds: 0,
    retry_backoff_multiplier: 1,
    misfire_policy: 'skip',
    schedule: {
      trigger_type: 'cron',
      trigger_expression: '*/5 * * * *',
      timezone: 'UTC',
    },
  });

  const rules: FormRules = {
    task_key: [{ required: true, message: '请输入任务标识', trigger: ['blur', 'input'] }],
    name: [{ required: true, message: '请输入任务名称', trigger: ['blur', 'input'] }],
    execution_target: [{ required: true, message: '请输入执行命令', trigger: ['blur', 'input'] }],
  };
  const statusOptions: SelectOption[] = [
    { label: '草稿', value: 'draft' },
    { label: '启用', value: 'enabled' },
    { label: '停用', value: 'disabled' },
  ];
  const triggerOptions: SelectOption[] = [
    { label: '定时表达式', value: 'cron' },
    { label: '固定间隔', value: 'interval' },
    { label: '指定时间', value: 'date' },
  ];
  const concurrencyOptions: SelectOption[] = [
    { label: '禁止并发', value: 'forbid' },
    { label: '允许并发', value: 'allow' },
    { label: '替换运行', value: 'replace' },
    { label: '排队执行', value: 'queue' },
  ];

  const taskColumns: DataTableColumns<CronTask> = [
    { title: '任务', key: 'name', minWidth: 200 },
    { title: '标识', key: 'task_key', minWidth: 220 },
    { title: '命令', key: 'execution_target', minWidth: 220 },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render(row) {
        return h(AppStatusTag, {
          tone: row.status === 'enabled' ? 'success' : row.status === 'disabled' ? 'neutral' : 'info',
          label: row.status === 'enabled' ? '启用' : row.status === 'disabled' ? '停用' : '草稿',
        });
      },
    },
    {
      title: '计划',
      key: 'schedule',
      minWidth: 180,
      render(row) {
        return row.schedule ? `${row.schedule.trigger_type} / ${row.schedule.trigger_expression}` : '-';
      },
    },
    { title: '更新', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 300,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '运行记录', show: hasPermission(['cron:runs:view']), onClick: () => openRuns(row) },
            {
              label: '编辑',
              show: hasPermission(['cron:tasks:update']) && row.status !== 'enabled',
              onClick: () => openEdit(row),
            },
            {
              label: row.status === 'enabled' ? '停用' : '启用',
              tone: row.status === 'enabled' ? 'danger' : 'primary',
              show: hasPermission([row.status === 'enabled' ? 'cron:tasks:disable' : 'cron:tasks:enable']),
              onClick: () => toggleStatus(row),
            },
            { label: '触发', show: hasPermission(['cron:tasks:trigger']), onClick: () => trigger(row) },
          ],
        });
      },
    },
  ];

  const taskPage = defineListPage<CronTask>({
    id: 'cron.tasks',
    title: '定时任务',
    description: '维护平台和租户级定时任务；自动调度需启动 cron worker。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns: taskColumns,
      rowKey: (row) => row.id,
      scrollX: 1320,
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['cron:tasks:create'])
        ? { key: 'create', label: '新增任务', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function resetForm() {
    Object.assign(form, {
      id: undefined,
      task_key: '',
      name: '',
      description: '',
      status: 'draft',
      execution_target: 'system.health.snapshot',
      payload_schema_version: 1,
      default_payload: {},
      concurrency_policy: 'forbid',
      timeout_seconds: 300,
      max_attempts: 1,
      retry_delay_seconds: 0,
      retry_backoff_multiplier: 1,
      misfire_policy: 'skip',
      schedule: { trigger_type: 'cron', trigger_expression: '*/5 * * * *', timezone: 'UTC' },
    });
    payloadText.value = '{}';
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: CronTask) {
    if (row.status === 'enabled') {
      message.warning('启用中的任务不能编辑，请先停用任务');
      return;
    }
    Object.assign(form, {
      ...row,
      schedule: {
        trigger_type: row.schedule?.trigger_type || 'cron',
        trigger_expression: row.schedule?.trigger_expression || '*/5 * * * *',
        timezone: row.schedule?.timezone || 'UTC',
      },
    });
    payloadText.value = JSON.stringify(row.default_payload || {}, null, 2);
    drawerVisible.value = true;
  }

  async function submit() {
    if (isEditingEnabledTask.value) {
      message.warning('启用中的任务不能编辑，请先停用任务');
      return;
    }
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    let defaultPayload: Record<string, unknown>;
    try {
      defaultPayload = JSON.parse(payloadText.value || '{}');
    } catch {
      message.error('Payload 不是合法 JSON');
      return;
    }
    saving.value = true;
    try {
      await saveCronTask({ ...form, default_payload: defaultPayload });
      message.success('任务已保存');
      drawerVisible.value = false;
      await reloadTasks();
    } finally {
      saving.value = false;
    }
  }

  async function toggleStatus(row: CronTask) {
    if (row.status === 'enabled') {
      await disableCronTask(row.id);
      message.success('任务已停用');
    } else {
      await enableCronTask(row.id);
      message.success('任务已启用');
    }
    await reloadTasks();
  }

  async function trigger(row: CronTask) {
    await triggerCronTask(row.id, row.default_payload || {});
    message.success('已执行手动运行');
    openRuns(row);
  }

  function openRuns(row: CronTask) {
    router.push({ path: '/cron/runs', query: { task_id: String(row.id) } });
  }

  async function reloadTasks() {
    loadingTasks.value = true;
    try {
      const payload = await getCronTasks({ page: 1, page_size: 50 });
      taskRows.value = payload.items || [];
    } finally {
      loadingTasks.value = false;
    }
  }

  reloadTasks();
</script>

<style lang="less" scoped>
  .cron-task-page {
    display: grid;
    gap: 16px;
    min-width: 0;
  }

  .cron-task-page__number {
    width: 100%;
  }
</style>
