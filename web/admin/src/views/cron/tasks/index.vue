<template>
  <div class="cron-task-page">
    <ListPageRuntime
      :schema="taskPage"
      :rows="taskRows"
      :loading="loadingTasks"
      :pagination-total="paginationTotal"
      @refresh="reloadTasks"
    />

    <n-drawer v-model:show="drawerVisible" width="560">
      <n-drawer-content :title="form.id ? '编辑定时任务' : '新增定时任务'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top" class="cron-task-page__drawer-form">
          <section class="cron-task-page__drawer-section cron-task-page__basic-section">
            <div class="cron-task-page__basic-row">
              <n-form-item label="任务标识" path="task_key">
                <n-input v-model:value="form.task_key" placeholder="system.health_snapshot" />
              </n-form-item>
              <n-form-item label="任务名称" path="name">
                <n-input v-model:value="form.name" placeholder="默认使用任务标识" />
              </n-form-item>
            </div>
            <n-form-item label="执行命令" path="execution_target">
              <n-input v-model:value="form.execution_target" placeholder="system.health.snapshot" />
            </n-form-item>
            <n-form-item label="状态" path="status">
              <n-select v-model:value="form.status" :options="statusOptions" :disabled="isEditingEnabledTask" />
            </n-form-item>
            <n-form-item label="说明">
              <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
            </n-form-item>
          </section>

          <section class="cron-task-page__drawer-section cron-task-page__schedule-panel">
            <div class="cron-task-page__section-title">执行频率</div>

            <n-radio-group v-model:value="simpleSchedule.mode" name="scheduleMode" size="small" class="cron-task-page__schedule-modes">
              <n-radio-button
                v-for="option in scheduleModeOptions"
                :key="option.value"
                :value="option.value"
                :label="option.label"
              />
            </n-radio-group>

            <div class="cron-task-page__schedule-fields">
              <n-form-item v-if="simpleSchedule.mode === 'interval'" label="固定间隔" path="schedule.trigger_expression">
                <n-input-group>
                  <n-input-number
                    v-model:value="simpleSchedule.intervalEvery"
                    :min="1"
                    :max="9999"
                    class="cron-task-page__interval-number"
                  />
                  <n-select
                    v-model:value="simpleSchedule.intervalUnit"
                    :options="intervalUnitOptions"
                    class="cron-task-page__interval-unit"
                  />
                </n-input-group>
              </n-form-item>

              <n-form-item v-if="simpleSchedule.mode === 'daily'" label="执行时间" path="schedule.trigger_expression">
                <n-time-picker
                  v-model:formatted-value="simpleSchedule.time"
                  format="HH:mm"
                  value-format="HH:mm"
                  :clearable="false"
                  class="cron-task-page__control"
                />
              </n-form-item>

              <n-form-item v-if="simpleSchedule.mode === 'weekly'" label="星期" path="schedule.trigger_expression" class="cron-task-page__field-wide">
                <n-checkbox-group v-model:value="simpleSchedule.weekdays">
                  <n-space item-style="display: flex;">
                    <n-checkbox v-for="day in weekdayOptions" :key="day.value" :value="day.value" :label="day.label" />
                  </n-space>
                </n-checkbox-group>
              </n-form-item>
              <n-form-item v-if="simpleSchedule.mode === 'weekly'" label="执行时间" path="schedule.trigger_expression">
                <n-time-picker
                  v-model:formatted-value="simpleSchedule.time"
                  format="HH:mm"
                  value-format="HH:mm"
                  :clearable="false"
                  class="cron-task-page__control"
                />
              </n-form-item>

              <n-form-item v-if="simpleSchedule.mode === 'monthly'" label="每月日期" path="schedule.trigger_expression">
                <n-input-number
                  v-model:value="simpleSchedule.monthDay"
                  :min="1"
                  :max="31"
                  class="cron-task-page__control"
                />
              </n-form-item>
              <n-form-item v-if="simpleSchedule.mode === 'monthly'" label="执行时间" path="schedule.trigger_expression">
                <n-time-picker
                  v-model:formatted-value="simpleSchedule.time"
                  format="HH:mm"
                  value-format="HH:mm"
                  :clearable="false"
                  class="cron-task-page__control"
                />
              </n-form-item>

              <n-form-item v-if="simpleSchedule.mode === 'once'" label="执行时间" path="schedule.trigger_expression" class="cron-task-page__field-wide">
                <n-date-picker
                  v-model:formatted-value="simpleSchedule.runAt"
                  type="datetime"
                  value-format="yyyy-MM-dd HH:mm:ss"
                  class="cron-task-page__control"
                />
              </n-form-item>

              <n-form-item v-if="simpleSchedule.mode === 'advanced'" label="触发类型" path="schedule.trigger_type">
                <n-select v-model:value="form.schedule.trigger_type" :options="triggerOptions" />
              </n-form-item>
              <n-form-item v-if="simpleSchedule.mode === 'advanced'" label="触发表达式" path="schedule.trigger_expression">
                <n-input v-model:value="form.schedule.trigger_expression" placeholder="*/5 * * * * 或 60" />
              </n-form-item>

              <n-form-item label="并发策略" path="concurrency_policy">
                <n-select v-model:value="form.concurrency_policy" :options="concurrencyOptions" />
              </n-form-item>
            </div>

            <div class="cron-task-page__schedule-preview">
              <span class="cron-task-page__preview-label">计划</span>
              <div class="cron-task-page__preview-main">
                <strong>{{ schedulePreview }}</strong>
                <span class="cron-task-page__schedule-expression">{{ scheduleExpressionPreview }}</span>
              </div>
            </div>
          </section>

          <section class="cron-task-page__drawer-section cron-task-page__execution-section">
            <n-form-item label="超时秒数" path="timeout_seconds">
              <n-input-number v-model:value="form.timeout_seconds" :min="1" :max="86400" class="cron-task-page__number" />
            </n-form-item>
            <n-form-item label="最大尝试" path="max_attempts">
              <n-input-number v-model:value="form.max_attempts" :min="1" :max="100" class="cron-task-page__number" />
            </n-form-item>
          </section>

          <n-collapse arrow-placement="right" class="cron-task-page__collapse">
            <n-collapse-item title="默认 Payload JSON" name="payload">
              <n-form-item :show-label="false">
                <n-input v-model:value="payloadText" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
              </n-form-item>
            </n-collapse-item>
          </n-collapse>
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
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    disableCronTask,
    enableCronTask,
    getCronTasks,
    saveCronTask,
    triggerCronTask,
    type CronSchedule,
    type CronTask,
  } from '@/api/cron';

  type ScheduleMode = 'interval' | 'daily' | 'weekly' | 'monthly' | 'once' | 'advanced';
  type IntervalUnit = 'seconds' | 'minutes' | 'hours' | 'days';
  type ScheduleDraft = Pick<CronSchedule, 'trigger_type' | 'trigger_expression' | 'timezone'>;

  type CronTaskForm = Partial<CronTask> & {
    schedule: ScheduleDraft;
  };

  const intervalMultipliers: Record<IntervalUnit, number> = {
    seconds: 1,
    minutes: 60,
    hours: 3600,
    days: 86400,
  };

  const intervalUnitLabels: Record<IntervalUnit, string> = {
    seconds: '秒',
    minutes: '分钟',
    hours: '小时',
    days: '天',
  };

  const weekdayLabels: Record<string, string> = {
    mon: '周一',
    tue: '周二',
    wed: '周三',
    thu: '周四',
    fri: '周五',
    sat: '周六',
    sun: '周日',
  };

  const message = useMessage();
  const router = useRouter();
  const { hasPermission } = usePermission();
  const loadingTasks = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const taskRows = ref<CronTask[]>([]);
  const paginationTotal = ref(0);
  const listState = ref<ListRuntimeState>({});
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
      trigger_type: 'interval',
      trigger_expression: '300',
      timezone: resolveDefaultTimezone(),
    },
  });

  const simpleSchedule = reactive({
    mode: 'interval' as ScheduleMode,
    intervalEvery: 5,
    intervalUnit: 'minutes' as IntervalUnit,
    time: '09:00',
    weekdays: ['mon'] as string[],
    monthDay: 1,
    runAt: '',
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

  const scheduleModeOptions: SelectOption[] = [
    { label: '固定间隔', value: 'interval' },
    { label: '每天', value: 'daily' },
    { label: '每周', value: 'weekly' },
    { label: '每月', value: 'monthly' },
    { label: '一次性', value: 'once' },
    { label: '高级表达式', value: 'advanced' },
  ];

  const intervalUnitOptions: SelectOption[] = [
    { label: '秒', value: 'seconds' },
    { label: '分钟', value: 'minutes' },
    { label: '小时', value: 'hours' },
    { label: '天', value: 'days' },
  ];

  const weekdayOptions: SelectOption[] = [
    { label: '周一', value: 'mon' },
    { label: '周二', value: 'tue' },
    { label: '周三', value: 'wed' },
    { label: '周四', value: 'thu' },
    { label: '周五', value: 'fri' },
    { label: '周六', value: 'sat' },
    { label: '周日', value: 'sun' },
  ];

  const concurrencyOptions: SelectOption[] = [
    { label: '禁止并发', value: 'forbid' },
    { label: '允许并发', value: 'allow' },
    { label: '替换运行', value: 'replace' },
    { label: '排队执行', value: 'queue' },
  ];

  const schedulePreview = computed(() => describeScheduleDraft(buildScheduleDraft()));
  const scheduleExpressionPreview = computed(() => {
    const schedule = buildScheduleDraft();
    return `保存为：${schedule.trigger_type} / ${schedule.trigger_expression || '-'}`;
  });

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
      minWidth: 200,
      render(row) {
        return row.schedule ? describeScheduleDraft(row.schedule) : '-';
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
      sort: { remote: true },
      rowKey: (row) => row.id,
      scrollX: 1320,
      columnRuntime: {
        columns: [
          { key: 'name', label: '任务名称', sortable: true },
          { key: 'task_key', label: '任务编码', sortable: true },
          { key: 'execution_target', label: '执行目标', sortable: true },
          { key: 'status', label: '状态', sortable: true },
          { key: 'schedule', label: '调度' },
          { key: 'update_time', label: '更新时间', sortable: true },
          { key: 'actions', label: '操作', required: true },
        ],
      },
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
    const timezone = resolveDefaultTimezone();
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
      schedule: { trigger_type: 'interval', trigger_expression: '300', timezone },
    });
    Object.assign(simpleSchedule, {
      mode: 'interval',
      intervalEvery: 5,
      intervalUnit: 'minutes',
      time: '09:00',
      weekdays: ['mon'],
      monthDay: 1,
      runAt: '',
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
    const schedule = {
      trigger_type: row.schedule?.trigger_type || 'interval',
      trigger_expression: row.schedule?.trigger_expression || '300',
      timezone: row.schedule?.timezone || resolveDefaultTimezone(),
    };
    Object.assign(form, { ...row, schedule });
    hydrateSimpleSchedule(schedule);
    payloadText.value = JSON.stringify(row.default_payload || {}, null, 2);
    drawerVisible.value = true;
  }

  async function submit() {
    if (isEditingEnabledTask.value) {
      message.warning('启用中的任务不能编辑，请先停用任务');
      return;
    }
    if (!String(form.name || '').trim()) {
      form.name = String(form.task_key || '').trim();
    }
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    const schedule = buildScheduleDraft();
    const scheduleError = validateScheduleDraft(schedule);
    if (scheduleError) {
      message.error(scheduleError);
      return;
    }
    let defaultPayload: Record<string, unknown>;
    try {
      defaultPayload = JSON.parse(payloadText.value || '{}');
    } catch {
      message.error('Payload 不是合法 JSON');
      return;
    }
    if (!defaultPayload || Array.isArray(defaultPayload) || typeof defaultPayload !== 'object') {
      message.error('Payload 必须是 JSON 对象');
      return;
    }
    Object.assign(form.schedule, schedule);
    saving.value = true;
    try {
      await saveCronTask({ ...form, schedule: { ...form.schedule }, default_payload: defaultPayload });
      message.success('任务保存成功');
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
    message.success('已触发运行');
    openRuns(row);
  }

  function openRuns(row: CronTask) {
    router.push({ path: '/cron/runs', query: { task_id: String(row.id) } });
  }

  async function reloadTasks(state: ListRuntimeState = listState.value) {
    listState.value = state;
    loadingTasks.value = true;
    try {
      const payload = await getCronTasks(runtimeListParams(state));
      taskRows.value = payload.items || [];
      paginationTotal.value = payload.pagination?.total || taskRows.value.length;
    } finally {
      loadingTasks.value = false;
    }
  }

  function buildScheduleDraft(): ScheduleDraft {
    const timezone = String(form.schedule.timezone || resolveDefaultTimezone()).trim() || resolveDefaultTimezone();
    if (simpleSchedule.mode === 'advanced') {
      return {
        trigger_type: String(form.schedule.trigger_type || 'cron').trim() || 'cron',
        trigger_expression: String(form.schedule.trigger_expression || '').trim(),
        timezone,
      };
    }
    if (simpleSchedule.mode === 'interval') {
      const every = Number(simpleSchedule.intervalEvery || 0);
      const seconds = every * intervalMultipliers[simpleSchedule.intervalUnit];
      return { trigger_type: 'interval', trigger_expression: String(seconds || ''), timezone };
    }
    if (simpleSchedule.mode === 'daily') {
      return { trigger_type: 'cron', trigger_expression: timeToCron(simpleSchedule.time, '*', '*'), timezone };
    }
    if (simpleSchedule.mode === 'weekly') {
      return {
        trigger_type: 'cron',
        trigger_expression: timeToCron(simpleSchedule.time, '*', simpleSchedule.weekdays.join(',')),
        timezone,
      };
    }
    if (simpleSchedule.mode === 'monthly') {
      return {
        trigger_type: 'cron',
        trigger_expression: timeToCron(simpleSchedule.time, String(simpleSchedule.monthDay || ''), '*'),
        timezone,
      };
    }
    return {
      trigger_type: 'date',
      trigger_expression: String(simpleSchedule.runAt || '').trim(),
      timezone,
    };
  }

  function validateScheduleDraft(schedule: ScheduleDraft): string {
    if (!schedule.timezone.trim()) {
      return '请填写时区';
    }
    if (!schedule.trigger_expression.trim()) {
      return '请填写执行时间或表达式';
    }
    if (schedule.trigger_type === 'interval') {
      const seconds = Number(schedule.trigger_expression);
      if (!Number.isInteger(seconds) || seconds <= 0) {
        return '固定间隔必须大于 0';
      }
    }
    if (simpleSchedule.mode === 'weekly' && simpleSchedule.weekdays.length === 0) {
      return '请选择至少一个星期';
    }
    if (simpleSchedule.mode === 'once' && !simpleSchedule.runAt) {
      return '请选择一次性执行时间';
    }
    if (simpleSchedule.mode === 'monthly' && (!simpleSchedule.monthDay || simpleSchedule.monthDay < 1 || simpleSchedule.monthDay > 31)) {
      return '每月日期必须在 1 到 31 之间';
    }
    return '';
  }

  function hydrateSimpleSchedule(schedule: ScheduleDraft) {
    const parsed = parseScheduleDraft(schedule);
    Object.assign(simpleSchedule, parsed);
  }

  function parseScheduleDraft(schedule: ScheduleDraft) {
    if (schedule.trigger_type === 'interval') {
      const seconds = Number(schedule.trigger_expression);
      const unit = pickIntervalUnit(seconds);
      return {
        mode: 'interval' as ScheduleMode,
        intervalEvery: Math.max(1, seconds / intervalMultipliers[unit]),
        intervalUnit: unit,
      };
    }
    if (schedule.trigger_type === 'date') {
      return {
        mode: 'once' as ScheduleMode,
        runAt: normalizeDateTimeValue(schedule.trigger_expression),
      };
    }
    const parts = schedule.trigger_expression.trim().split(/\s+/);
    const cronParts = parts.length === 6 ? parts.slice(1) : parts;
    if (cronParts.length === 5) {
      const [minute, hour, day, month, weekday] = cronParts;
      const time = cronToTime(hour, minute);
      if (time && day === '*' && month === '*' && weekday === '*') {
        return { mode: 'daily' as ScheduleMode, time };
      }
      if (time && day === '*' && month === '*' && weekday !== '*') {
        return { mode: 'weekly' as ScheduleMode, time, weekdays: weekday.split(',').filter(Boolean) };
      }
      if (time && /^\d+$/.test(day) && month === '*' && weekday === '*') {
        return { mode: 'monthly' as ScheduleMode, time, monthDay: Number(day) };
      }
    }
    return { mode: 'advanced' as ScheduleMode };
  }

  function describeScheduleDraft(schedule: ScheduleDraft): string {
    if (schedule.trigger_type === 'interval') {
      const seconds = Number(schedule.trigger_expression);
      const unit = pickIntervalUnit(seconds);
      const every = Number.isFinite(seconds) && seconds > 0 ? seconds / intervalMultipliers[unit] : 0;
      return every > 0 ? `每 ${every} ${intervalUnitLabels[unit]}执行一次` : '固定间隔执行';
    }
    if (schedule.trigger_type === 'date') {
      return schedule.trigger_expression ? `一次性执行：${normalizeDateTimeValue(schedule.trigger_expression)}` : '一次性执行';
    }
    const parsed = parseScheduleDraft(schedule);
    if (parsed.mode === 'daily') {
      return `每天 ${parsed.time} 执行`;
    }
    if (parsed.mode === 'weekly') {
      const days = (parsed.weekdays || []).map((day) => weekdayLabels[day] || day).join('、');
      return `每周 ${days} ${parsed.time} 执行`;
    }
    if (parsed.mode === 'monthly') {
      return `每月 ${parsed.monthDay} 号 ${parsed.time} 执行`;
    }
    return `${schedule.trigger_type} / ${schedule.trigger_expression}`;
  }

  function timeToCron(time: string, day: string, weekday: string): string {
    const [hour = '0', minute = '0'] = String(time || '09:00').split(':');
    return `${Number(minute)} ${Number(hour)} ${day} * ${weekday}`;
  }

  function cronToTime(hour: string, minute: string): string {
    if (!/^\d+$/.test(hour) || !/^\d+$/.test(minute)) {
      return '';
    }
    const hourNumber = Number(hour);
    const minuteNumber = Number(minute);
    if (hourNumber < 0 || hourNumber > 23 || minuteNumber < 0 || minuteNumber > 59) {
      return '';
    }
    return `${String(hourNumber).padStart(2, '0')}:${String(minuteNumber).padStart(2, '0')}`;
  }

  function pickIntervalUnit(seconds: number): IntervalUnit {
    if (Number.isFinite(seconds) && seconds > 0) {
      if (seconds % intervalMultipliers.days === 0) return 'days';
      if (seconds % intervalMultipliers.hours === 0) return 'hours';
      if (seconds % intervalMultipliers.minutes === 0) return 'minutes';
    }
    return 'seconds';
  }

  function normalizeDateTimeValue(value: string): string {
    return String(value || '').replace('T', ' ').replace(/Z$/, '').slice(0, 19);
  }

  function resolveDefaultTimezone(): string {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai';
  }

  reloadTasks();
</script>

<style lang="less" scoped>
  .cron-task-page {
    display: grid;
    gap: 16px;
    min-width: 0;
  }

  .cron-task-page__number,
  .cron-task-page__control {
    width: 100%;
  }

  .cron-task-page__drawer-form {
    display: grid;
    gap: 18px;
  }

  .cron-task-page__drawer-section {
    display: grid;
    gap: 10px;
  }

  .cron-task-page__drawer-section :deep(.n-form-item) {
    margin-bottom: 0;
  }

  .cron-task-page__drawer-section :deep(.n-form-item-feedback-wrapper) {
    min-height: 0;
  }

  .cron-task-page__drawer-section :deep(.n-form-item-feedback) {
    padding-top: 6px;
  }

  .cron-task-page__basic-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: start;
    gap: 14px;
  }

  .cron-task-page__basic-row :deep(.n-form-item) {
    align-self: start;
  }

  .cron-task-page__schedule-panel {
    padding-top: 2px;
  }

  .cron-task-page__section-title {
    color: var(--text-color-1);
    font-size: 15px;
    font-weight: 600;
  }

  .cron-task-page__schedule-modes {
    display: flex;
    flex-wrap: wrap;
    gap: 0;
  }

  .cron-task-page__schedule-modes :deep(.n-radio-button) {
    flex: 1 1 auto;
  }

  .cron-task-page__schedule-fields {
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(150px, 0.9fr);
    gap: 10px 24px;
  }

  .cron-task-page__field-wide {
    grid-column: 1 / -1;
  }

  .cron-task-page__execution-section {
    gap: 16px;
  }

  .cron-task-page__interval-number {
    width: 52%;
  }

  .cron-task-page__interval-unit {
    width: 48%;
  }

  .cron-task-page__schedule-preview {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    column-gap: 10px;
    padding: 4px 0 0;
    color: var(--text-color-1);
    font-size: 14px;
  }

  .cron-task-page__preview-label {
    color: var(--text-color-2);
    font-size: 12px;
  }

  .cron-task-page__preview-main {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 6px 12px;
    min-width: 0;
  }

  .cron-task-page__preview-main strong {
    font-weight: 600;
  }

  .cron-task-page__schedule-expression {
    min-width: 0;
    color: var(--text-color-3);
    font-size: 12px;
    overflow-wrap: anywhere;
  }

  .cron-task-page__collapse {
    margin-top: 2px;
  }

  .cron-task-page__collapse :deep(.n-collapse-item) {
    border-top: 0;
  }

  .cron-task-page__collapse :deep(.n-collapse-item__header) {
    padding: 4px 0 10px;
  }

  .cron-task-page__collapse :deep(.n-collapse-item__content-inner) {
    padding: 0 0 4px;
  }

  @media (max-width: 720px) {
    .cron-task-page__drawer-form {
      gap: 16px;
    }

    .cron-task-page__schedule-fields {
      display: grid;
      grid-template-columns: 1fr;
    }

    .cron-task-page__basic-row {
      grid-template-columns: 1fr;
      gap: 10px;
    }

    .cron-task-page__schedule-expression {
      padding-left: 0;
    }
  }
</style>
