<template>
  <AppPage density="compact" variant="dense-data">
    <div class="send-workbench">
      <section class="send-workbench__form">
        <div class="send-workbench__heading">
          <h2>发送站内信</h2>
          <p>向指定用户发送租户内消息，发送结果会立即写入消息台账。</p>
        </div>

        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="标题" path="title">
              <n-input v-model:value="form.title" placeholder="例如：系统维护通知" />
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
              placeholder="填写消息正文"
              :autosize="{ minRows: 8, maxRows: 14 }"
            />
          </n-form-item>
          <div class="send-workbench__actions">
            <n-button @click="reset">重置</n-button>
            <n-button type="primary" :loading="sending" @click="submit">发送消息</n-button>
          </div>
        </n-form>
      </section>

      <aside class="send-workbench__preview">
        <div class="preview-meta">
          <AppStatusTag tone="info" :label="form.message_type" />
          <AppStatusTag tone="neutral" :label="form.priority" />
        </div>
        <h3>{{ form.title || '未填写标题' }}</h3>
        <p>{{ form.content || '消息内容预览会显示在这里。' }}</p>
        <div class="preview-foot">
          <span>{{ form.recipient_user_ids.length }} 个接收人</span>
          <span>in_app</span>
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
  import { sendInAppMessage } from '@/api/messaging';

  interface TenantUser {
    id: number;
    username: string;
    is_active?: boolean;
  }

  const message = useMessage();
  const formRef = ref<FormInst | null>(null);
  const sending = ref(false);
  const usersLoading = ref(false);
  const allUsers = ref<TenantUser[]>([]);
  const userOptions = ref<SelectOption[]>([]);
  const form = reactive({
    title: '',
    content: '',
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

  const rules: FormRules = {
    title: [{ required: true, message: '请填写标题', trigger: ['blur', 'input'] }],
    content: [{ required: true, message: '请填写内容', trigger: ['blur', 'input'] }],
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

  async function handleUserSearch(keyword: string) {
    if (!allUsers.value.length) {
      await loadUsers();
    }
    userOptions.value = toUserOptions(allUsers.value, keyword);
  }

  function reset() {
    form.title = '';
    form.content = '';
    form.recipient_user_ids = [];
    form.message_type = 'system';
    form.priority = 'normal';
    formRef.value?.restoreValidation();
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    sending.value = true;
    try {
      await sendInAppMessage({
        title: form.title.trim(),
        content: form.content.trim(),
        recipient_user_ids: form.recipient_user_ids,
        message_type: form.message_type,
        priority: form.priority,
      });
      message.success('消息已发送');
      reset();
    } finally {
      sending.value = false;
    }
  }

  loadUsers();
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
