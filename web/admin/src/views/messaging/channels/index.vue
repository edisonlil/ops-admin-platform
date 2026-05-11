<template>
  <div>
    <ListPageRuntime :schema="channelPage" :rows="rows" :loading="loading" @refresh="reload" />
    <n-drawer v-model:show="drawerVisible" width="620">
      <n-drawer-content :title="form.id ? '编辑渠道账号' : '新增渠道账号'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="渠道类型" path="channel">
              <n-select v-model:value="form.channel" :options="channelOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="账号名称" path="name">
              <n-input v-model:value="form.name" placeholder="例如：默认站内信通道" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="配置 JSON">
            <n-input v-model:value="configText" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" />
          </n-form-item>
          <n-form-item label="密钥引用">
            <n-input v-model:value="form.secret_ref" placeholder="例如：secret://messaging/feishu-default" />
          </n-form-item>
          <n-space>
            <n-checkbox v-model:checked="form.enabled">启用</n-checkbox>
            <n-checkbox v-model:checked="form.is_default">设为默认</n-checkbox>
          </n-space>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存渠道</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusGroup from '@/components/Application/AppStatusGroup.vue';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    disableMessageChannelAccount,
    enableMessageChannelAccount,
    getMessageChannelAccounts,
    saveMessageChannelAccount,
    testMessageChannelAccount,
    type MessageChannelAccount,
  } from '@/api/messaging';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<MessageChannelAccount[]>([]);
  const configText = ref('{}');

  const form = reactive<Partial<MessageChannelAccount>>({
    id: undefined,
    channel: 'in_app',
    name: '',
    config: {},
    secret_ref: '',
    enabled: true,
    is_default: false,
  });

  const channelOptions: SelectOption[] = [
    { label: '站内信', value: 'in_app' },
    { label: '飞书', value: 'feishu' },
    { label: '钉钉', value: 'dingtalk' },
    { label: '邮箱', value: 'email' },
    { label: '短信', value: 'sms' },
  ];
  const rules: FormRules = {
    channel: [{ required: true, message: '请选择渠道类型', trigger: ['change', 'blur'] }],
    name: [{ required: true, message: '请输入账号名称', trigger: ['blur', 'input'] }],
  };

  const columns: DataTableColumns<MessageChannelAccount> = [
    { title: '账号名称', key: 'name', minWidth: 200 },
    { title: '渠道', key: 'channel', width: 120 },
    {
      title: '状态',
      key: 'enabled',
      width: 160,
      render(row) {
        return h(AppStatusGroup, {
          items: [
            { key: 'enabled', label: row.enabled ? '启用' : '停用', tone: row.enabled ? 'success' : 'neutral' },
            ...(row.is_default ? [{ key: 'default', label: '默认', tone: 'info' as const }] : []),
          ],
        });
      },
    },
    { title: '密钥引用', key: 'secret_ref', minWidth: 240, render: (row) => row.secret_ref || '-' },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time) },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['messaging:channels:update']), onClick: () => openEdit(row) },
            { label: '测试', show: hasPermission(['messaging:channels:test']), onClick: () => testAccount(row) },
            {
              label: row.enabled ? '停用' : '启用',
              tone: row.enabled ? 'danger' : 'primary',
              show: hasPermission([row.enabled ? 'messaging:channels:disable' : 'messaging:channels:enable']),
              onClick: () => toggleEnabled(row),
            },
          ],
        });
      },
    },
  ];

  const channelPage = defineListPage<MessageChannelAccount>({
    id: 'messaging.channels',
    title: '渠道配置',
    description: '管理站内信、飞书、钉钉、邮箱、短信等消息通道账号，为多平台投递做准备。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1120,
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['messaging:channels:create'])
        ? { key: 'create', label: '新增渠道', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function resetForm() {
    form.id = undefined;
    form.channel = 'in_app';
    form.name = '';
    form.config = {};
    form.secret_ref = '';
    form.enabled = true;
    form.is_default = false;
    configText.value = '{}';
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: MessageChannelAccount) {
    Object.assign(form, { ...row, config: { ...(row.config || {}) } });
    configText.value = JSON.stringify(row.config || {}, null, 2);
    drawerVisible.value = true;
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    let config: Record<string, unknown> = {};
    try {
      config = JSON.parse(configText.value || '{}');
    } catch {
      message.error('配置 JSON 格式不正确');
      return;
    }
    saving.value = true;
    try {
      await saveMessageChannelAccount({ ...form, config });
      message.success('渠道已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function testAccount(row: MessageChannelAccount) {
    const result = await testMessageChannelAccount(row.id);
    if (result.ok) {
      message.success(result.message || '渠道测试通过');
    } else {
      message.warning(result.message || '渠道测试未通过');
    }
  }

  async function toggleEnabled(row: MessageChannelAccount) {
    if (row.enabled) {
      await disableMessageChannelAccount(row.id);
      message.success('渠道已停用');
    } else {
      await enableMessageChannelAccount(row.id);
      message.success('渠道已启用');
    }
    await reload();
  }

  async function reload() {
    loading.value = true;
    try {
      const payload = await getMessageChannelAccounts();
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>
