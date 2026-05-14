<template>
  <div class="prompt-library-page">
    <ListPageRuntime :schema="pageSchema" :rows="filteredRows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索名称、Key、说明" class="prompt-library-page__keyword" />
        <n-select v-model:value="statusFilter" clearable placeholder="状态" :options="assetStatusOptions" class="prompt-library-page__select" />
        <n-select v-model:value="categoryFilter" clearable placeholder="分类" :options="categoryOptions" class="prompt-library-page__select" />
        <n-select v-model:value="ownerFilter" clearable placeholder="归属上下文" :options="ownerOptions" class="prompt-library-page__select" />
      </template>

      <template #item="{ row }">
        <article class="prompt-card">
          <header class="prompt-card__header">
            <div class="prompt-card__title">
              <span class="prompt-card__category">{{ row.category || 'general' }}</span>
              <h3>{{ row.name }}</h3>
            </div>
            <AppStatusTag :tone="assetStatusTone(row.status)" :label="assetStatusLabel(row.status)" />
          </header>

          <p class="prompt-card__key">{{ row.prompt_key }}</p>
          <p class="prompt-card__description">{{ row.description || '暂无说明' }}</p>

          <div class="prompt-card__tags">
            <n-tag v-for="tag in row.tags || []" :key="tag" size="small" round>{{ tag }}</n-tag>
            <span v-if="!(row.tags || []).length" class="prompt-card__muted">未设置标签</span>
          </div>

          <dl class="prompt-card__facts">
            <div>
              <dt>版本</dt>
              <dd>{{ row.version_count || 0 }}</dd>
            </div>
            <div>
              <dt>绑定</dt>
              <dd>{{ row.binding_count || 0 }}</dd>
            </div>
            <div>
              <dt>范围</dt>
              <dd>{{ visibilityLabel(row.visibility) }}</dd>
            </div>
          </dl>

          <footer class="prompt-card__footer">
            <span>{{ row.owner_context || 'general' }} · {{ formatToDateTime(row.update_time || row.create_time || '') || '-' }}</span>
            <div class="prompt-card__actions">
              <n-button size="tiny" quaternary @click="openVersions(row)">版本</n-button>
              <n-button v-if="canManage" size="tiny" quaternary @click="openEdit(row)">编辑</n-button>
              <n-button v-if="canManage" size="tiny" quaternary type="error" @click="remove(row)">归档</n-button>
            </div>
          </footer>
        </article>
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="assetDrawerVisible" width="560">
      <n-drawer-content :title="assetForm.id ? '编辑提示词' : '新建提示词'">
        <n-form ref="assetFormRef" :model="assetForm" :rules="assetRules" label-placement="top">
          <n-form-item label="Prompt Key" path="prompt_key">
            <n-input v-model:value="assetForm.prompt_key" placeholder="voice_analysis.transcript.summary" />
          </n-form-item>
          <n-form-item label="名称" path="name">
            <n-input v-model:value="assetForm.name" placeholder="会议纪要提取" />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="分类">
              <n-input v-model:value="assetForm.category" placeholder="analysis" />
            </n-form-item-gi>
            <n-form-item-gi label="归属上下文">
              <n-input v-model:value="assetForm.owner_context" placeholder="voice_analysis" />
            </n-form-item-gi>
            <n-form-item-gi label="可见性">
              <n-select v-model:value="assetForm.visibility" :options="visibilityOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="状态">
              <n-select v-model:value="assetForm.status" :options="assetStatusOptions" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="标签">
            <n-dynamic-tags v-model:value="assetForm.tags" />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="assetForm.description" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="assetDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submitAsset">保存</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="versionDrawerVisible" width="860">
      <n-drawer-content :title="selectedPrompt ? `${selectedPrompt.name} · 版本` : '提示词版本'">
        <div class="version-workbench">
          <section class="version-list">
            <div v-for="version in versions" :key="version.id" class="version-row">
              <div>
                <strong>{{ version.version }}</strong>
                <span>{{ formatToDateTime(version.update_time || version.create_time || '') || '-' }}</span>
              </div>
              <AppStatusTag :tone="versionStatusTone(version.status)" :label="versionStatusLabel(version.status)" />
              <n-space size="small">
                <n-button size="tiny" quaternary @click="openVersionForm(version)">编辑</n-button>
                <n-button v-if="canManage && version.status !== 'published'" size="tiny" quaternary type="primary" @click="publishVersion(version)">发布</n-button>
                <n-button v-if="canManage && version.status === 'published'" size="tiny" quaternary type="warning" @click="deprecateVersion(version)">废弃</n-button>
              </n-space>
            </div>
            <n-empty v-if="!versions.length" description="还没有版本" />
          </section>

          <section class="version-editor">
            <div class="version-editor__header">
              <h3>{{ versionForm.id ? '编辑版本' : '新建版本' }}</h3>
              <n-button size="small" tertiary @click="resetVersionForm">清空</n-button>
            </div>
            <n-form label-placement="top">
              <n-form-item label="版本号">
                <n-input v-model:value="versionForm.version" placeholder="1.0.0" />
              </n-form-item>
              <n-form-item label="System Prompt">
                <n-input v-model:value="versionForm.system_prompt" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
              </n-form-item>
              <n-form-item label="Developer Prompt">
                <n-input v-model:value="versionForm.developer_prompt" type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" />
              </n-form-item>
              <n-form-item label="User Prompt Template">
                <n-input v-model:value="versionForm.user_prompt_template" type="textarea" :autosize="{ minRows: 5, maxRows: 10 }" />
              </n-form-item>
              <n-grid :cols="2" :x-gap="16" responsive="screen">
                <n-form-item-gi label="变量 Schema JSON">
                  <n-input v-model:value="variablesSchemaText" type="textarea" :autosize="{ minRows: 5, maxRows: 9 }" />
                </n-form-item-gi>
                <n-form-item-gi label="输出 Schema JSON">
                  <n-input v-model:value="outputSchemaText" type="textarea" :autosize="{ minRows: 5, maxRows: 9 }" />
                </n-form-item-gi>
              </n-grid>
              <n-space justify="end">
                <n-button type="primary" :loading="saving" :disabled="!canManage" @click="submitVersion">保存版本</n-button>
              </n-space>
            </n-form>
          </section>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deletePromptAsset,
    deprecatePromptVersion,
    getPromptAssets,
    getPromptVersions,
    publishPromptVersion,
    savePromptAsset,
    savePromptVersion,
    type PromptAsset,
    type PromptVersion,
  } from '@/api/aiAssets';

  type PromptAssetForm = Partial<PromptAsset> & { tags: string[] };
  type PromptVersionForm = Partial<PromptVersion>;

  const message = useMessage();
  const { hasPermission } = usePermission();
  const canManage = computed(() => hasPermission(['prompt:assets:manage']));
  const loading = ref(false);
  const saving = ref(false);
  const rows = ref<PromptAsset[]>([]);
  const versions = ref<PromptVersion[]>([]);
  const selectedPrompt = ref<PromptAsset | null>(null);
  const keyword = ref('');
  const statusFilter = ref<string | null>(null);
  const categoryFilter = ref<string | null>(null);
  const ownerFilter = ref<string | null>(null);
  const assetDrawerVisible = ref(false);
  const versionDrawerVisible = ref(false);
  const assetFormRef = ref<FormInst | null>(null);
  const variablesSchemaText = ref('{}');
  const outputSchemaText = ref('{}');

  const assetForm = reactive<PromptAssetForm>({
    prompt_key: '',
    name: '',
    description: '',
    category: 'general',
    tags: [],
    owner_context: 'general',
    visibility: 'tenant',
    status: 'draft',
  });

  const versionForm = reactive<PromptVersionForm>({
    version: '',
    system_prompt: '',
    developer_prompt: '',
    user_prompt_template: '',
    render_engine: 'simple',
    status: 'draft',
  });

  const assetRules: FormRules = {
    prompt_key: [{ required: true, message: '请输入 Prompt Key', trigger: ['blur', 'input'] }],
    name: [{ required: true, message: '请输入名称', trigger: ['blur', 'input'] }],
  };

  const assetStatusOptions: SelectOption[] = [
    { label: '草稿', value: 'draft' },
    { label: '评审中', value: 'reviewing' },
    { label: '已发布', value: 'published' },
    { label: '已归档', value: 'archived' },
  ];
  const visibilityOptions: SelectOption[] = [
    { label: '私有', value: 'private' },
    { label: '租户', value: 'tenant' },
    { label: '平台', value: 'platform' },
  ];

  const categoryOptions = computed<SelectOption[]>(() => uniqueOptions(rows.value.map((row) => row.category)));
  const ownerOptions = computed<SelectOption[]>(() => uniqueOptions(rows.value.map((row) => row.owner_context)));
  const filteredRows = computed(() => {
    const text = keyword.value.trim().toLowerCase();
    return rows.value.filter((row) => {
      const matchesKeyword =
        !text ||
        row.name.toLowerCase().includes(text) ||
        row.prompt_key.toLowerCase().includes(text) ||
        row.description.toLowerCase().includes(text);
      return (
        matchesKeyword &&
        (!statusFilter.value || row.status === statusFilter.value) &&
        (!categoryFilter.value || row.category === categoryFilter.value) &&
        (!ownerFilter.value || row.owner_context === ownerFilter.value)
      );
    });
  });

  const pageSchema = computed(() => defineListPage<PromptAsset>({
    id: 'prompts.library',
    title: '提示词库',
    description: '以卡片方式维护可版本化、可绑定、可测试的提示词资产。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'card-list',
      itemKey: (row) => row.id,
      cardMinWidth: '300px',
    },
    toolbar: {
      primaryAction: canManage.value
        ? { key: 'create', label: '新建提示词', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 12, pageSizes: [12, 24, 48], showSizePicker: true },
  }));

  function uniqueOptions(values: string[]) {
    return Array.from(new Set(values.filter(Boolean))).map((value) => ({ label: value, value }));
  }

  function resetAssetForm() {
    Object.assign(assetForm, {
      id: undefined,
      prompt_key: '',
      name: '',
      description: '',
      category: 'general',
      tags: [],
      owner_context: 'general',
      visibility: 'tenant',
      status: 'draft',
    });
    assetFormRef.value?.restoreValidation();
  }

  function openCreate() {
    resetAssetForm();
    assetDrawerVisible.value = true;
  }

  function openEdit(row: PromptAsset) {
    Object.assign(assetForm, { ...row, tags: [...(row.tags || [])] });
    assetDrawerVisible.value = true;
  }

  async function submitAsset() {
    try {
      await assetFormRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      await savePromptAsset(assetForm);
      message.success('提示词已保存');
      assetDrawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function remove(row: PromptAsset) {
    await deletePromptAsset(row.id);
    message.success('提示词已归档');
    await reload();
  }

  async function openVersions(row: PromptAsset) {
    selectedPrompt.value = row;
    resetVersionForm();
    versionDrawerVisible.value = true;
    await loadVersions(row.id);
  }

  async function loadVersions(promptId: number) {
    const payload = await getPromptVersions(promptId);
    versions.value = payload.items || [];
  }

  function resetVersionForm() {
    Object.assign(versionForm, {
      id: undefined,
      version: '',
      system_prompt: '',
      developer_prompt: '',
      user_prompt_template: '',
      render_engine: 'simple',
      status: 'draft',
    });
    variablesSchemaText.value = '{}';
    outputSchemaText.value = '{}';
  }

  function openVersionForm(version: PromptVersion) {
    Object.assign(versionForm, version);
    variablesSchemaText.value = stringifyJson(version.variables_schema || {});
    outputSchemaText.value = stringifyJson(version.output_schema || {});
  }

  async function submitVersion() {
    if (!selectedPrompt.value) return;
    const variablesSchema = parseJsonObject(variablesSchemaText.value, '变量 Schema');
    const outputSchema = parseJsonObject(outputSchemaText.value, '输出 Schema');
    if (!variablesSchema || !outputSchema) return;
    saving.value = true;
    try {
      await savePromptVersion(selectedPrompt.value.id, {
        ...versionForm,
        variables_schema: variablesSchema,
        output_schema: outputSchema,
      });
      message.success('版本已保存');
      resetVersionForm();
      await loadVersions(selectedPrompt.value.id);
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function publishVersion(version: PromptVersion) {
    if (!selectedPrompt.value) return;
    await publishPromptVersion(selectedPrompt.value.id, version.id);
    message.success('版本已发布');
    await loadVersions(selectedPrompt.value.id);
    await reload();
  }

  async function deprecateVersion(version: PromptVersion) {
    if (!selectedPrompt.value) return;
    await deprecatePromptVersion(selectedPrompt.value.id, version.id);
    message.success('版本已废弃');
    await loadVersions(selectedPrompt.value.id);
  }

  async function reload() {
    loading.value = true;
    try {
      const payload = await getPromptAssets({ page: 1, page_size: 100 });
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  function stringifyJson(value: unknown) {
    return JSON.stringify(value || {}, null, 2);
  }

  function parseJsonObject(text: string, label: string): Record<string, unknown> | null {
    try {
      const payload = JSON.parse(text || '{}');
      if (!payload || Array.isArray(payload) || typeof payload !== 'object') {
        message.error(`${label} 必须是 JSON object`);
        return null;
      }
      return payload;
    } catch {
      message.error(`${label} 不是合法 JSON`);
      return null;
    }
  }

  function assetStatusLabel(status: string) {
    return ({ draft: '草稿', reviewing: '评审中', published: '已发布', archived: '已归档' } as Record<string, string>)[status] || status;
  }

  function assetStatusTone(status: string) {
    return status === 'published' ? 'success' : status === 'reviewing' ? 'warning' : status === 'archived' ? 'neutral' : 'info';
  }

  function versionStatusLabel(status: string) {
    return ({ draft: '草稿', published: '已发布', deprecated: '已废弃' } as Record<string, string>)[status] || status;
  }

  function versionStatusTone(status: string) {
    return status === 'published' ? 'success' : status === 'deprecated' ? 'neutral' : 'info';
  }

  function visibilityLabel(visibility: string) {
    return ({ private: '私有', tenant: '租户', platform: '平台' } as Record<string, string>)[visibility] || visibility;
  }

  reload();
</script>

<style lang="less" scoped>
  .prompt-library-page {
    min-width: 0;
  }

  .prompt-library-page__keyword {
    width: min(340px, 100%);
  }

  .prompt-library-page__select {
    width: 160px;
  }

  .prompt-card {
    display: grid;
    gap: 12px;
    min-height: 236px;
    padding: 16px;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: 8px;
  }

  .prompt-card__header,
  .prompt-card__footer {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
    min-width: 0;
  }

  .prompt-card__title {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .prompt-card__title h3 {
    margin: 0;
    overflow-wrap: anywhere;
    color: var(--app-text-color);
    font-size: 16px;
    font-weight: 650;
    line-height: 1.35;
    letter-spacing: 0;
  }

  .prompt-card__category,
  .prompt-card__muted,
  .prompt-card__footer {
    color: var(--app-text-color-2);
    font-size: 12px;
    line-height: 1.35;
  }

  .prompt-card__key {
    margin: 0;
    overflow-wrap: anywhere;
    color: var(--app-primary-color);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
  }

  .prompt-card__description {
    display: -webkit-box;
    min-height: 40px;
    margin: 0;
    overflow: hidden;
    color: var(--app-text-color-2);
    font-size: 13px;
    line-height: 1.55;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .prompt-card__tags,
  .prompt-card__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    min-width: 0;
  }

  .prompt-card__facts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin: 0;
  }

  .prompt-card__facts div {
    display: grid;
    gap: 2px;
    min-width: 0;
    padding: 8px;
    background: var(--app-surface-muted-bg);
    border-radius: 6px;
  }

  .prompt-card__facts dt {
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  .prompt-card__facts dd {
    margin: 0;
    overflow: hidden;
    color: var(--app-text-color);
    font-size: 14px;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .prompt-card__footer {
    align-items: center;
    padding-top: 4px;
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 48%, transparent);
  }

  .version-workbench {
    display: grid;
    grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }

  .version-list,
  .version-editor {
    display: grid;
    gap: 10px;
    min-width: 0;
  }

  .version-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    align-items: center;
    padding: 10px;
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: 8px;
  }

  .version-row div {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .version-row strong,
  .version-editor__header h3 {
    margin: 0;
    color: var(--app-text-color);
    font-size: 14px;
    font-weight: 650;
  }

  .version-row span {
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  .version-row :deep(.n-space) {
    grid-column: 1 / -1;
  }

  .version-editor__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  @media (max-width: 900px) {
    .prompt-card__footer,
    .version-workbench {
      display: grid;
      grid-template-columns: 1fr;
    }
  }
</style>
