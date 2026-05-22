<template>
  <div class="skill-library-page">
    <ListPageRuntime :schema="pageSchema" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索技能名称、标识或说明" class="skill-library-page__keyword" />
        <n-select
          v-model:value="tagFilters"
          multiple
          clearable
          placeholder="标签"
          :options="tagOptions"
          max-tag-count="responsive"
          class="skill-library-page__tag-select"
        />
        <div class="skill-status-filter" role="group" aria-label="技能状态筛选">
          <button
            v-for="option in assetStatusOptions"
            :key="option.value"
            type="button"
            class="skill-status-filter__item"
            :class="{ 'skill-status-filter__item--active': statusFilter === option.value }"
            @click="statusFilter = option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <span class="skill-filter-summary">共 {{ paginationTotal }} 个</span>
      </template>

      <template #item="{ row }">
        <article class="skill-card">
          <header class="skill-card__header">
            <div>
              <h3>{{ row.name }}</h3>
              <span>{{ row.skill_key }}</span>
            </div>
            <n-tag size="small" :type="assetStatusTagType(row.status)">
              {{ assetStatusLabel(row.status) }}
            </n-tag>
          </header>

          <p class="skill-card__description">{{ row.description || '暂无说明' }}</p>

          <div class="skill-card__tags">
            <n-tag v-for="tag in row.tags || []" :key="tag" size="small" round>{{ tag }}</n-tag>
            <span v-if="!(row.tags || []).length" class="skill-card__muted">未设置标签</span>
          </div>

          <footer class="skill-card__footer">
            <span>{{ row.version_count || 0 }} 个版本</span>
            <span>{{ formatToDateTime(row.update_time || row.create_time || '') || '-' }}</span>
            <div class="skill-card__actions">
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

    <n-drawer v-model:show="uploadDrawerVisible" width="min(1040px, 96vw)">
      <n-drawer-content :title="assetForm.id ? '编辑技能' : '上传技能'">
        <n-form ref="assetFormRef" :model="assetForm" :rules="assetRules" label-placement="top" class="skill-form">
          <template v-if="assetForm.id">
            <n-form-item label="技能名称" path="name">
              <n-input v-model:value="assetForm.name" placeholder="例如：合同审阅助手" />
            </n-form-item>
            <n-form-item label="技能标识">
              <n-input v-model:value="assetForm.skill_key" disabled />
            </n-form-item>
            <n-form-item label="说明">
              <n-input v-model:value="assetForm.description" type="textarea" placeholder="说明这个技能的用途和适用场景" :autosize="{ minRows: 2, maxRows: 4 }" />
            </n-form-item>
            <n-form-item label="标签">
              <n-select v-model:value="assetForm.tags" multiple filterable tag clearable placeholder="选择或输入标签" :options="tagOptions" />
            </n-form-item>
          </template>
          <template v-if="!assetForm.id">
            <n-form-item label="版本号" path="version">
              <n-input v-model:value="assetForm.version" placeholder="1.0.0" />
            </n-form-item>
            <n-form-item label="技能包">
              <n-upload
                :key="assetUploadKey"
                :default-upload="false"
                :max="1"
                accept=".zip,application/zip,application/x-zip-compressed"
                @change="handleAssetUploadChange"
              >
                <n-upload-dragger>
                  <div class="skill-upload__title">选择 ZIP 技能包</div>
                  <div class="skill-upload__hint">包内需包含 SKILL.md</div>
                </n-upload-dragger>
              </n-upload>
            </n-form-item>
          </template>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="uploadDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submitAsset">{{ assetForm.id ? '保存' : '上传' }}</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="versionDrawerVisible" width="min(1100px, 96vw)">
      <n-drawer-content :title="selectedSkill ? `${selectedSkill.name} · 版本` : '技能版本'">
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
                <small>{{ shortHash(version.content_sha256) }}</small>
              </div>
              <n-tag size="small" :type="versionStatusTagType(version.status)">
                {{ versionStatusLabel(version.status) }}
              </n-tag>
              <span class="version-row__time">{{ formatToDateTime(version.update_time || version.create_time || '') || '-' }}</span>
              <n-space size="small" class="version-row__actions" @click.stop>
                <n-button v-if="canManage && version.status === 'draft'" size="tiny" quaternary type="primary" @click="publishVersion(version)">发布</n-button>
                <n-button
                  v-if="canManage && version.status === 'published'"
                  size="tiny"
                  quaternary
                  type="warning"
                  :disabled="isOnlyPublishedVersion(version)"
                  @click="deprecateVersion(version)"
                >
                  废弃
                </n-button>
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
              <n-form-item label="技能包">
                <n-upload
                  :key="versionUploadKey"
                  :default-upload="false"
                  :max="1"
                  :disabled="isVersionReadonly"
                  accept=".zip,application/zip,application/x-zip-compressed"
                  @change="handleVersionUploadChange"
                >
                  <n-upload-dragger>
                    <div class="skill-upload__title">选择 ZIP 技能包</div>
                    <div class="skill-upload__hint">将替换当前草稿版本内容</div>
                  </n-upload-dragger>
                </n-upload>
              </n-form-item>
              <n-form-item label="校验结果">
                <pre class="validation-report">{{ JSON.stringify(versionForm.validation_report || {}, null, 2) }}</pre>
              </n-form-item>
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
  import type { FormInst, FormRules, SelectOption, TagProps, UploadFileInfo } from 'naive-ui';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteSkillAsset,
    deprecateSkillVersion,
    getSkillAsset,
    getSkillAssets,
    getSkillVersions,
    publishSkillVersion,
    saveSkillAsset,
    saveSkillVersion,
    uploadSkillAsset,
    type SkillAsset,
    type SkillVersion,
  } from '@/api/aiAssets';

  type SkillAssetForm = Partial<SkillAsset> & {
    tags: string[];
    version: string;
    file: File | null;
  };
  type SkillVersionForm = Partial<SkillVersion> & {
    file: File | null;
  };

  const message = useMessage();
  const { hasPermission } = usePermission();
  const canManage = computed(() => hasPermission(['skill:assets:manage']));
  const loading = ref(false);
  const saving = ref(false);
  const rows = ref<SkillAsset[]>([]);
  const paginationTotal = ref(0);
  const versions = ref<SkillVersion[]>([]);
  const selectedSkill = ref<SkillAsset | null>(null);
  const keyword = ref('');
  const statusFilter = ref('all');
  const tagFilters = ref<string[]>([]);
  const uploadDrawerVisible = ref(false);
  const versionDrawerVisible = ref(false);
  const assetFormRef = ref<FormInst | null>(null);
  const assetUploadKey = ref(0);
  const versionUploadKey = ref(0);

  const assetForm = reactive<SkillAssetForm>({
    skill_key: '',
    name: '',
    description: '',
    tags: [],
    status: 'draft',
    source_type: 'upload',
    version: '1.0.0',
    file: null,
  });

  const versionForm = reactive<SkillVersionForm>({
    version: '',
    manifest: {},
    file: null,
    entrypoint: 'SKILL.md',
    runtime_constraints: {},
    validation_report: {},
    status: 'draft',
  });

  const assetRules = computed<FormRules>(() => ({
    ...(assetForm.id
      ? {
          name: [{ required: true, message: '请输入技能名称', trigger: ['blur', 'input'] }],
        }
      : {
          version: [{ required: true, message: '请输入版本号', trigger: ['blur', 'input'] }],
        }),
  }));

  const assetStatusOptions = [
    { label: '全部', value: 'all' },
    { label: '草稿', value: 'draft' },
    { label: '已发布', value: 'published' },
    { label: '已归档', value: 'archived' },
  ];
  const tagOptions = computed<SelectOption[]>(() => uniqueOptions(rows.value.flatMap((row) => row.tags || [])));
  const isVersionReadonly = computed(() => Boolean(versionForm.id && versionForm.status !== 'draft'));
  const pageSchema = computed(() => defineListPage<SkillAsset>({
    id: 'skills.library',
    title: '技能库',
    description: '集中管理可上传、可版本化和可发布的模型技能资产。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'card-list',
      itemKey: (row) => row.id,
      cardMinWidth: '260px',
      sort: { remote: true },
    },
    toolbar: {
      primaryAction: canManage.value
        ? { key: 'upload', label: '上传技能', type: 'primary', onClick: () => openCreate() }
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
      skill_key: '',
      name: '',
      description: '',
      tags: [],
      status: 'draft',
      source_type: 'upload',
      version: '1.0.0',
      file: null,
    });
    assetUploadKey.value += 1;
    assetFormRef.value?.restoreValidation();
  }

  function openCreate() {
    resetAssetForm();
    uploadDrawerVisible.value = true;
  }

  function openEdit(row: SkillAsset) {
    resetAssetForm();
    Object.assign(assetForm, { ...row, tags: [...(row.tags || [])], file: null });
    uploadDrawerVisible.value = true;
    assetFormRef.value?.restoreValidation();
  }

  async function submitAsset() {
    try {
      await assetFormRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      if (assetForm.id) {
        await saveSkillAsset(assetForm);
        message.success('技能已保存');
      } else {
        if (!assetForm.file) {
          message.warning('请选择 ZIP 技能包');
          return;
        }
        await uploadSkillAsset({
          skill_key: assetForm.skill_key,
          version: assetForm.version,
          file: assetForm.file,
        });
        message.success('技能已上传');
      }
      uploadDrawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function openVersions(row: SkillAsset) {
    selectedSkill.value = row;
    versionDrawerVisible.value = true;
    await reloadVersions(row.id);
    openVersionForm(selectEditableVersion(versions.value) || versions.value[0] || null);
  }

  async function reloadVersions(skillId = selectedSkill.value?.id || 0) {
    if (!skillId) return;
    const payload = await getSkillVersions(skillId);
    versions.value = payload.items || [];
  }

  function resetVersionForm() {
    Object.assign(versionForm, {
      id: undefined,
      version: nextVersionLabel(versions.value),
      manifest: {},
      file: null,
      entrypoint: 'SKILL.md',
      runtime_constraints: {},
      validation_report: {},
      status: 'draft',
    });
    versionUploadKey.value += 1;
  }

  function openVersionForm(version: SkillVersion | null) {
    if (!version) {
      resetVersionForm();
      return;
    }
    Object.assign(versionForm, {
      ...version,
      file: null,
      manifest: { ...(version.manifest || {}) },
      runtime_constraints: { ...(version.runtime_constraints || {}) },
      validation_report: { ...(version.validation_report || {}) },
    });
    versionUploadKey.value += 1;
  }

  async function submitVersion() {
    if (!selectedSkill.value) return;
    if (!String(versionForm.version || '').trim()) {
      message.warning('请输入版本号');
      return;
    }
    if (!versionForm.file) {
      message.warning('请选择 ZIP 技能包');
      return;
    }
    saving.value = true;
    try {
      await saveSkillVersion(selectedSkill.value.id, {
        id: versionForm.id,
        version: versionForm.version,
        file: versionForm.file,
      });
      message.success('版本已保存');
      await reloadVersions();
      resetVersionForm();
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function publishVersion(version: SkillVersion) {
    if (!selectedSkill.value) return;
    await publishSkillVersion(selectedSkill.value.id, version.id);
    message.success('技能版本已发布');
    await reloadVersions();
    await reload();
  }

  async function deprecateVersion(version: SkillVersion) {
    if (!selectedSkill.value) return;
    if (isOnlyPublishedVersion(version)) {
      message.warning('至少保留一个已发布版本；要下架整个技能请归档资产');
      return;
    }
    await deprecateSkillVersion(selectedSkill.value.id, version.id);
    message.success('技能版本已废弃');
    await reloadVersions();
    await reload();
  }

  async function remove(row: SkillAsset) {
    const result = await deleteSkillAsset(row.id);
    message.success(result.deleted ? '技能已删除' : '技能已归档');
    await reload();
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await getSkillAssets({
        ...runtimeListParams(state, { pageSize: 12 }),
        keyword: keyword.value || undefined,
        status: statusFilter.value === 'all' ? undefined : statusFilter.value,
      });
      const filtered = tagFilters.value.length
        ? payload.items.filter((row) => tagFilters.value.every((tag) => (row.tags || []).includes(tag)))
        : payload.items;
      rows.value = filtered;
      paginationTotal.value = payload.pagination?.total || filtered.length;
    } finally {
      loading.value = false;
    }
  }

  function selectEditableVersion(items: SkillVersion[]) {
    return items.find((item) => item.status === 'draft') || null;
  }

  function nextVersionLabel(items: SkillVersion[]) {
    return `1.0.${items.length}`;
  }

  function isOnlyPublishedVersion(version: SkillVersion) {
    return version.status === 'published' && versions.value.filter((item) => item.status === 'published').length <= 1;
  }

  function assetStatusLabel(status: string) {
    return status === 'published' ? '已发布' : status === 'archived' ? '已归档' : '草稿';
  }

  function assetStatusTagType(status: string): TagProps['type'] {
    return status === 'published' ? 'success' : status === 'archived' ? 'warning' : 'default';
  }

  function versionStatusLabel(status: string) {
    return status === 'published' ? '已发布' : status === 'deprecated' ? '已废弃' : '草稿';
  }

  function versionStatusTagType(status: string): TagProps['type'] {
    return status === 'published' ? 'success' : status === 'deprecated' ? 'warning' : 'default';
  }

  function shortHash(value: string) {
    return value ? value.slice(0, 10) : '未校验';
  }

  function handleAssetUploadChange(options: { fileList: UploadFileInfo[] }) {
    assetForm.file = fileFromUpload(options.fileList[0]);
  }

  function handleVersionUploadChange(options: { fileList: UploadFileInfo[] }) {
    versionForm.file = fileFromUpload(options.fileList[0]);
  }

  function fileFromUpload(fileInfo?: UploadFileInfo) {
    const file = fileInfo?.file;
    if (!file) return null;
    if (!file.name.toLowerCase().endsWith('.zip')) {
      message.warning('仅支持 ZIP 技能包');
      return null;
    }
    return file;
  }

  reload();
</script>

<style scoped lang="less">
  .skill-library-page {
    &__keyword {
      flex: 0 1 320px;
      min-width: 220px;
    }

    &__tag-select {
      flex: 0 1 260px;
      min-width: 200px;
    }
  }

  .skill-status-filter {
    display: inline-flex;
    flex: 0 0 auto;
    min-width: 0;
    padding: 2px;
    background: var(--app-page-bg);
    border: 1px solid var(--app-border-color);
    border-radius: 8px;
  }

  .skill-status-filter__item {
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

  .skill-status-filter__item--active {
    color: var(--app-primary-color);
    background: var(--app-surface-bg);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  }

  .skill-filter-summary {
    margin-left: auto;
    color: var(--app-icon-color);
    font-size: var(--app-font-size-sm, 13px);
    white-space: nowrap;
  }

  .skill-card {
    display: flex;
    flex-direction: column;
    min-height: 196px;
    padding: 14px;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: 8px;
    gap: 12px;
  }

  .skill-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;

    h3 {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      line-height: 1.4;
    }

    span {
      color: var(--app-icon-color);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }
  }

  .skill-card__description {
    min-height: 42px;
    margin: 0;
    color: var(--app-text-color-2);
    line-height: 1.6;
  }

  .skill-card__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .skill-card__muted {
    color: var(--app-icon-color);
    font-size: 12px;
  }

  .skill-card__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: auto;
    color: var(--app-icon-color);
    font-size: 12px;
  }

  .skill-card__actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .skill-form {
    max-width: 920px;
  }

  .skill-upload__title {
    color: var(--app-text-color);
    font-size: 14px;
    font-weight: 600;
  }

  .skill-upload__hint {
    margin-top: 4px;
    color: var(--app-icon-color);
    font-size: 12px;
  }

  .version-workbench {
    display: grid;
    grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
    gap: 16px;
  }

  .version-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .version-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    padding: 10px;
    border: 1px solid var(--app-border-color);
    border-radius: 8px;
    cursor: pointer;
  }

  .version-row--active {
    border-color: var(--app-primary-color);
    background: var(--app-hover-color);
  }

  .version-row__main {
    display: flex;
    flex-direction: column;
    min-width: 0;

    small {
      color: var(--app-icon-color);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
  }

  .version-row__time,
  .version-row__actions {
    grid-column: 1 / -1;
  }

  .version-editor__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    h3 {
      margin: 0;
      font-size: 16px;
    }
  }

  .validation-report {
    width: 100%;
    max-height: 180px;
    margin: 0;
    overflow: auto;
    padding: 10px;
    border: 1px solid var(--app-border-color);
    border-radius: 8px;
    background: var(--app-page-bg);
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  @media (max-width: 860px) {
    .version-workbench {
      grid-template-columns: 1fr;
    }

    .skill-card__footer {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
