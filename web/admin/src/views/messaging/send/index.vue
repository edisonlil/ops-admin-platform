<template>
  <AppPage density="compact" variant="dense-data">
    <div class="send-workbench">
      <section class="send-workbench__form">
        <div class="send-workbench__heading">
          <h2>发送消息</h2>
          <p>向指定用户或群聊机器人发送消息，支持直接编写或套用已启用的消息模板。</p>
        </div>

        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-form-item label="发送方式" path="mode">
            <n-radio-group v-model:value="form.mode" @update:value="handleModeChange">
              <n-radio-button value="direct">直接发送</n-radio-button>
              <n-radio-button value="template">模板发送</n-radio-button>
            </n-radio-group>
          </n-form-item>

          <n-form-item v-if="form.mode === 'direct'" label="发送渠道" path="channels">
            <n-checkbox-group v-model:value="form.channels" @update:value="handleChannelsChange">
              <n-space>
                <n-checkbox v-for="channel in activeChannelOptions" :key="channel.value" :value="channel.value">
                  {{ channel.label }}
                </n-checkbox>
              </n-space>
            </n-checkbox-group>
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
              <n-checkbox-group v-model:value="form.channels" @update:value="handleChannelsChange">
                <n-space>
                  <n-checkbox v-for="channel in activeChannelOptions" :key="channel.value" :value="channel.value">
                    {{ channel.label }}
                  </n-checkbox>
                </n-space>
              </n-checkbox-group>
            </n-form-item-gi>
          </n-grid>

          <div v-if="form.mode === 'template' && templateVariableFields.length" class="template-variables">
            <div class="template-variables__header">
              <span>模板变量</span>
              <n-button size="tiny" text :disabled="!form.template_key" @click="renderSelectedTemplate">刷新预览</n-button>
            </div>
            <n-grid :cols="2" :x-gap="16" responsive="screen">
              <n-form-item-gi v-for="field in templateVariableFields" :key="field.key" :show-require-mark="field.required">
                <template #label>
                  <span class="template-variable-label">
                    <span>{{ field.label }}</span>
                    <span v-if="field.label !== field.key" class="template-variable-key">{{ field.key }}</span>
                  </span>
                </template>
                <n-select
                  v-if="field.options?.length"
                  v-model:value="templateVariableValues[field.key]"
                  clearable
                  :options="field.options"
                  :placeholder="field.placeholder"
                  @update:value="scheduleRenderSelectedTemplate"
                />
                <n-switch
                  v-else-if="field.type === 'boolean'"
                  v-model:value="templateVariableValues[field.key]"
                  @update:value="scheduleRenderSelectedTemplate"
                />
                <n-input-number
                  v-else-if="field.type === 'number'"
                  v-model:value="templateVariableValues[field.key]"
                  clearable
                  :placeholder="field.placeholder"
                  class="template-variable-number"
                  @update:value="scheduleRenderSelectedTemplate"
                />
                <n-input
                  v-else
                  v-model:value="templateVariableValues[field.key]"
                  clearable
                  :placeholder="field.placeholder"
                  @blur="renderSelectedTemplate"
                  @update:value="scheduleRenderSelectedTemplate"
                />
                <div v-if="field.description" class="template-variable-description">{{ field.description }}</div>
              </n-form-item-gi>
            </n-grid>
          </div>

          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="标题" path="title">
              <n-input v-model:value="form.title" :disabled="form.mode === 'template'" placeholder="例如：系统维护通知" />
            </n-form-item-gi>
            <n-form-item-gi v-if="usesInAppChannel" label="接收用户" path="recipient_user_ids">
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
            <n-form-item-gi v-if="usesChatBotChannel" label="群聊机器人" path="chat_bot_ids">
              <n-select
                v-model:value="form.chat_bot_ids"
                multiple
                filterable
                clearable
                :options="chatBotOptions"
                :loading="chatBotsLoading"
                placeholder="选择要发送到的群聊机器人"
                @focus="loadChatBots"
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
          <span>{{ form.recipient_user_ids.length }} 个接收人 / {{ form.chat_bot_ids.length }} 个机器人</span>
          <span>{{ previewChannels }}</span>
        </div>
      </aside>
    </div>
  </AppPage>
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { AppPage } from '@/page-runtime';
  import { getCurrentTenantUsers } from '@/api/business';
  import { usePermission } from '@/hooks/web/usePermission';
  import {
    getMessageChatBots,
    getMessageTemplates,
    renderMessageTemplate,
    sendInAppMessage,
    sendTemplateMessage,
    type MessageChatBot,
    type MessageTemplate,
  } from '@/api/messaging';

  interface TenantUser {
    id: number;
    username: string;
    is_active?: boolean;
  }

  interface TemplateVariableField {
    key: string;
    label: string;
    placeholder: string;
    description: string;
    type: 'text' | 'number' | 'boolean';
    required: boolean;
    options?: SelectOption[];
  }

  type SchemaRecord = Record<string, unknown>;

  const TEMPLATE_VARIABLE_PATTERN = /\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g;
  const RESERVED_SCHEMA_KEYS = new Set(['type', 'title', 'label', 'description', 'properties', 'required', 'default', 'example']);
  const message = useMessage();
  const { hasPermission } = usePermission();
  const formRef = ref<FormInst | null>(null);
  const sending = ref(false);
  const usersLoading = ref(false);
  const templatesLoading = ref(false);
  const chatBotsLoading = ref(false);
  const allUsers = ref<TenantUser[]>([]);
  const templates = ref<MessageTemplate[]>([]);
  const chatBots = ref<MessageChatBot[]>([]);
  const userOptions = ref<SelectOption[]>([]);
  const missingVariables = ref<string[]>([]);
  const templateVariableValues = reactive<Record<string, string | number | boolean | null>>({});
  const rendered = reactive({ title: '', content: '' });
  const canSendMessage = computed(() => hasPermission(['messaging:messages:send']));
  let renderTimer: ReturnType<typeof setTimeout> | undefined;

  const form = reactive({
    mode: 'direct',
    title: '',
    content: '',
    template_key: null as string | null,
    channels: ['in_app'] as string[],
    recipient_user_ids: [] as number[],
    chat_bot_ids: [] as number[],
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
    { label: '机器人', value: 'chat_bot' },
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
  const chatBotOptions = computed<SelectOption[]>(() =>
    chatBots.value
      .filter((item) => item.enabled)
      .map((item) => ({
        label: `${platformLabel(item.platform)} / ${item.name}`,
        value: item.id,
      }))
  );
  const typeLabel = computed(() => typeOptions.find((item) => item.value === form.message_type)?.label || form.message_type);
  const priorityLabel = computed(() => priorityOptions.find((item) => item.value === form.priority)?.label || form.priority);
  const previewTitle = computed(() => (form.mode === 'template' ? rendered.title : form.title) || '未填写标题');
  const previewContent = computed(() => (form.mode === 'template' ? rendered.content : form.content) || '消息内容预览会显示在这里。');
  const previewChannels = computed(() => form.channels.map((value) => channelOptions.find((item) => item.value === value)?.label || value).join(' / '));
  const selectedTemplate = computed(() => templates.value.find((item) => item.template_key === form.template_key));
  const templateVariableFields = computed<TemplateVariableField[]>(() => buildTemplateVariableFields(selectedTemplate.value));
  const activeChannelOptions = computed(() => {
    if (form.mode === 'direct') {
      return channelOptions.filter((item) => ['in_app', 'chat_bot'].includes(String(item.value)));
    }
    return channelOptions;
  });
  const usesInAppChannel = computed(() => form.channels.includes('in_app'));
  const usesChatBotChannel = computed(() => form.channels.includes('chat_bot'));

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
    recipient_user_ids: [
      {
        validator() {
          return !usesInAppChannel.value || form.recipient_user_ids.length > 0;
        },
        message: '请选择接收用户',
        trigger: ['change', 'blur'],
      },
    ],
    chat_bot_ids: [
      {
        validator() {
          return !usesChatBotChannel.value || form.chat_bot_ids.length > 0;
        },
        message: '请选择群聊机器人',
        trigger: ['change', 'blur'],
      },
    ],
    channels: [
      {
        validator() {
          return form.channels.length > 0;
        },
        message: '请选择发送渠道',
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

  function platformLabel(platform: string) {
    const labels: Record<string, string> = {
      wps: 'WPS协作',
      wecom: '企业微信',
      feishu: '飞书',
      dingtalk: '钉钉',
    };
    return labels[platform] || platform;
  }

  function asSchemaRecord(value: unknown): SchemaRecord | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as SchemaRecord) : null;
  }

  function extractTemplateVariableKeys(template?: MessageTemplate): string[] {
    if (!template) {
      return [];
    }
    const keys = new Set<string>();
    const source = `${template.title_template || ''}\n${template.content_template || ''}`;
    for (const match of source.matchAll(TEMPLATE_VARIABLE_PATTERN)) {
      keys.add(match[1]);
    }
    return [...keys];
  }

  function collectSchemaEntries(schema?: SchemaRecord): {
    entries: Map<string, unknown>;
    requiredKeys: Set<string>;
  } {
    const entries = new Map<string, unknown>();
    const requiredKeys = new Set<string>();
    if (!schema) {
      return { entries, requiredKeys };
    }
    const required = Array.isArray(schema.required) ? schema.required : [];
    required.forEach((key) => {
      if (typeof key === 'string') {
        requiredKeys.add(key);
      }
    });

    const properties = asSchemaRecord(schema.properties);
    if (properties) {
      Object.entries(properties).forEach(([key, value]) => entries.set(key, value));
      return { entries, requiredKeys };
    }

    const variables = Array.isArray(schema.variables) ? schema.variables : [];
    variables.forEach((item) => {
      if (typeof item === 'string') {
        entries.set(item, {});
      } else {
        const record = asSchemaRecord(item);
        const key = record && typeof record.key === 'string' ? record.key : record && typeof record.name === 'string' ? record.name : '';
        if (key) {
          entries.set(key, record);
        }
      }
    });

    Object.entries(schema).forEach(([key, value]) => {
      if (!RESERVED_SCHEMA_KEYS.has(key) && !entries.has(key)) {
        entries.set(key, value);
      }
    });
    return { entries, requiredKeys };
  }

  function buildTemplateVariableFields(template?: MessageTemplate): TemplateVariableField[] {
    if (!template) {
      return [];
    }
    const tokenKeys = new Set(extractTemplateVariableKeys(template));
    const schema = asSchemaRecord(template.variables_schema);
    const { entries, requiredKeys } = collectSchemaEntries(schema || undefined);
    const keys = [...new Set([...entries.keys(), ...tokenKeys])];

    return keys.map((key) => {
      const raw = entries.get(key);
      const node = asSchemaRecord(raw);
      const rawLabel = typeof raw === 'string' ? raw : undefined;
      const label = String(node?.label || node?.title || node?.name || rawLabel || key);
      const description = String(node?.description || node?.help || '');
      const typeValue = String(node?.type || '').toLowerCase();
      const options = buildVariableOptions(node);
      const fieldType: TemplateVariableField['type'] =
        typeValue === 'boolean' ? 'boolean' : typeValue === 'number' || typeValue === 'integer' ? 'number' : 'text';

      return {
        key,
        label,
        description,
        type: fieldType,
        required: tokenKeys.has(key) || requiredKeys.has(key) || node?.required === true,
        placeholder: String(node?.placeholder || node?.example || `请输入${label}`),
        options,
      };
    });
  }

  function buildVariableOptions(node: SchemaRecord | null): SelectOption[] | undefined {
    const enumValues = Array.isArray(node?.enum) ? node?.enum : Array.isArray(node?.options) ? node?.options : [];
    const options = enumValues
      .map((item) => {
        const record = asSchemaRecord(item);
        if (record) {
          const value = record.value;
          if (typeof value !== 'string' && typeof value !== 'number') {
            return null;
          }
          return { label: String(record.label || value), value };
        }
        if (typeof item !== 'string' && typeof item !== 'number') {
          return null;
        }
        return { label: String(item), value: item };
      })
      .filter(Boolean) as SelectOption[];
    return options.length ? options : undefined;
  }

  function syncTemplateVariableValues() {
    const activeKeys = new Set(templateVariableFields.value.map((field) => field.key));
    Object.keys(templateVariableValues).forEach((key) => {
      if (!activeKeys.has(key)) {
        delete templateVariableValues[key];
      }
    });
    templateVariableFields.value.forEach((field) => {
      if (typeof templateVariableValues[field.key] === 'undefined') {
        templateVariableValues[field.key] = field.type === 'boolean' ? false : null;
      }
    });
  }

  function buildVariables() {
    const variables: Record<string, unknown> = {};
    templateVariableFields.value.forEach((field) => {
      const value = templateVariableValues[field.key];
      if (value === null || typeof value === 'undefined' || value === '') {
        return;
      }
      assignVariableValue(variables, field.key, value);
    });
    return variables;
  }

  function assignVariableValue(target: Record<string, unknown>, key: string, value: unknown) {
    const parts = key.split('.').filter(Boolean);
    let current = target;
    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        current[part] = value;
        return;
      }
      const next = asSchemaRecord(current[part]) || {};
      current[part] = next;
      current = next;
    });
  }

  function findUnfilledRequiredVariables() {
    return templateVariableFields.value
      .filter((field) => field.required)
      .filter((field) => {
        const value = templateVariableValues[field.key];
        return value === null || typeof value === 'undefined' || (typeof value === 'string' && !value.trim());
      })
      .map((field) => field.label);
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

  async function loadChatBots() {
    if (chatBots.value.length || chatBotsLoading.value) {
      return;
    }
    chatBotsLoading.value = true;
    try {
      const payload = await getMessageChatBots();
      chatBots.value = payload.items || [];
    } catch (error) {
      message.error(error instanceof Error ? error.message : '机器人列表加载失败');
    } finally {
      chatBotsLoading.value = false;
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
    form.channels = ['in_app'];
    form.chat_bot_ids = [];
    if (form.mode === 'template') {
      await loadTemplates();
      await renderSelectedTemplate();
    }
  }

  async function handleTemplateChange() {
    const template = selectedTemplate.value;
    form.channels = normalizeFormChannels(template?.channels?.length ? [...template.channels] : ['in_app']);
    handleChannelsChange();
    syncTemplateVariableValues();
    await renderSelectedTemplate();
  }

  function handleChannelsChange() {
    if (!usesInAppChannel.value) {
      form.recipient_user_ids = [];
    }
    if (!usesChatBotChannel.value) {
      form.chat_bot_ids = [];
    } else {
      loadChatBots();
    }
    formRef.value?.restoreValidation();
  }

  function scheduleRenderSelectedTemplate() {
    if (renderTimer) {
      clearTimeout(renderTimer);
    }
    renderTimer = setTimeout(() => {
      renderTimer = undefined;
      renderSelectedTemplate();
    }, 350);
  }

  async function renderSelectedTemplate() {
    if (form.mode !== 'template' || !form.template_key) {
      rendered.title = '';
      rendered.content = '';
      missingVariables.value = [];
      return;
    }
    try {
      syncTemplateVariableValues();
      const payload = await renderMessageTemplate({ template_key: form.template_key, variables: buildVariables() });
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
    form.channels = ['in_app'];
    form.recipient_user_ids = [];
    form.chat_bot_ids = [];
    form.message_type = 'system';
    form.priority = 'normal';
    rendered.title = '';
    rendered.content = '';
    missingVariables.value = [];
    Object.keys(templateVariableValues).forEach((key) => delete templateVariableValues[key]);
    formRef.value?.restoreValidation();
  }

  async function submit() {
    try {
      await formRef.value?.validate();
      if (form.mode === 'template') {
        const missingRequired = findUnfilledRequiredVariables();
        if (missingRequired.length) {
          message.error(`请填写模板变量：${missingRequired.join('、')}`);
          return;
        }
        await renderSelectedTemplate();
      }
    } catch {
      return;
    }
    sending.value = true;
    try {
      if (form.mode === 'template') {
        const channels = deliveryChannels();
        await sendTemplateMessage({
          template_key: String(form.template_key),
          variables: buildVariables(),
          recipient_user_ids: form.recipient_user_ids,
          chat_bot_ids: form.chat_bot_ids,
          message_type: form.message_type,
          priority: form.priority,
          channels,
        });
      } else {
        await sendInAppMessage({
          title: form.title.trim(),
          content: form.content.trim(),
          recipient_user_ids: form.recipient_user_ids,
          chat_bot_ids: form.chat_bot_ids,
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

  function normalizeFormChannels(channels: string[]) {
    const normalized = channels.filter((channel) => channelOptions.some((item) => item.value === channel));
    return normalized.length ? [...new Set(normalized)] : ['in_app'];
  }

  function deliveryChannels() {
    return form.channels.filter((channel) => channel !== 'chat_bot');
  }

  loadUsers();
  loadTemplates();
  loadChatBots();

  onBeforeUnmount(() => {
    if (renderTimer) {
      clearTimeout(renderTimer);
    }
  });
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

  .template-variables {
    margin-bottom: 18px;
    padding: 14px 14px 2px;
    border: 1px solid var(--app-border-color);
    border-radius: 6px;
    background: var(--app-bg-color);
  }

  .template-variables__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
    color: var(--app-text-color-1);
    font-weight: 650;
  }

  .template-variable-label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    max-width: 100%;
  }

  .template-variable-key {
    overflow: hidden;
    max-width: 180px;
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 400;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .template-variable-description {
    margin-top: 6px;
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
  }

  .template-variable-number {
    width: 100%;
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
