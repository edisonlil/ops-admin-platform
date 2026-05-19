<template>
  <div>
    <ListPageRuntime :schema="chatBotPage" :rows="rows" :loading="loading" @refresh="reload" />
    <n-drawer v-model:show="drawerVisible" width="620">
      <n-drawer-content :title="form.id ? '编辑群聊机器人' : '新增群聊机器人'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="机器人名称" path="name">
              <n-input v-model:value="form.name" placeholder="例如：运维告警群机器人" />
            </n-form-item-gi>
            <n-form-item-gi label="渠道平台" path="platform">
              <n-select v-model:value="form.platform" :options="platformOptions" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="Webhook 地址" path="webhook_url">
            <n-input v-model:value="form.webhook_url" placeholder="粘贴群机器人 Webhook 地址" />
          </n-form-item>
          <n-form-item label="签名密钥">
            <n-input
              v-model:value="form.signing_secret"
              type="password"
              show-password-on="click"
              placeholder="可选，飞书和钉钉建议填写"
            />
          </n-form-item>
          <n-form-item label="描述">
            <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
          </n-form-item>
          <n-space>
            <n-checkbox v-model:checked="form.enabled">启用</n-checkbox>
            <n-checkbox v-model:checked="form.is_default">设为默认机器人</n-checkbox>
          </n-space>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存机器人</n-button>
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
  import { defineListPage, ListPageRuntime, runtimeSortParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    disableMessageChatBot,
    enableMessageChatBot,
    getMessageChatBots,
    saveMessageChatBot,
    testMessageChatBot,
    type MessageChatBot,
  } from '@/api/messaging';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<MessageChatBot[]>([]);

  const form = reactive<Partial<MessageChatBot>>({
    id: undefined,
    platform: 'wps',
    name: '',
    description: '',
    webhook_url: '',
    signing_secret: '',
    message_format: 'text',
    enabled: true,
    is_default: false,
  });

  const platformOptions: SelectOption[] = [
    { label: 'WPS协作', value: 'wps' },
    { label: '企业微信', value: 'wecom' },
    { label: '飞书', value: 'feishu' },
    { label: '钉钉', value: 'dingtalk' },
  ];

  const platformLabelMap = Object.fromEntries(platformOptions.map((item) => [item.value, item.label])) as Record<string, string>;

  const rules: FormRules = {
    name: [{ required: true, message: '请输入机器人名称', trigger: ['blur', 'input'] }],
    platform: [{ required: true, message: '请选择渠道平台', trigger: ['change', 'blur'] }],
    webhook_url: [{ required: true, message: '请输入 Webhook 地址', trigger: ['blur', 'input'] }],
  };

  const columns: DataTableColumns<MessageChatBot> = [
    { title: '机器人名称', key: 'name', minWidth: 180 },
    { title: '渠道平台', key: 'platform', width: 120, render: (row) => platformLabelMap[row.platform] || row.platform },
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
    { title: 'Webhook', key: 'webhook_url', minWidth: 220, render: (row) => row.webhook_url || '-' },
    {
      title: '测试结果',
      key: 'last_test_status',
      width: 130,
      render(row) {
        if (!row.last_test_status) return '-';
        return h(AppStatusTag, {
          tone: row.last_test_status === 'success' ? 'success' : 'error',
          label: row.last_test_status === 'success' ? '成功' : '失败',
        });
      },
    },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time) },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['messaging:chat_bots:update']), onClick: () => openEdit(row) },
            { label: '测试', show: hasPermission(['messaging:chat_bots:test']), onClick: () => testBot(row) },
            {
              label: row.enabled ? '停用' : '启用',
              tone: row.enabled ? 'danger' : 'primary',
              show: hasPermission([row.enabled ? 'messaging:chat_bots:disable' : 'messaging:chat_bots:enable']),
              onClick: () => toggleEnabled(row),
            },
          ],
        });
      },
    },
  ];

  const chatBotPage = defineListPage<MessageChatBot>({
    id: 'messaging.chatBots',
    title: '群聊机器人',
    description: '配置 WPS协作、企业微信、飞书、钉钉群机器人，用于消息发送和业务通知。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1200,
      sort: { remote: true },
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['messaging:chat_bots:create'])
        ? { key: 'create', label: '新增机器人', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function resetForm() {
    form.id = undefined;
    form.platform = 'wps';
    form.name = '';
    form.description = '';
    form.webhook_url = '';
    form.signing_secret = '';
    form.message_format = 'text';
    form.enabled = true;
    form.is_default = false;
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: MessageChatBot) {
    Object.assign(form, { ...row });
    drawerVisible.value = true;
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      await saveMessageChatBot(form);
      message.success('机器人已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function testBot(row: MessageChatBot) {
    const result = await testMessageChatBot(row.id);
    if (result.ok) {
      message.success(result.message || '测试消息已发送');
    } else {
      message.warning(result.message || '测试发送失败');
    }
    await reload();
  }

  async function toggleEnabled(row: MessageChatBot) {
    if (row.enabled) {
      await disableMessageChatBot(row.id);
      message.success('机器人已停用');
    } else {
      await enableMessageChatBot(row.id);
      message.success('机器人已启用');
    }
    await reload();
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await getMessageChatBots(runtimeSortParams(state));
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>
