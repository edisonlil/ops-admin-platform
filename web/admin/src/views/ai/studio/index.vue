<template>
  <div class="ai-studio-page">
    <ListPageRuntime :schema="studioPage" :rows="filteredApplications" :loading="loading" @refresh="reload">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索应用名称或 Key" class="ai-studio-page__search" />
        <n-select v-model:value="statusFilter" :options="statusOptions" class="ai-studio-page__status" />
      </template>

      <template #item="{ row }">
        <article
          class="ai-app-card"
          role="button"
          tabindex="0"
          @click="openDetail(row)"
          @keydown.enter.prevent="openDetail(row)"
          @keydown.space.prevent="openDetail(row)"
        >
          <header class="ai-app-card__header">
            <div class="ai-app-card__identity">
              <span class="ai-app-card__icon">
                <n-icon :component="appIcon(row)" />
              </span>
              <div>
                <h3>{{ row.name }}</h3>
                <span>{{ row.app_key }}</span>
              </div>
            </div>
            <n-tag size="small" :type="row.status === 'published' ? 'success' : 'default'">
              {{ row.status === 'published' ? '已发布' : '草稿' }}
            </n-tag>
          </header>
          <p>{{ row.description || '暂无描述' }}</p>
          <footer class="ai-app-card__footer">
            <span>{{ appTypeLabel(row.app_type) }}</span>
            <span>{{ formatAppTime(row.update_time || row.create_time) }}</span>
          </footer>
        </article>
      </template>
    </ListPageRuntime>

    <n-modal
      v-model:show="createModalVisible"
      preset="card"
      title="创建应用"
      class="ai-create-modal"
      :style="{ width: 'min(520px, calc(100vw - 32px))' }"
    >
      <n-form label-placement="top" class="ai-create-form">
        <n-form-item label="应用名称" required>
          <n-input v-model:value="createForm.name" placeholder="例如：退款说明生成" />
        </n-form-item>
        <n-form-item label="图标">
          <n-select v-model:value="createForm.icon" :options="iconOptions" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input
            v-model:value="createForm.description"
            type="textarea"
            placeholder="简要说明这个应用服务什么场景"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="createModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="createApplication">创建</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import { ApiOutlined, AppstoreOutlined, ExperimentOutlined, MessageOutlined, RobotOutlined } from '@vicons/antd';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    getAiApplications,
    getTenantAiQuota,
    saveAiApplication,
    type AiApplication,
    type AiQuota,
  } from '@/api/aiStudio';

  const router = useRouter();
  const message = useMessage();
  const loading = ref(false);
  const creating = ref(false);
  const keyword = ref('');
  const statusFilter = ref('all');
  const createModalVisible = ref(false);
  const applications = ref<AiApplication[]>([]);
  const quota = ref<AiQuota | null>(null);
  const createForm = reactive({
    name: '',
    icon: 'robot',
    description: '',
  });

  const iconMap = {
    robot: RobotOutlined,
    chat: MessageOutlined,
    workflow: AppstoreOutlined,
    experiment: ExperimentOutlined,
    api: ApiOutlined,
  };

  const iconOptions = [
    { label: '助手', value: 'robot' },
    { label: '对话', value: 'chat' },
    { label: '流程', value: 'workflow' },
    { label: '实验', value: 'experiment' },
    { label: '接口', value: 'api' },
  ];

  const statusOptions = [
    { label: '全部状态', value: 'all' },
    { label: '草稿', value: 'draft' },
    { label: '已发布', value: 'published' },
  ];

  const appCount = computed(() => quota.value?.usage?.applications ?? applications.value.length);
  const quotaReached = computed(() => !!quota.value && appCount.value >= quota.value.max_applications);
  const filteredApplications = computed(() => {
    const q = keyword.value.trim().toLowerCase();
    return applications.value.filter((app) => {
      const statusMatched = statusFilter.value === 'all' || app.status === statusFilter.value;
      const keywordMatched = !q || `${app.name} ${app.app_key}`.toLowerCase().includes(q);
      return statusMatched && keywordMatched;
    });
  });

  const studioPage = computed(() =>
    defineListPage<AiApplication>({
      id: 'ai.studio',
      title: 'AI Studio',
      description: '构建、调试并发布租户级 AI 应用。',
      variant: 'dense-data',
      density: 'compact',
      toolbar: {
        primaryAction: {
          key: 'create-application',
          label: '创建应用',
          type: 'primary',
          disabled: quotaReached.value,
          onClick: openCreateModal,
        },
        rightTools: ['refresh'],
      },
      view: {
        type: 'card-list',
        itemKey: 'app_key',
        cardMinWidth: '320px',
      },
      pagination: { pageSize: 12 },
    })
  );

  function openCreateModal() {
    if (quotaReached.value) {
      message.warning('当前租户应用数量已达上限');
      return;
    }
    createForm.name = '';
    createForm.icon = 'robot';
    createForm.description = '';
    createModalVisible.value = true;
  }

  async function createApplication() {
    const name = createForm.name.trim();
    if (!name) {
      message.warning('请填写应用名称');
      return;
    }
    creating.value = true;
    try {
      const appKey = createAppKey(name);
      await saveAiApplication({
        app_key: appKey,
        name,
        icon: createForm.icon,
        description: createForm.description.trim(),
        app_type: 'single_turn_generation',
        status: 'draft',
        endpoint_slug: appKey,
        system_prompt: '你是一个专业、简洁的助手。',
        developer_prompt: '',
        user_prompt_template: '请回答：{{question}}',
        variables_schema: { type: 'object', required: ['question'] },
        output_schema: {},
        model_preferences: { model: 'dashscope.qwen-plus', temperature: 0.2 },
        auth_policy: {},
        quota_policy: {},
        trace_policy: { enabled: true },
        runtime_config: { icon: createForm.icon },
      });
      message.success('应用已创建');
      createModalVisible.value = false;
      await reload();
    } finally {
      creating.value = false;
    }
  }

  function openDetail(app: AiApplication) {
    router.push({ name: 'ai-studio-app-detail', params: { appKey: app.app_key } });
  }

  async function reload() {
    loading.value = true;
    try {
      const [appPayload, quotaPayload] = await Promise.all([getAiApplications(), getTenantAiQuota()]);
      applications.value = appPayload.items || [];
      quota.value = quotaPayload;
    } finally {
      loading.value = false;
    }
  }

  function appIcon(app: AiApplication) {
    const key = String(app.runtime_config?.icon || 'robot') as keyof typeof iconMap;
    return iconMap[key] || RobotOutlined;
  }

  function appTypeLabel(type: string) {
    return type === 'single_turn_generation' ? '单轮生成' : type;
  }

  function formatAppTime(value?: string) {
    return formatToDateTime(value || '') || '-';
  }

  function createAppKey(name: string) {
    const normalized = name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
    return `${normalized || 'single-turn'}-${Date.now().toString(36)}`;
  }

  onMounted(reload);
</script>

<style lang="less" scoped>
  .ai-studio-page {
    min-width: 0;
  }

  .ai-studio-page__search {
    width: 280px;
  }

  .ai-studio-page__status {
    width: 140px;
  }

  .ai-app-card {
    display: grid;
    gap: 12px;
    min-height: 164px;
    padding: 14px;
    cursor: pointer;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius);
    transition:
      border-color 0.18s ease,
      box-shadow 0.18s ease,
      transform 0.18s ease;
  }

  .ai-app-card:hover,
  .ai-app-card:focus-visible {
    border-color: var(--app-primary-color);
    box-shadow: 0 0 0 2px var(--app-primary-soft-bg);
    transform: translateY(-1px);
    outline: none;
  }

  .ai-app-card__header,
  .ai-app-card__identity,
  .ai-app-card__footer {
    display: flex;
    gap: 12px;
  }

  .ai-app-card__header {
    align-items: flex-start;
    justify-content: space-between;
  }

  .ai-app-card__identity {
    min-width: 0;
    align-items: center;
  }

  .ai-app-card__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    flex: 0 0 auto;
    color: var(--app-primary-color);
    background: var(--app-primary-soft-bg);
    border-radius: 8px;
  }

  .ai-app-card__header h3 {
    margin: 0;
    overflow: hidden;
    font-size: 16px;
    font-weight: 650;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ai-app-card__header span,
  .ai-app-card p,
  .ai-app-card__footer {
    color: var(--app-text-color-2);
  }

  .ai-app-card p {
    min-height: 42px;
    margin: 0;
    line-height: 1.5;
  }

  .ai-app-card__footer {
    justify-content: space-between;
    font-size: 12px;
  }

  .ai-create-form {
    padding-top: 4px;
  }

  @media (max-width: 900px) {
    .ai-studio-page__search,
    .ai-studio-page__status {
      width: 100%;
    }
  }
</style>
