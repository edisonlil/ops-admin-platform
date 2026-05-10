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
            <n-form-item-gi label="接收用户 ID" path="recipientText">
              <n-input v-model:value="form.recipientText" placeholder="例如：1, 2, 3" />
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
          <span>{{ parsedRecipientIds.length }} 个接收人</span>
          <span>in_app</span>
        </div>
      </aside>
    </div>
  </AppPage>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { FormInst, FormRules } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { AppPage } from '@/page-runtime';
  import { sendInAppMessage } from '@/api/messaging';

  const message = useMessage();
  const formRef = ref<FormInst | null>(null);
  const sending = ref(false);
  const form = reactive({
    title: '',
    content: '',
    recipientText: '',
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

  const parsedRecipientIds = computed(() =>
    form.recipientText
      .split(',')
      .map((item) => Number(item.trim()))
      .filter((item, index, list) => Number.isInteger(item) && item > 0 && list.indexOf(item) === index)
  );

  const rules: FormRules = {
    title: [{ required: true, message: '请填写标题', trigger: ['blur', 'input'] }],
    content: [{ required: true, message: '请填写内容', trigger: ['blur', 'input'] }],
    recipientText: [
      {
        validator() {
          return parsedRecipientIds.value.length > 0;
        },
        message: '请填写至少一个数字用户 ID',
        trigger: ['blur', 'input'],
      },
    ],
  };

  function reset() {
    form.title = '';
    form.content = '';
    form.recipientText = '';
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
        recipient_user_ids: parsedRecipientIds.value,
        message_type: form.message_type,
        priority: form.priority,
      });
      message.success('消息已发送');
      reset();
    } finally {
      sending.value = false;
    }
  }
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
