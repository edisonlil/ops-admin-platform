<template>
  <AppPage density="compact" variant="dense-data">
    <div class="send-workbench">
      <section class="send-workbench__form">
        <div class="send-workbench__heading">
          <h2>发送站内信</h2>
          <p>向指定用户发送租户内消息，支持直接编写或套用已启用的消息模板。</p>
        </div>

        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-form-item label="发送方式" path="mode">
            <n-radio-group v-model:value="form.mode" @update:value="handleModeChange">
              <n-radio-button value="direct">直接发送</n-radio-button>
              <n-radio-button value="template">模板发送</n-radio-button>
            </n-radio-group>
          </n-form-item>

          <n-grid v-if="form.mode === 'template'" :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="消息模板" path="template_key">
              <n-select
                v-model:value="form.template_key"
                filterable
                clearable
                :options="templateOptions"
                :loading="templatesLoading"
                placeholder="选择已启用模板"
                @update:value="handleTemplateChange"
              />
            </n-form-item-gi>
            <n-form-item-gi label="发送渠道" path="channels">
              <n-checkbox-group v-model:value="form.channels">
                <n-space>
                  <n-checkbox v-for="channel in channelOptions" :key="channel.value" :value="channel.value">
                    {{ channel.label }}
                  </n-checkbox>
                </n-space>
              </n-checkbox-group>
            </n-form-item-gi>
          </n-grid>

          <n-form-item v-if="form.mode === 'template'" label="模板变量 JSON" path="variables_text">
            <n-input
              v-model:value="form.variables_text"
              type="textarea"
              placeholder='例如：{"window":"今晚 22:00","version":"v1.2.0"}'
              :autosize="{ minRows: 4, maxRows: 8 }"
              @blur="renderSelectedTemplate"
            />
          </n-form-item>

          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="标题" path="title">
              <n-input v-model:value="form.title" :disabled="form.mode === 'template'" placeholder="例如：系统维护通知" />
            </n-form-item-gi>
            <n-form-item-gi label="接收用户" path="recipient_user_ids">
              <n-select
                v-model:value="form.recipient_user_ids"
                multiple
                filterable
                remote
                clearable
                :options="userOptions"
                :loading="usersLoading"
                placeholder="搜索并选择接收用户"
                @search="handleUserSearch"
                @focus="loadUsers"
              />
            </n-form-item-gi>
            <n-form-item-gi label="消息类型" path="message_type">
              <n-select v-model:value="form.message_type" :options="typeOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="优先级" path="priority">
              <n-select v-model:value="form.priority" :options="priorityOptions" />
            </n-form-item-gi>
          </n-grid>

          <n-form-item label="内容" path="content">
            <n-input
              v-model:value="form.content"
              type="textarea"
              :disabled="form.mode === 'template'"
              placeholder="填写消息正文"
              :autosize="{ minRows: 8, maxRows: 14 }"
            />
          </n-form-item>

          <div class="send-workbench__actions">
            <n-button @click="reset">重置</n-button>
            <n-button v-if="canSendMessage" type="primary" :loading="sending" @click="submit">发送消息</n-button>
          </div>
        </n-form>
      </section>

      <aside class="send-workbench__preview">
        <div class="preview-meta">
          <AppStatusTag tone="info" :label="typeLabel" />
          <AppStatusTag tone="neutral" :label="priorityLabel" />
        </div>
        <h3>{{ previewTitle }}</h3>
        <p>{{ previewContent }}</p>
        <div v-if="missingVariables.length" class="preview-warning">缺少变量：{{ missingVariables.join('、') }}</div>
        <div class="preview-foot">
          <span>{{ form.recipient_user_ids.length }} 个接收人</span>
          <span>{{ previewChannels }}</span>
        </div>
      </aside>
    </div>
  </AppPage>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { AppPage } from '@/page-runtime';
  import { getCurrentTenantUsers } from '@/api/business';
  import { usePermission } from '@/hooks/web/usePermission';
  import {
    getMessageTemplates,
    renderMessageTemplate,
    sendInAppMessage,
    sendTemplateMessage,
    type MessageTemplate,
  } from '@/api/messaging';

  interface TenantUser {
    id: number;
    username: string;
    is_active?: boolean;
  }

  const message = useMessage();
  const { hasPermission } = usePermission();
  const formRef = ref<FormInst | null>(null);
  const sending = ref(false);
  const usersLoading = ref(false);
  const templatesLoading = ref(false);
  const allUsers = ref<TenantUser[]>([]);
  const templates = ref<MessageTemplate[]>([]);
  const userOptions = ref<SelectOption[]>([]);
  const missingVariables = ref<string[]>([]);
  const rendered = reactive({ title: '', content: '' });
  const canSendMessage = computed(() => hasPermission(['messaging:messages:send']));

  const form = reactive({
    mode: 'direct',
    title: '',
    content: '',
    template_key: null as string | null,
    variables_text: '{}',
    channels: ['in_app'] as string[],
    recipient_user_ids: [] as number[],
    message_type: 'system',
    priority: 'normal',
  });

  const typeOptions = [
    { label: '系统', value: 'system' },
    { label: '流程', value: 'workflow' },
    { label: '安全', value: 'security' },
    { label: '自定义', value: 'custom' },
  ];

  const priorityOptions = [
    { label: '低', value: 'low' },
    { label: '普通', value: 'normal' },
    { label: '高', value: 'high' },
    { label: '紧急', value: 'urgent' },
  ];

  const channelOptions = [
    { label: '站内信', value: 'in_app' },
    { label: '飞书', value: 'feishu' },
    { label: '钉钉', value: 'dingtalk' },
    { label: '邮箱', value: 'email' },
    { label: '短信', value: 'sms' },
  ];

  const templateOptions = computed<SelectOption[]>(() =>
    templates.value
      .filter((item) => item.status === 'enabled')
      .map((item) => ({
        label: `${item.name}（${item.template_key}）`,
        value: item.template_key,
      }))
  );
  const typeLabel = computed(() => typeOptions.find((item) => item.value === form.message_type)?.label || form.message_type);
  const priorityLabel = computed(() => priorityOptions.find((item) => item.value === form.priority)?.label || form.priority);
  const previewTitle = computed(() => (form.mode === 'template' ? rendered.title : form.title) || '未填写标题');
  const previewContent = computed(() => (form.mode === 'template' ? rendered.content : form.content) || '消息内容预览会显示在这里。');
  const previewChannels = computed(() => form.channels.map((value) => channelOptions.find((item) => item.value === value)?.label || value).join(' / '));

  const rules: FormRules = {
    title: [
      {
        validator() {
          return form.mode === 'template' || Boolean(form.title.trim());
        },
        message: '请填写标题',
        trigger: ['blur', 'input'],
      },
    ],
    content: [
      {
        validator() {
          return form.mode === 'template' || Boolean(form.content.trim());
        },
        message: '请填写内容',
        trigger: ['blur', 'input'],
      },
    ],
    template_key: [
      {
        validator() {
          return form.mode === 'direct' || Boolean(form.template_key);
        },
        message: '请选择消息模板',
        trigger: ['change', 'blur'],
      },
    ],
    variables_text: [
      {
        validator() {
          try {
            JSON.parse(form.variables_text || '{}');
            return true;
          } catch {
            return false;
          }
        },
        message: '模板变量必须是合法 JSON',
        trigger: ['blur'],
      },
    ],
    recipient_user_ids: [
      {
        validator() {
          return form.recipient_user_ids.length > 0;
        },
        message: '请选择至少一个接收用户',
        trigger: ['change', 'blur'],
      },
    ],
  };

  function toUserOptions(users: TenantUser[], keyword = '') {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return users
      .filter((user) => {
        const username = String(user.username || '');
        return !normalizedKeyword || username.toLowerCase().includes(normalizedKeyword) || String(user.id).includes(normalizedKeyword);
      })
      .map((user) => ({
        label: user.username,
        value: user.id,
        disabled: user.is_active === false,
      }));
  }

  function parseVariables() {
    const parsed = JSON.parse(form.variables_text || '{}');
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  }

  async function loadUsers() {
    if (allUsers.value.length || usersLoading.value) {
      return;
    }
    usersLoading.value = true;
    try {
      const payload = await getCurrentTenantUsers();
      allUsers.value = payload.items || [];
      userOptions.value = toUserOptions(allUsers.value);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '用户列表加载失败');
    } finally {
      usersLoading.value = false;
    }
  }

  async function loadTemplates() {
    if (templates.value.length || templatesLoading.value) {
      return;
    }
    templatesLoading.value = true;
    try {
      const payload = await getMessageTemplates();
      templates.value = payload.items || [];
    } catch (error) {
      message.error(error instanceof Error ? error.message : '模板列表加载失败');
    } finally {
      templatesLoading.value = false;
    }
  }

  async function handleUserSearch(keyword: string) {
    if (!allUsers.value.length) {
      await loadUsers();
    }
    userOptions.value = toUserOptions(allUsers.value, keyword);
  }

  async function handleModeChange() {
    formRef.value?.restoreValidation();
    if (form.mode === 'template') {
      await loadTemplates();
      await renderSelectedTemplate();
    }
  }

  async function handleTemplateChange() {
    const template = templates.value.find((item) => item.template_key === form.template_key);
    form.channels = template?.channels?.length ? [...template.channels] : ['in_app'];
    await renderSelectedTemplate();
  }

  async function renderSelectedTemplate() {
    if (form.mode !== 'template' || !form.template_key) {
      rendered.title = '';
      rendered.content = '';
      missingVariables.value = [];
      return;
    }
    try {
      const payload = await renderMessageTemplate({ template_key: form.template_key, variables: parseVariables() });
      rendered.title = payload.rendered.title;
      rendered.content = payload.rendered.content;
      missingVariables.value = payload.missing_variables || [];
    } catch (error) {
      message.error(error instanceof Error ? error.message : '模板预览失败');
    }
  }

  function reset() {
    form.title = '';
    form.content = '';
    form.template_key = null;
    form.variables_text = '{}';
    form.channels = ['in_app'];
    form.recipient_user_ids = [];
    form.message_type = 'system';
    form.priority = 'normal';
    rendered.title = '';
    rendered.content = '';
    missingVariables.value = [];
    formRef.value?.restoreValidation();
  }

  async function submit() {
    try {
      await formRef.value?.validate();
      if (form.mode === 'template') {
        await renderSelectedTemplate();
      }
    } catch {
      return;
    }
    sending.value = true;
    try {
      if (form.mode === 'template') {
        await sendTemplateMessage({
          template_key: String(form.template_key),
          variables: parseVariables(),
          recipient_user_ids: form.recipient_user_ids,
          message_type: form.message_type,
          priority: form.priority,
          channels: form.channels,
        });
      } else {
        await sendInAppMessage({
          title: form.title.trim(),
          content: form.content.trim(),
          recipient_user_ids: form.recipient_user_ids,
          message_type: form.message_type,
          priority: form.priority,
        });
      }
      message.success('消息已发送');
      reset();
    } finally {
      sending.value = false;
    }
  }

  loadUsers();
  loadTemplates();
</script>

<style lang="less" scoped>
  .send-workbench {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 16px;
    align-items: start;
  }

  .send-workbench__form,
  .send-workbench__preview {
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-card-radius);
    background: var(--app-surface-bg);
  }

  .send-workbench__form {
    padding: 18px;
  }

  .send-workbench__heading {
    margin-bottom: 16px;

    h2 {
      margin: 0 0 4px;
      font-size: 18px;
      font-weight: 650;
    }

    p {
      margin: 0;
      color: var(--app-text-color-2);
      line-height: 1.6;
    }
  }

  .send-workbench__actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  .send-workbench__preview {
    display: grid;
    gap: 12px;
    min-height: 260px;
    padding: 16px;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 650;
      word-break: break-word;
    }

    p {
      margin: 0;
      color: var(--app-text-color-2);
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
    }
  }

  .preview-meta,
  .preview-foot {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .preview-warning {
    border: 1px solid #ffd591;
    border-radius: 6px;
    background: #fff7e6;
    color: #ad6800;
    padding: 8px 10px;
    line-height: 1.5;
  }

  .preview-foot {
    align-self: end;
    justify-content: space-between;
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  @media (max-width: 960px) {
    .send-workbench {
      grid-template-columns: 1fr;
    }
  }
</style>
