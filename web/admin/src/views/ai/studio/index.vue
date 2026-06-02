<template>
  <div class="ai-studio-page">
    <ListPageRuntime :schema="studioPage" :rows="activeRows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload" @filter-reset="resetFilters">
      <template v-if="showViewSwitch" #toolbar-left>
        <n-radio-group v-model:value="activeView" size="small" class="ai-studio-page__views">
          <n-radio-button v-if="canReadApplications" value="applications">AI 应用</n-radio-button>
          <n-radio-button v-if="canReadCapabilities" value="capabilities">AI 能力</n-radio-button>
        </n-radio-group>
      </template>

      <template #filters="{ submit }">
        <n-input v-model:value="keyword" clearable :placeholder="searchPlaceholder" @keyup.enter="submit" />
        <n-select
          v-if="currentView === 'applications'"
          v-model:value="statusFilter"
          :options="statusOptions"
          @update:value="submit"
        />
        <n-select
          v-else
          v-model:value="capabilityStatusFilter"
          :options="capabilityStatusOptions"
          @update:value="submit"
        />
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
        <n-form-item label="应用类型" required>
          <n-select v-model:value="createForm.app_type" :options="appTypeOptions" placeholder="请选择应用类型" />
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

    <n-modal
      v-model:show="capabilityModalVisible"
      preset="card"
      :title="isPlatformCapabilityPage ? '创建平台AI能力' : '创建能力'"
      class="ai-create-modal"
      :style="{ width: 'min(560px, calc(100vw - 32px))' }"
    >
      <n-form label-placement="top" class="ai-create-form">
        <n-form-item label="能力 Key" required>
          <n-input v-model:value="capabilityForm.capability_key" placeholder="例如：summarize" />
        </n-form-item>
        <n-form-item label="能力名称" required>
          <n-input v-model:value="capabilityForm.name" placeholder="例如：摘要生成" />
        </n-form-item>
        <n-form-item label="图标">
          <n-select v-model:value="capabilityForm.icon" :options="iconOptions" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input
            v-model:value="capabilityForm.description"
            type="textarea"
            placeholder="简要说明这个能力服务什么内部场景"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="capabilityModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="creatingCapability" @click="createCapability">创建</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, onMounted, reactive, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { NButton, NSpace, NTag, useMessage, type DataTableColumns } from 'naive-ui';
  import { ApiOutlined, AppstoreOutlined, ExperimentOutlined, MessageOutlined, RobotOutlined } from '@vicons/antd';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { useUser } from '@/store/modules/user';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    getAiCapabilities,
    getAiCapabilityModelOptions,
    getAiApplications,
    getPlatformAiCapabilities,
    getTenantAiQuota,
    saveAiCapability,
    saveAiApplication,
    savePlatformAiCapability,
    type AiCapability,
    type AiApplication,
    type AiQuota,
  } from '@/api/aiStudio';

  const route = useRoute();
  const router = useRouter();
  const message = useMessage();
  const { hasPermission } = usePermission();
  const userStore = useUser();
  const loading = ref(false);
  const creating = ref(false);
  const creatingCapability = ref(false);
  const keyword = ref('');
  const statusFilter = ref('all');
  const capabilityStatusFilter = ref('all');
  const activeView = ref<'applications' | 'capabilities'>('applications');
  const createModalVisible = ref(false);
  const capabilityModalVisible = ref(false);
  const applications = ref<AiApplication[]>([]);
  const applicationTotal = ref(0);
  const models = ref<Recordable[]>([]);
  const capabilities = ref<AiCapability[]>([]);
  const capabilityTotal = ref(0);
  const quota = ref<AiQuota | null>(null);
  const createForm = reactive({
    name: '',
    icon: 'robot',
    app_type: 'single_turn_generation',
    description: '',
  });
  const capabilityForm = reactive({
    capability_key: '',
    name: '',
    icon: 'api',
    description: '',
    scope: 'tenant',
  });

  const isPlatformCapabilityPage = computed(() => {
    const routeName = String(route.name || '');
    const activeMenu = String(route.meta?.activeMenu || '');
    return routeName === 'ai-platform-capabilities' || activeMenu === 'ai-platform-capabilities';
  });
  const currentView = computed<'applications' | 'capabilities'>(() =>
    isPlatformCapabilityPage.value ? 'capabilities' : activeView.value
  );
  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);
  const canReadApplications = computed(
    () => !isPlatformCapabilityPage.value && hasPermission(['ai_applications:read'])
  );
  const canManageApplications = computed(
    () => !isPlatformCapabilityPage.value && hasPermission(['ai_applications:manage'])
  );
  const canReadCapabilities = computed(() =>
    hasPermission(['ai_capabilities:read']) || hasPermission(['ai_capabilities:platform_manage'])
  );
  const canManageCapabilities = computed(() =>
    hasPermission(['ai_capabilities:manage']) || hasPermission(['ai_capabilities:platform_manage'])
  );
  const canManagePlatformCapabilities = computed(() => isPlatformAdmin.value);
  const showViewSwitch = computed(
    () => !isPlatformCapabilityPage.value && canReadApplications.value && canReadCapabilities.value
  );

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
  const appTypeOptions = [
    { label: '\u5355\u8f6e\u5bf9\u8bdd', value: 'single_turn_generation' },
    { label: 'Workflow', value: 'workflow' },
    { label: 'Agent', value: 'agent' },
  ];
  const capabilityStatusOptions = [
    { label: '全部状态', value: 'all' },
    { label: '启用', value: 'enabled' },
    { label: '停用', value: 'disabled' },
  ];
  const appCount = computed(() => quota.value?.usage?.applications ?? applications.value.length);
  const capabilityCount = computed(() => quota.value?.usage?.capabilities ?? capabilities.value.length);
  const quotaReached = computed(() => !!quota.value && appCount.value >= quota.value.max_applications);
  const capabilityQuotaReached = computed(
    () =>
      !isPlatformCapabilityPage.value &&
      !!quota.value &&
      capabilityCount.value >= quota.value.max_capabilities
  );
  const searchPlaceholder = computed(() =>
    currentView.value === 'applications' ? '搜索应用名称或 Key' : '搜索能力 Key、名称或模型'
  );
  const activeRows = computed(() =>
    currentView.value === 'applications' ? applications.value : capabilities.value
  );
  const paginationTotal = computed(() =>
    currentView.value === 'applications' ? applicationTotal.value : capabilityTotal.value
  );
  const modelOptions = computed(() =>
    models.value.map((item) => ({
      label: `${item.display_name || item.model_name || item.model_key} (${item.model_key})`,
      value: item.model_key,
    }))
  );

  const capabilityColumns = computed<DataTableColumns<AiCapability>>(() => [
    {
      title: '能力 Key',
      key: 'capability_key',
      width: 180,
      render: (row) => h('strong', { class: 'ai-capability-key' }, row.capability_key),
    },
    { title: '名称', key: 'name', width: 180 },
    {
      title: '模型或路由',
      key: 'model',
      minWidth: 220,
      render: (row) => String(row.model_preferences?.model || row.model_preferences?.route_key || '-'),
    },
    {
      title: 'Scope',
      key: 'scope',
      width: 100,
      render: (row) =>
        h(
          NTag,
          { size: 'small', type: row.scope === 'platform' ? 'info' : 'default' },
          { default: () => (row.scope === 'platform' ? '平台' : '租户') }
        ),
    },
    {
      title: '状态',
      key: 'enabled',
      width: 100,
      render: (row) =>
        h(
          NTag,
          { size: 'small', type: row.enabled ? 'success' : 'default' },
          { default: () => (row.enabled ? '启用' : '停用') }
        ),
    },
    { title: '调用方式', key: 'call_method', width: 170 },
    {
      title: '更新时间',
      key: 'update_time',
      width: 170,
      render: (row) => formatAppTime(row.update_time || row.create_time),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (row) =>
        h(NSpace, { size: 4 }, () => [
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              type: 'primary',
              onClick: () => openCapabilityDetail(row),
            },
            { default: () => '配置' }
          ),
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              onClick: () => copyCapabilityCall(row),
            },
            { default: () => '复制调用' }
          ),
        ]),
    },
  ]);

  const studioPage = computed(() =>
    defineListPage<AiApplication | AiCapability>({
      id: 'ai.studio',
      title: isPlatformCapabilityPage.value ? '平台AI能力' : 'AI Studio',
      description: isPlatformCapabilityPage.value
        ? '统一管理平台内置 AI 能力，租户可直接启用或覆盖配置。'
        : '统一管理 AI 应用与平台内部 AI 能力。',
      variant: 'dense-data',
      density: 'compact',
      toolbar: {
        primaryAction:
          currentView.value === 'applications'
            ? canManageApplications.value
              ? {
                  key: 'create-application',
                  label: '创建应用',
                  type: 'primary',
                  disabled: quotaReached.value,
                  onClick: openCreateModal,
                }
              : undefined
            : canManageCapabilities.value || canManagePlatformCapabilities.value
              ? {
                  key: 'create-capability',
                  label: '创建能力',
                  type: 'primary',
                  disabled: capabilityQuotaReached.value,
                  onClick: openCapabilityModal,
                }
              : undefined,
        batchActions: [],
        rightTools: ['refresh'],
      },
      filterBar: { showSubmit: true, showReset: true },
      view:
        currentView.value === 'applications'
          ? {
              type: 'card-list',
              itemKey: 'app_key',
              cardMinWidth: '320px',
              sort: { remote: true },
            }
          : {
              type: 'table',
              rowKey: 'capability_key',
              columns: capabilityColumns.value as DataTableColumns<AiApplication | AiCapability>,
              selectable: false,
              scrollX: 1180,
              sort: { remote: true },
              columnRuntime: {
                columns: [
                  { key: 'capability_key', sortable: true },
                  { key: 'name', sortable: true },
                  { key: 'model', sortable: false },
                  { key: 'scope', sortable: true },
                  { key: 'enabled', sortable: true },
                  { key: 'call_method', sortable: true },
                  { key: 'update_time', sortable: true },
                  { key: 'actions', required: true, sortable: false },
                ],
              },
              tableLayout: { rowDensity: 'medium', maxHeight: 'calc(100vh - 360px)' },
            },
      pagination: { pageSize: currentView.value === 'applications' ? 12 : 20 },
    })
  );

  function openCreateModal() {
    if (isPlatformCapabilityPage.value) {
      return;
    }
    if (quotaReached.value) {
      message.warning('当前租户应用数量已达上限');
      return;
    }
    createForm.name = '';
    createForm.icon = 'robot';
    createForm.app_type = 'single_turn_generation';
    createForm.description = '';
    createModalVisible.value = true;
  }

  function openCapabilityModal() {
    if (capabilityQuotaReached.value) {
      message.warning('当前租户能力数量已达上限');
      return;
    }
    capabilityForm.capability_key = '';
    capabilityForm.name = '';
    capabilityForm.icon = 'api';
    capabilityForm.description = '';
    capabilityForm.scope = isPlatformCapabilityPage.value ? 'platform' : 'tenant';
    capabilityModalVisible.value = true;
  }

  async function createCapability() {
    const capabilityKey = capabilityForm.capability_key.trim();
    const name = capabilityForm.name.trim();
    if (!capabilityKey || !name) {
      message.warning('请填写能力 Key 和名称');
      return;
    }
    creatingCapability.value = true;
    try {
      const payload = {
        capability_key: capabilityKey,
        name,
        description: capabilityForm.description.trim(),
        scope: capabilityForm.scope,
        binding_type: 'prompt_runtime',
        binding_key: capabilityKey,
        call_method: 'aiService.execute',
        system_prompt: '',
        user_prompt_template: '',
        input_schema: {},
        output_schema: {},
        model_preferences: {},
        runtime_config: { icon: capabilityForm.icon },
        enabled: true,
      };
      await (capabilityForm.scope === 'platform' ? savePlatformAiCapability(payload) : saveAiCapability(payload));
      message.success('能力已创建');
      capabilityModalVisible.value = false;
      await reload();
    } finally {
      creatingCapability.value = false;
    }
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
      const isWorkflowApp = createForm.app_type === 'workflow';
      const isAgentApp = createForm.app_type === 'agent';
      await saveAiApplication({
        app_key: appKey,
        name,
        icon: createForm.icon,
        description: createForm.description.trim(),
        app_type: createForm.app_type,
        status: 'draft',
        endpoint_slug: appKey,
        system_prompt: isWorkflowApp ? '' : '\u4f60\u662f\u4e00\u4e2a\u4e13\u4e1a\u3001\u7b80\u6d01\u7684\u52a9\u624b\u3002',
        developer_prompt: '',
        user_prompt_template: isWorkflowApp || isAgentApp ? '' : '\u8bf7\u56de\u7b54\uff1a{{question}}',
        variables_schema:
          isWorkflowApp || isAgentApp ? { type: 'object', required: [] } : { type: 'object', required: ['question'] },
        output_schema: {},
        model_preferences: isWorkflowApp ? {} : { model: 'dashscope.qwen-plus', temperature: 0.2 },
        auth_policy: {},
        quota_policy: {},
        trace_policy: { enabled: true },
        runtime_config: {
          icon: createForm.icon,
          ...(isWorkflowApp ? { workflow: defaultWorkflowDefinition() } : {}),
          ...(isAgentApp ? { agent: { history_limit: 20 } } : {}),
        },
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

  function openCapabilityDetail(capability: AiCapability) {
    router.push({
      name: isPlatformCapabilityPage.value ? 'ai-platform-capability-detail' : 'ai-studio-capability-detail',
      params: { capabilityKey: capability.capability_key },
    });
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const listParams = runtimeListParams(state, { pageSize: currentView.value === 'applications' ? 12 : 20 });
      const appParams = {
        ...listParams,
        keyword: keyword.value.trim() || undefined,
        status: statusFilter.value === 'all' ? undefined : statusFilter.value,
      };
      const capabilityParams = {
        ...listParams,
        keyword: keyword.value.trim() || undefined,
        status: capabilityStatusFilter.value === 'all' ? undefined : capabilityStatusFilter.value,
      };
      const tasks: Promise<unknown>[] = isPlatformCapabilityPage.value ? [] : [getTenantAiQuota()];
      applications.value = canReadApplications.value ? applications.value : [];
      capabilities.value = canReadCapabilities.value ? capabilities.value : [];
      if (canReadApplications.value) {
        tasks.push(getAiApplications(currentView.value === 'applications' ? appParams : { page: 1, page_size: 20 }));
      }
      if (canManageCapabilities.value) {
        tasks.push(getAiCapabilityModelOptions());
      }
      if (canReadCapabilities.value) {
        tasks.push(
          isPlatformCapabilityPage.value || isPlatformAdmin.value
            ? getPlatformAiCapabilities(currentView.value === 'capabilities' ? capabilityParams : { page: 1, page_size: 20 })
            : getAiCapabilities(currentView.value === 'capabilities' ? capabilityParams : { page: 1, page_size: 20 })
        );
      }
      const payloads = await Promise.all(tasks);
      let payloadIndex = 0;
      if (isPlatformCapabilityPage.value) {
        quota.value = null;
      } else {
        quota.value = payloads[payloadIndex++] as AiQuota;
      }
      if (canReadApplications.value) {
        const appPayload = payloads[payloadIndex++] as { items?: AiApplication[]; pagination?: { total?: number } };
        applications.value = appPayload.items || [];
        applicationTotal.value = appPayload.pagination?.total || applications.value.length;
      }
      if (canManageCapabilities.value) {
        const modelPayload = payloads[payloadIndex++] as { items?: Recordable[] };
        models.value = modelPayload.items || [];
      }
      if (canReadCapabilities.value) {
        const capabilityPayload = payloads[payloadIndex++] as { items?: AiCapability[]; pagination?: { total?: number } };
        capabilities.value = capabilityPayload.items || [];
        capabilityTotal.value = capabilityPayload.pagination?.total || capabilities.value.length;
      }
    } finally {
      loading.value = false;
    }
  }

  function resetFilters() {
    keyword.value = '';
    statusFilter.value = 'all';
    capabilityStatusFilter.value = 'all';
  }

  function appIcon(app: AiApplication) {
    const key = String(app.runtime_config?.icon || 'robot') as keyof typeof iconMap;
    return iconMap[key] || RobotOutlined;
  }

  function appTypeLabel(type: string) {
    if (type === 'single_turn_generation') return '\u5355\u8f6e\u5bf9\u8bdd';
    if (type === 'workflow') return 'Workflow';
    if (type === 'agent') return 'Agent';
    return type;
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
    const fallbackKey = createForm.app_type === 'workflow' ? 'workflow' : createForm.app_type === 'agent' ? 'agent' : 'single-turn';
    return `${normalized || fallbackKey}-${Date.now().toString(36)}`;
  }

  function defaultWorkflowDefinition() {
    return {
      nodes: [
        { id: 'start', type: 'start', data: { label: '开始' }, position: { x: 80, y: 160 } },
        {
          id: 'llm_1',
          type: 'llm',
          data: {
            label: 'LLM',
            model: 'dashscope.qwen-plus',
            system_prompt: '你是一个专业、简洁的助手。',
            user_prompt_template: '请回答：{{question}}',
            output_key: 'answer',
          },
          position: { x: 360, y: 120 },
        },
        { id: 'end', type: 'end', data: { label: '结束', output: '{{answer}}' }, position: { x: 660, y: 160 } },
      ],
      edges: [
        { id: 'start-llm_1', source: 'start', target: 'llm_1' },
        { id: 'llm_1-end', source: 'llm_1', target: 'end' },
      ],
    };
  }

  async function copyCapabilityCall(row: AiCapability) {
    const snippet = `aiService.execute("${row.capability_key}", variables)`;
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(snippet);
    }
    message.success('调用方式已复制');
  }

  watch(
    [canReadApplications, canReadCapabilities, isPlatformCapabilityPage],
    () => {
      if (isPlatformCapabilityPage.value) {
        activeView.value = 'capabilities';
        return;
      }
      if (activeView.value === 'applications' && !canReadApplications.value && canReadCapabilities.value) {
        activeView.value = 'capabilities';
      }
      if (activeView.value === 'capabilities' && !canReadCapabilities.value && canReadApplications.value) {
        activeView.value = 'applications';
      }
    },
    { immediate: true }
  );

  watch([currentView], () => {
    reload();
  });

  onMounted(reload);
</script>

<style lang="less" scoped>
  .ai-studio-page {
    min-width: 0;
  }

  .ai-studio-page__views {
    min-width: 220px;
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

  :deep(.ai-capability-key) {
    font-weight: 650;
  }

  :deep(.ai-capability-binding) {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  :deep(.ai-capability-binding span),
  :deep(.ai-capability-binding small) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :deep(.ai-capability-binding small) {
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  @media (max-width: 900px) {
  }
</style>
