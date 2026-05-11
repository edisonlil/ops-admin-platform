<template>
  <div>
    <ListPageRuntime :schema="templatePage" :rows="rows" :loading="loading" @refresh="reload" />
    <n-drawer v-model:show="drawerVisible" width="640">
      <n-drawer-content :title="form.id ? '编辑消息模板' : '新增消息模板'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="模板标识" path="template_key">
              <n-input v-model:value="form.template_key" placeholder="例如：maintenance_notice" />
            </n-form-item-gi>
            <n-form-item-gi label="模板名称" path="name">
              <n-input v-model:value="form.name" placeholder="例如：系统维护通知" />
            </n-form-item-gi>
            <n-form-item-gi label="默认渠道" path="channels">
              <n-select v-model:value="form.channels" multiple :options="channelOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="状态" path="status">
              <n-select v-model:value="form.status" :options="statusOptions" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="标题模板" path="title_template">
            <n-input v-model:value="form.title_template" placeholder="例如：系统将在 {{window}} 维护" />
          </n-form-item>
          <n-form-item label="内容模板" path="content_template">
            <n-input v-model:value="form.content_template" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存模板</n-button>
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
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    disableMessageTemplate,
    enableMessageTemplate,
    getMessageTemplates,
    saveMessageTemplate,
    type MessageTemplate,
  } from '@/api/messaging';

  const message = useMessage();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<MessageTemplate[]>([]);

  const form = reactive<Partial<MessageTemplate>>({
    id: undefined,
    template_key: '',
    name: '',
    description: '',
    channels: ['in_app'],
    title_template: '',
    content_template: '',
    variables_schema: {},
    status: 'draft',
  });

  const channelOptions: SelectOption[] = [
    { label: '站内信', value: 'in_app' },
    { label: '飞书', value: 'feishu' },
    { label: '钉钉', value: 'dingtalk' },
    { label: '邮箱', value: 'email' },
    { label: '短信', value: 'sms' },
  ];
  const statusOptions: SelectOption[] = [
    { label: '草稿', value: 'draft' },
    { label: '启用', value: 'enabled' },
    { label: '停用', value: 'disabled' },
  ];
  const rules: FormRules = {
    template_key: [{ required: true, message: '请输入模板标识', trigger: ['blur', 'input'] }],
    name: [{ required: true, message: '请输入模板名称', trigger: ['blur', 'input'] }],
    title_template: [{ required: true, message: '请输入标题模板', trigger: ['blur', 'input'] }],
    content_template: [{ required: true, message: '请输入内容模板', trigger: ['blur', 'input'] }],
  };

  const columns: DataTableColumns<MessageTemplate> = [
    { title: '模板名称', key: 'name', minWidth: 180 },
    { title: '模板标识', key: 'template_key', minWidth: 180 },
    {
      title: '状态',
      key: 'status',
      width: 110,
      render(row) {
        return h(AppStatusTag, {
          tone: row.status === 'enabled' ? 'success' : row.status === 'disabled' ? 'neutral' : 'info',
          label: row.status === 'enabled' ? '启用' : row.status === 'disabled' ? '停用' : '草稿',
        });
      },
    },
    { title: '默认渠道', key: 'channels', width: 180, render: (row) => row.channels.join('、') },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time) },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', onClick: () => openEdit(row) },
            {
              label: row.status === 'enabled' ? '停用' : '启用',
              tone: row.status === 'enabled' ? 'danger' : 'primary',
              onClick: () => toggleStatus(row),
            },
          ],
        });
      },
    },
  ];

  const templatePage = defineListPage<MessageTemplate>({
    id: 'messaging.templates',
    title: '消息模板',
    description: '维护可复用的消息标题、正文和默认渠道，为后续外部平台投递提供统一内容来源。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1060,
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: { key: 'create', label: '新增模板', type: 'primary', onClick: () => openCreate() },
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function resetForm() {
    form.id = undefined;
    form.template_key = '';
    form.name = '';
    form.description = '';
    form.channels = ['in_app'];
    form.title_template = '';
    form.content_template = '';
    form.variables_schema = {};
    form.status = 'draft';
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: MessageTemplate) {
    Object.assign(form, { ...row, channels: [...row.channels] });
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
      await saveMessageTemplate(form);
      message.success('模板已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function toggleStatus(row: MessageTemplate) {
    if (row.status === 'enabled') {
      await disableMessageTemplate(row.id);
      message.success('模板已停用');
    } else {
      await enableMessageTemplate(row.id);
      message.success('模板已启用');
    }
    await reload();
  }

  async function reload() {
    loading.value = true;
    try {
      const payload = await getMessageTemplates();
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>
