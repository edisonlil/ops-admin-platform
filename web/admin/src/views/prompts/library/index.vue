<template>
  <div class="prompt-library-page">
    <ListPageRuntime :schema="pageSchema" :rows="filteredRows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索标题、说明、标签" class="prompt-library-page__keyword" />
        <n-select
          v-model:value="tagFilters"
          multiple
          clearable
          placeholder="标签"
          :options="tagOptions"
          max-tag-count="responsive"
          class="prompt-library-page__tag-select"
        />
        <div class="prompt-status-filter" role="group" aria-label="提示词状态筛选">
          <button
            v-for="option in assetStatusOptions"
            :key="option.value"
            type="button"
            class="prompt-status-filter__item"
            :class="{ 'prompt-status-filter__item--active': statusFilter === option.value }"
            @click="statusFilter = option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <span class="prompt-filter-summary">共 {{ rows.length }} 个，当前显示 {{ filteredRows.length }} 个</span>
      </template>

      <template #item="{ row }">
        <article class="prompt-card">
          <header class="prompt-card__header">
            <div class="prompt-card__title">
              <h3>{{ row.name }}</h3>
            </div>
            <div class="prompt-card__header-actions">
              <AppStatusTag :tone="assetStatusTone(row.status)" :label="assetStatusLabel(row.status)" />
              <n-button v-if="canManage" size="tiny" quaternary :loading="copyingId === row.id" @click="copyPrompt(row)">复制</n-button>
            </div>
          </header>

          <p class="prompt-card__description">{{ row.description || '暂无说明' }}</p>

          <div class="prompt-card__tags">
            <n-tag v-for="tag in row.tags || []" :key="tag" size="small" round>{{ tag }}</n-tag>
            <span v-if="!(row.tags || []).length" class="prompt-card__muted">未设置标签</span>
          </div>

          <footer class="prompt-card__footer">
            <span class="prompt-card__version-count">{{ row.version_count || 0 }} 个版本</span>
            <span>{{ formatToDateTime(row.update_time || row.create_time || '') || '-' }}</span>
            <div class="prompt-card__actions">
              <n-button size="tiny" quaternary @click="openVersions(row)">版本</n-button>
              <n-button v-if="canManage" size="tiny" quaternary @click="openEdit(row)">编辑</n-button>
              <n-button v-if="canManage" size="tiny" quaternary type="error" @click="remove(row)">
                {{ row.status === 'archived' ? '删除' : '归档' }}
              </n-button>
            </div>
          </footer>
        </article>
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="assetDrawerVisible" width="min(1080px, 96vw)">
      <n-drawer-content :title="assetForm.id ? '编辑提示词' : '新增提示词'">
        <n-spin :show="assetFormLoading">
          <n-form ref="assetFormRef" :model="assetForm" :rules="assetRules" label-placement="top" class="prompt-form">
            <n-form-item label="标题" path="name">
              <n-input v-model:value="assetForm.name" placeholder="为你的提示词起个醒目的标题" />
            </n-form-item>
            <n-form-item label="提示词内容" path="prompt_content">
              <div class="prompt-form__prompt-field">
                <n-input
                  v-model:value="assetForm.prompt_content"
                  type="textarea"
                  placeholder="在这里输入你的提示词内容，可以包含具体的指令、上下文要求等"
                  :autosize="{ minRows: 12, maxRows: 18 }"
                />
                <div class="prompt-form__prompt-tools">
                  <n-button quaternary circle title="AI 辅助" @click="showComingSoon">
                    <template #icon>
                      <n-icon><RobotOutlined /></n-icon>
                    </template>
                  </n-button>
                  <n-button quaternary circle title="优化提示词" @click="showComingSoon">
                    <template #icon>
                      <n-icon><HighlightOutlined /></n-icon>
                    </template>
                  </n-button>
                </div>
              </div>
            </n-form-item>
            <p class="prompt-form__hint">提示：使用 <code>&#123;&#123;变量名&#125;&#125;</code> 语法可以创建动态变量</p>
            <n-form-item label="描述">
              <n-input
                v-model:value="assetForm.description"
                type="textarea"
                placeholder="简要描述这个提示词的用途和使用场景"
                :autosize="{ minRows: 2, maxRows: 5 }"
              />
            </n-form-item>
            <n-form-item label="标签">
              <n-select
                v-model:value="assetForm.tags"
                multiple
                filterable
                tag
                clearable
                placeholder="选择或输入标签"
                :options="tagOptions"
              />
            </n-form-item>
            <n-form-item label="版本" path="version">
              <n-input v-model:value="assetForm.version" placeholder="1.0.0" />
            </n-form-item>
          </n-form>
        </n-spin>
        <template #footer>
          <n-space justify="end">
            <n-button @click="assetDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submitAsset">保存</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="versionDrawerVisible" width="min(980px, 96vw)">
      <n-drawer-content :title="selectedPrompt ? `${selectedPrompt.name} · 版本` : '提示词版本'">
        <div class="version-workbench">
          <section class="version-list">
            <article
              v-for="version in versions"
              :key="version.id"
              role="button"
              tabindex="0"
              class="version-row"
              :class="{ 'version-row--active': versionForm.id === version.id }"
              @click="openVersionForm(version)"
              @keydown.enter.prevent="openVersionForm(version)"
              @keydown.space.prevent="openVersionForm(version)"
            >
              <div class="version-row__main">
                <strong>{{ version.version }}</strong>
              </div>
              <AppStatusTag :tone="versionStatusTone(version.status)" :label="versionStatusLabel(version.status)" />
              <span class="version-row__time">{{ formatToDateTime(version.update_time || version.create_time || '') || '-' }}</span>
              <n-space size="small" class="version-row__actions" @click.stop>
                <n-button v-if="canManage && version.status === 'draft'" size="tiny" quaternary type="primary" @click="publishVersion(version)">发布</n-button>
                <n-tooltip v-if="canManage && version.status === 'published'" trigger="hover">
                  <template #trigger>
                    <n-button
                      size="tiny"
                      quaternary
                      type="warning"
                      :disabled="isOnlyPublishedVersion(version)"
                      @click="deprecateVersion(version)"
                    >
                      废弃
                    </n-button>
                  </template>
                  {{ isOnlyPublishedVersion(version) ? '至少保留一个已发布版本；要下架整个提示词请归档资产' : '废弃此版本' }}
                </n-tooltip>
              </n-space>
            </article>
            <n-empty v-if="!versions.length" description="还没有版本" />
          </section>

          <section class="version-editor">
            <div class="version-editor__header">
              <h3>{{ versionForm.id ? '编辑版本' : '新建版本' }}</h3>
              <n-button size="small" tertiary @click="resetVersionForm">清空</n-button>
            </div>
            <n-form label-placement="top" class="version-form">
              <n-form-item label="版本号">
                <n-input v-model:value="versionForm.version" placeholder="1.0.0" :disabled="isVersionReadonly" />
              </n-form-item>
              <n-form-item label="提示词内容">
                <div class="prompt-form__prompt-field">
                  <n-input
                    v-model:value="versionForm.user_prompt_template"
                    type="textarea"
                    placeholder="在这里输入你的提示词内容，可以包含具体的指令、上下文要求等"
                    :autosize="{ minRows: 12, maxRows: 18 }"
                    :disabled="isVersionReadonly"
                  />
                  <div class="prompt-form__prompt-tools">
                    <n-button quaternary circle title="AI 辅助" :disabled="isVersionReadonly" @click="showComingSoon">
                      <template #icon>
                        <n-icon><RobotOutlined /></n-icon>
                      </template>
                    </n-button>
                    <n-button quaternary circle title="优化提示词" :disabled="isVersionReadonly" @click="showComingSoon">
                      <template #icon>
                        <n-icon><HighlightOutlined /></n-icon>
                      </template>
                    </n-button>
                  </div>
                </div>
              </n-form-item>
              <p class="prompt-form__hint">提示：使用 <code>&#123;&#123;变量名&#125;&#125;</code> 语法可以创建动态变量</p>
              <n-space justify="end">
                <n-button type="primary" :loading="saving" :disabled="!canManage || isVersionReadonly" @click="submitVersion">保存版本</n-button>
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
  import { HighlightOutlined, RobotOutlined } from '@vicons/antd';
  import type { FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    copyPromptAsset,
    deletePromptAsset,
    deprecatePromptVersion,
    getPromptAsset,
    getPromptAssets,
    getPromptVersions,
    publishPromptVersion,
    savePromptAsset,
    savePromptVersion,
    type PromptAsset,
    type PromptVersion,
  } from '@/api/aiAssets';

  type PromptAssetForm = Partial<PromptAsset> & {
    tags: string[];
    prompt_content: string;
    version: string;
    version_id?: number;
    version_status: string;
  };
  type PromptVersionForm = Partial<PromptVersion>;

  const message = useMessage();
  const { hasPermission } = usePermission();
  const canManage = computed(() => hasPermission(['prompt:assets:manage']));
  const loading = ref(false);
  const saving = ref(false);
  const copyingId = ref<number | null>(null);
  const assetFormLoading = ref(false);
  const rows = ref<PromptAsset[]>([]);
  const versions = ref<PromptVersion[]>([]);
  const selectedPrompt = ref<PromptAsset | null>(null);
  const keyword = ref('');
  const statusFilter = ref('all');
  const tagFilters = ref<string[]>([]);
  const assetDrawerVisible = ref(false);
  const versionDrawerVisible = ref(false);
  const assetFormRef = ref<FormInst | null>(null);

  const assetForm = reactive<PromptAssetForm>({
    prompt_key: '',
    name: '',
    description: '',
    tags: [],
    status: 'draft',
    prompt_content: '',
    version: '1.0.0',
    version_id: undefined,
    version_status: 'draft',
  });

  const versionForm = reactive<PromptVersionForm>({
    version: '',
    system_prompt: '',
    developer_prompt: '',
    user_prompt_template: '',
    render_engine: 'simple',
    status: 'draft',
  });

  const assetRules = computed<FormRules>(() => ({
    name: [{ required: true, message: '请输入标题', trigger: ['blur', 'input'] }],
    prompt_content: [{ required: true, message: '请输入提示词内容', trigger: ['blur', 'input'] }],
    version: [{ required: true, message: '请输入版本号', trigger: ['blur', 'input'] }],
  }));

  const assetStatusOptions = [
    { label: '全部', value: 'all' },
    { label: '草稿', value: 'draft' },
    { label: '已发布', value: 'published' },
    { label: '已归档', value: 'archived' },
  ];
  const tagOptions = computed<SelectOption[]>(() => uniqueOptions(rows.value.flatMap((row) => row.tags || [])));
  const isVersionReadonly = computed(() => Boolean(versionForm.id && versionForm.status !== 'draft'));
  const filteredRows = computed(() => {
    const text = keyword.value.trim().toLowerCase();
    return rows.value.filter((row) => {
      const tags = row.tags || [];
      const matchesKeyword =
        !text ||
        row.name.toLowerCase().includes(text) ||
        row.description.toLowerCase().includes(text) ||
        tags.some((tag) => tag.toLowerCase().includes(text));
      const matchesStatus = statusFilter.value === 'all' || row.status === statusFilter.value;
      const matchesTags = !tagFilters.value.length || tagFilters.value.some((tag) => tags.includes(tag));
      return (
        matchesKeyword &&
        matchesStatus &&
        matchesTags
      );
    });
  });

  const pageSchema = computed(() => defineListPage<PromptAsset>({
    id: 'prompts.library',
    title: '提示词库',
    description: '以卡片方式维护可版本化、可发布和可归档的提示词资产。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'card-list',
      itemKey: (row) => row.id,
      cardMinWidth: '236px',
    },
    toolbar: {
      primaryAction: canManage.value
        ? { key: 'create', label: '新建提示词', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 12, pageSizes: [6, 12, 24], showSizePicker: true },
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
      tags: [],
      status: 'draft',
      prompt_content: '',
      version: '1.0.0',
      version_id: undefined,
      version_status: 'draft',
    });
    assetFormRef.value?.restoreValidation();
  }

  function openCreate() {
    resetAssetForm();
    assetDrawerVisible.value = true;
  }

  async function openEdit(row: PromptAsset) {
    resetAssetForm();
    Object.assign(assetForm, { ...row, tags: [...(row.tags || [])] });
    assetDrawerVisible.value = true;
    assetFormLoading.value = true;
    try {
      const payload = await getPromptAsset(row.id);
      const editableVersion = selectEditableVersion(payload.versions || []);
      const baseVersion = editableVersion || payload.versions?.[0] || null;
      Object.assign(assetForm, {
        ...payload.item,
        tags: [...(payload.item.tags || [])],
        prompt_content: baseVersion?.user_prompt_template || '',
        version: editableVersion?.version || nextVersionLabel(payload.versions || []),
        version_id: editableVersion?.id,
        version_status: editableVersion?.status || 'draft',
      });
      assetFormRef.value?.restoreValidation();
    } finally {
      assetFormLoading.value = false;
    }
  }

  async function submitAsset() {
    try {
      await assetFormRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      const saved = await savePromptAsset(assetForm);
      await savePromptVersion(saved.item.id, {
        id: assetForm.version_id,
        version: assetForm.version || '1.0.0',
        user_prompt_template: assetForm.prompt_content,
        render_engine: 'simple',
        status: assetForm.version_status || 'draft',
      });
      message.success('提示词已保存');
      assetDrawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  function selectEditableVersion(items: PromptVersion[]) {
    return items.find((item) => item.status === 'draft') || null;
  }

  function nextVersionLabel(items: PromptVersion[]) {
    return items.length ? `${items.length + 1}.0.0` : '1.0.0';
  }

  function showComingSoon() {
    message.info('这个辅助能力还在接入中');
  }

  async function remove(row: PromptAsset) {
    const result = await deletePromptAsset(row.id);
    message.success(result.deleted ? '提示词已删除' : '提示词已归档');
    await reload();
  }

  async function copyPrompt(row: PromptAsset) {
    copyingId.value = row.id;
    try {
      const copied = await copyPromptAsset(row.id);
      message.success(`已复制为「${copied.item.name}」`);
      await reload();
    } finally {
      copyingId.value = null;
    }
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
  }

  function openVersionForm(version: PromptVersion) {
    Object.assign(versionForm, version);
  }

  async function submitVersion() {
    if (!selectedPrompt.value) return;
    if (isVersionReadonly.value) return;
    saving.value = true;
    try {
      const selectedVersion = versions.value.find((item) => item.id === versionForm.id);
      const nextVersion = String(versionForm.version || '').trim();
      const versionChanged = Boolean(selectedVersion && nextVersion && nextVersion !== selectedVersion.version);
      await savePromptVersion(selectedPrompt.value.id, {
        ...versionForm,
        id: versionChanged ? undefined : versionForm.id,
        version: nextVersion,
        system_prompt: '',
        developer_prompt: '',
        variables_schema: {},
        output_schema: {},
        example_inputs: [],
        example_outputs: [],
        model_preferences: {},
        render_engine: 'simple',
        status: 'draft',
      });
      message.success(versionChanged ? '已另存为新版本' : '版本已保存');
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
    if (isOnlyPublishedVersion(version)) {
      message.warning('至少保留一个已发布版本；要下架整个提示词请归档资产');
      return;
    }
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

  function isOnlyPublishedVersion(version: PromptVersion) {
    return version.status === 'published' && versions.value.filter((item) => item.status === 'published').length <= 1;
  }

  reload();
</script>

<style lang="less" scoped>
  .prompt-library-page {
    min-width: 0;
  }

  .prompt-library-page__keyword {
    flex: 0 1 320px;
    min-width: 220px;
  }

  .prompt-library-page__tag-select {
    flex: 0 1 260px;
    min-width: 200px;
  }

  .prompt-status-filter {
    display: inline-flex;
    flex: 0 0 auto;
    min-width: 0;
    padding: 2px;
    background: var(--app-page-bg);
    border: 1px solid var(--app-border-color);
    border-radius: 8px;
  }

  .prompt-status-filter__item {
    min-height: 28px;
    padding: 0 12px;
    color: var(--app-icon-color);
    font: inherit;
    font-size: var(--app-font-size-sm, 13px);
    white-space: nowrap;
    cursor: pointer;
    background: transparent;
    border: 0;
    border-radius: 6px;
    transition:
      color 0.16s ease,
      background 0.16s ease,
      box-shadow 0.16s ease;

    &:hover {
      color: var(--app-text-color);
      background: var(--app-hover-color);
    }
  }

  .prompt-status-filter__item--active {
    color: var(--app-primary-color);
    background: var(--app-surface-bg);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  }

  .prompt-filter-summary {
    margin-left: auto;
    color: var(--app-icon-color);
    font-size: var(--app-font-size-sm, 13px);
    white-space: nowrap;
  }

  .prompt-form {
    display: grid;
    gap: 18px;
    padding-top: 12px;
  }

  .prompt-form__hint {
    margin: -12px 0 2px;
    color: var(--app-text-color-2);
    font-size: 13px;
    line-height: 1.4;
  }

  .prompt-form__prompt-field {
    position: relative;
    width: 100%;
  }

  .prompt-form__prompt-field :deep(.n-input__textarea-el) {
    padding-right: 96px;
  }

  .prompt-form__prompt-tools {
    position: absolute;
    top: 10px;
    right: 12px;
    z-index: 1;
    display: flex;
    gap: 8px;
    color: var(--app-text-color-2);
  }

  .prompt-card {
    display: grid;
    gap: 12px;
    align-content: start;
    min-height: 204px;
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
    display: -webkit-box;
    overflow: hidden;
    overflow-wrap: anywhere;
    color: var(--app-text-color);
    font-size: 16px;
    font-weight: 650;
    line-height: 1.35;
    letter-spacing: 0;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .prompt-card__header-actions {
    display: flex;
    flex: 0 0 auto;
    gap: 8px;
    align-items: center;
    white-space: nowrap;
  }

  .prompt-card__muted,
  .prompt-card__footer {
    color: var(--app-text-color-2);
    font-size: 12px;
    line-height: 1.35;
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

  .prompt-card__footer {
    position: relative;
    align-items: center;
    padding-top: 16px;
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 48%, transparent);
  }

  .prompt-card__version-count {
    position: absolute;
    top: 0;
    right: 0;
    padding-left: 8px;
    transform: translateY(-50%);
    background: var(--app-surface-bg);
    color: var(--app-text-color-2);
    font-size: 12px;
    line-height: 1.35;
    white-space: nowrap;
  }

  .version-workbench {
    display: grid;
    grid-template-columns: minmax(176px, 240px) minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }

  .version-list,
  .version-editor {
    display: grid;
    gap: 10px;
    min-width: 0;
  }

  .version-form {
    display: grid;
    gap: 14px;
  }

  .version-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 4px 8px;
    align-items: center;
    width: 100%;
    padding: 8px 10px;
    text-align: left;
    cursor: pointer;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: 8px;
    transition:
      border-color 0.16s ease,
      background-color 0.16s ease,
      box-shadow 0.16s ease;
  }

  .version-row:hover,
  .version-row:focus-visible {
    border-color: color-mix(in srgb, var(--primary-color, #2f6bff) 52%, var(--app-border-color, #d9e1ec));
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color, #2f6bff) 10%, transparent);
    outline: none;
  }

  .version-row--active {
    background: color-mix(in srgb, var(--primary-color, #2f6bff) 6%, var(--app-surface-bg));
    border-color: color-mix(in srgb, var(--primary-color, #2f6bff) 64%, var(--app-border-color, #d9e1ec));
  }

  .version-row__main {
    display: grid;
    gap: 0;
    min-width: 0;
  }

  .version-row strong,
  .version-editor__header h3 {
    margin: 0;
    color: var(--app-text-color);
    font-size: 14px;
    font-weight: 650;
  }

  .version-row__time {
    grid-column: 1;
    color: var(--app-text-color-2);
    font-size: 12px;
    line-height: 1.25;
  }

  .version-row__actions {
    grid-column: 2;
    grid-row: 2;
    justify-self: end;
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

    .prompt-library-page__keyword,
    .prompt-library-page__tag-select {
      flex-basis: auto;
      width: 100%;
      min-width: 0;
    }

    .prompt-status-filter {
      overflow-x: auto;
    }

    .prompt-filter-summary {
      margin-left: 0;
      white-space: normal;
    }
  }
</style>
