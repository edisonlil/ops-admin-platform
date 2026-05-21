<template>
  <div v-if="!isEditorMode" class="appearance-theme-page">
    <ListPageRuntime :schema="themeListPage" :rows="themes" :loading="themesLoading" :pagination-total="themePaginationTotal" @refresh="loadThemes">
      <template #filters>
        <n-input
          v-model:value="themeSearch"
          clearable
          class="theme-filter-search"
          placeholder="搜索主题名称、状态或预设"
        />
        <div class="theme-status-filter" role="group" aria-label="主题状态筛选">
          <button
            v-for="option in statusFilterOptions"
            :key="option.value"
            type="button"
            class="theme-status-filter__item"
            :class="{ 'theme-status-filter__item--active': statusFilter === option.value }"
            @click="statusFilter = option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <span class="theme-filter-summary">共 {{ themePaginationTotal }} 个</span>
      </template>

      <template #item="{ row: theme }">
        <article class="theme-resource-card" :style="previewStyle(theme)">
          <button class="theme-resource-card__preview" type="button" @click="canUpdateTheme && editTheme(theme.id)">
            <div class="theme-preview-shell">
              <aside class="theme-preview-shell__nav">
                <span></span>
                <span></span>
                <span></span>
              </aside>
              <main class="theme-preview-shell__main">
                <div class="theme-preview-shell__topline"></div>
                <div class="theme-preview-shell__metric-row">
                  <span></span>
                  <span></span>
                </div>
                <div class="theme-preview-shell__table">
                  <span v-for="index in 9" :key="index"></span>
                </div>
              </main>
            </div>
          </button>

          <div class="theme-resource-card__body">
            <header class="theme-resource-card__header">
              <div class="theme-resource-card__title-block">
                <h2>{{ theme.name || '未命名主题' }}</h2>
                <p>版本 {{ theme.version || 1 }}</p>
              </div>
              <n-space size="small" align="center">
                <n-tag v-if="theme.is_platform_default" size="small" type="info">平台默认</n-tag>
                <n-tag size="small" :type="statusTagType(theme.status)">
                  {{ statusLabel(theme.status) }}
                </n-tag>
              </n-space>
            </header>

            <div class="theme-resource-card__footer">
              <div class="theme-resource-card__palette" aria-hidden="true">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div class="theme-resource-card__actions">
                <n-button v-if="canUpdateTheme" size="small" type="primary" secondary @click="editTheme(theme.id)">编辑</n-button>
                <n-dropdown
                  v-if="themeActionOptions(theme).length"
                  trigger="click"
                  :options="themeActionOptions(theme)"
                  @select="(key) => handleThemeAction(key, theme)"
                >
                  <n-button size="small" quaternary>更多</n-button>
                </n-dropdown>
              </div>
            </div>
          </div>
        </article>
      </template>
    </ListPageRuntime>
  </div>

  <div v-else class="appearance-studio-page" :style="appearanceStore.editorCssVars">
    <header class="studio-topbar">
      <div class="studio-topbar__main">
        <n-button quaternary size="small" @click="backToThemes">返回</n-button>
        <div class="studio-topbar__identity">
          <n-input
            v-model:value="appearanceStore.editingThemeName"
            class="studio-topbar__name-input"
            maxlength="40"
            placeholder="请输入主题名称"
          />
          <div class="studio-topbar__meta">
            <n-tag size="small" :type="statusTagType(appearanceStore.editingThemeStatus)">
              {{ statusLabel(appearanceStore.editingThemeStatus) }}
            </n-tag>
            <span>预设 {{ appearanceStore.editingPresetId }}</span>
            <span>校验 {{ appearanceStore.editorValidationErrors.length }} 项</span>
          </div>
        </div>
      </div>
      <n-space class="studio-topbar__actions" align="center">
        <n-button secondary @click="appearanceStore.resetToPreset">重置当前预设</n-button>
        <n-button v-if="canUpdateTheme" type="primary" secondary :loading="appearanceStore.isPublishing" @click="saveDraft">保存草稿</n-button>
        <n-button v-if="canPublishTheme" type="primary" :loading="publishingTheme" @click="publishEditingTheme">发布主题</n-button>
      </n-space>
    </header>

    <section class="studio-shell">
      <aside ref="navPane" class="studio-nav" aria-label="工作台导航">
        <div class="studio-nav__summary">
          <span class="studio-nav__label">工作台</span>
          <strong>{{ activePanelTitle }}</strong>
          <p>{{ activePanelDescription }}</p>
        </div>
        <nav class="studio-nav__groups">
          <section v-for="section in studioNavigation" :key="section.key" class="studio-nav__group">
            <div class="studio-nav__group-title">
              <span>{{ section.title }}</span>
              <em>{{ section.items.length }}</em>
            </div>
            <button
              v-for="page in section.items"
              :key="page.key"
              class="studio-nav__item"
              :class="{ 'studio-nav__item--active': activePageKey === page.key }"
              type="button"
              @click="setActivePage(page.key)"
            >
              <strong>{{ page.title }}</strong>
              <span>{{ page.caption }}</span>
            </button>
          </section>
        </nav>
      </aside>

      <main ref="editorPane" class="studio-editor">
        <div class="studio-editor__header">
          <div>
            <span>{{ activePanelGroup }}</span>
            <h2>{{ activePanelTitle }}</h2>
          </div>
          <p>{{ activePanelDescription }}</p>
        </div>

        <section class="studio-editor__panel">
          <PresetPanel v-if="activePanel === 'presets'" />
          <PrimitivePanel v-else-if="activePanel === 'primitive'" />
          <SemanticPanel v-else-if="activePanel === 'semantic'" />
          <VisualTokenPanel v-else-if="activePanel === 'visual'" :target="activePreviewTarget" />
          <ComponentPanel v-else-if="activePanel === 'components'" :target="activePreviewTarget" />
          <LayoutPanel v-else-if="activePanel === 'layout'" />
          <BehaviorPanel v-else-if="activePanel === 'behavior'" />
          <ImportExportPanel v-else />
        </section>
      </main>

      <aside ref="previewPane" class="studio-preview" aria-label="实时预览">
        <n-alert v-if="appearanceStore.editorValidationErrors.length" type="warning" :bordered="false">
          <div class="studio-preview__alert-title">当前配置有 {{ appearanceStore.editorValidationErrors.length }} 项需要处理</div>
          <div v-for="error in appearanceStore.editorValidationErrors.slice(0, 5)" :key="error.path">
            {{ error.path }}: {{ error.message }}
          </div>
        </n-alert>
        <PreviewPanel :active-panel="activePanel" :preview-target="activePreviewTarget" />
      </aside>
    </section>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import {
    createAppearanceTheme,
    disableAppearanceTheme,
    getAppearanceThemes,
    publishAppearanceTheme,
    setPlatformDefaultAppearanceTheme,
  } from '@/api/appearance';
  import BehaviorPanel from '@/components/AppearanceStudio/BehaviorPanel.vue';
  import ComponentPanel from '@/components/AppearanceStudio/ComponentPanel.vue';
  import ImportExportPanel from '@/components/AppearanceStudio/ImportExportPanel.vue';
  import LayoutPanel from '@/components/AppearanceStudio/LayoutPanel.vue';
  import PresetPanel from '@/components/AppearanceStudio/PresetPanel.vue';
  import PreviewPanel from '@/components/AppearanceStudio/PreviewPanel.vue';
  import PrimitivePanel from '@/components/AppearanceStudio/PrimitivePanel.vue';
  import SemanticPanel from '@/components/AppearanceStudio/SemanticPanel.vue';
  import VisualTokenPanel from '@/components/AppearanceStudio/VisualTokenPanel.vue';
  import type { EffectiveAppearanceTheme } from '@/api/appearance';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';

  type ThemeItem = NonNullable<EffectiveAppearanceTheme['theme']>;
  type PanelKey =
    | 'presets'
    | 'primitive'
    | 'semantic'
    | 'visual'
    | 'components'
    | 'layout'
    | 'behavior'
    | 'io';
  type StudioPageKey =
    | 'presets'
    | 'primitive'
    | 'semantic'
    | 'radius'
    | 'type'
    | 'shadow'
    | 'Button'
    | 'Field'
    | 'DataTable'
    | 'TableToolbar'
    | 'StatusAction'
    | 'Shell'
    | 'layout'
    | 'behavior'
    | 'io';

  interface StudioPage {
    key: StudioPageKey;
    panel: PanelKey;
    previewTarget: string;
    title: string;
    caption: string;
    description: string;
  }

  interface StudioSection {
    key: string;
    title: string;
    items: StudioPage[];
  }

  const appearanceStore = useAppearanceStore();
  const { hasPermission } = usePermission();
  const themes = ref<ThemeItem[]>([]);
  const themePaginationTotal = ref(0);
  const themesLoading = ref(false);
  const publishingTheme = ref(false);
  const themeSearch = ref('');
  const statusFilter = ref('all');
  const activePageKey = ref<StudioPageKey>('presets');
  const navPane = ref<HTMLElement | null>(null);
  const editorPane = ref<HTMLElement | null>(null);
  const previewPane = ref<HTMLElement | null>(null);
  const isEditorMode = computed(() => !!appearanceStore.editingThemeId);
  const canCreateTheme = computed(() => hasPermission(['appearance:themes:create']));
  const canUpdateTheme = computed(() => hasPermission(['appearance:themes:update']));
  const canPublishTheme = computed(() => hasPermission(['appearance:themes:publish']));
  const canDisableTheme = computed(() => hasPermission(['appearance:themes:disable']));
  const canSetDefaultTheme = computed(() => hasPermission(['appearance:themes:set_default']));

  const statusFilterOptions = [
    { label: '全部', value: 'all' },
    { label: '已发布', value: 'published' },
    { label: '草稿', value: 'draft' },
    { label: '已停用', value: 'disabled' },
  ];

  const themeListPage = defineListPage<ThemeItem>({
    id: 'appearance.themes',
    title: '主题管理',
    description: '集中管理后台外观主题。主题发布后，可在租户管理中分配给具体租户。',
    variant: 'enterprise',
    density: 'comfortable',
    view: {
      type: 'card-list',
      itemKey: (theme) => Number(theme.id),
      cardMinWidth: '236px',
      sort: { remote: true },
    },
    toolbar: {
      primaryAction: canCreateTheme.value
        ? { key: 'create', label: '新建主题', type: 'primary', onClick: () => createTheme() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 12, pageSizes: [12, 24, 48], showSizePicker: true },
  });

  const studioNavigation: StudioSection[] = [
    {
      key: 'global',
      title: '全局样式',
      items: [
        { key: 'presets', panel: 'presets', previewTarget: 'presets', title: '风格预设', caption: '主题起点', description: '从内置预设开始，快速确定主题的基础气质。' },
        { key: 'primitive', panel: 'primitive', previewTarget: 'primitive', title: '基础变量', caption: '色阶 / 字号 / 间距', description: '维护色阶、字号、圆角、间距等底层变量。' },
        { key: 'semantic', panel: 'semantic', previewTarget: 'semantic', title: '语义变量', caption: '品牌 / 状态 / 文本', description: '把品牌色、状态色、文本和页面背景映射到业务语义。' },
        { key: 'radius', panel: 'visual', previewTarget: 'radius', title: '圆角', caption: '全局形态', description: '调整卡片、按钮、输入框等常用界面的圆角节奏。' },
        { key: 'type', panel: 'visual', previewTarget: 'type', title: '字体', caption: '字号层级', description: '检查字号层级在标题、数字、中文与表单内容中的真实效果。' },
        { key: 'shadow', panel: 'visual', previewTarget: 'shadow', title: '阴影', caption: '层级深度', description: '控制浮层、卡片和弱强调区域的阴影强度。' },
      ],
    },
    {
      key: 'component',
      title: '组件样式',
      items: [
        { key: 'Button', panel: 'components', previewTarget: 'Button', title: '按钮', caption: '默认 / 主按钮 / 状态', description: '单独配置按钮颜色、圆角、高度和不同交互状态。' },
        { key: 'Field', panel: 'components', previewTarget: 'Field', title: '表单控件', caption: '输入框 / 选择器', description: '单独配置输入框、选择器的边框、焦点色和控件高度。' },
        { key: 'Picker', panel: 'components', previewTarget: 'Picker', title: '选择与弹层', caption: '日期 / 时间 / 树选择', description: '统一配置选择类控件的弹层、选项、日期格子和树选择面板外观。' },
        { key: 'DataTable', panel: 'components', previewTarget: 'DataTable', title: '数据表格', caption: '表头 / 行 / 单元格', description: '单独配置表格背景、行状态、单元格尺寸和表格圆角。' },
        { key: 'TableToolbar', panel: 'components', previewTarget: 'TableToolbar', title: '表格工具栏', caption: '查询 / 批量操作', description: '配置表格查询区、工具栏、批量操作栏和选择列的外观入口。' },
        { key: 'StatusAction', panel: 'components', previewTarget: 'StatusAction', title: '状态与操作', caption: '标签 / 表格操作', description: '单独配置状态标签与表格操作按钮的尺寸和状态色。' },
        { key: 'Tree', panel: 'components', previewTarget: 'Tree', title: '树组件', caption: '节点 / 缩进 / 选中', description: '配置菜单权限树、角色授权树和树选择类控件的节点密度与状态。' },
        { key: 'Upload', panel: 'components', previewTarget: 'Upload', title: '上传组件', caption: '卡片 / 拖拽 / 文件项', description: '配置图片上传卡片、触发区、遮罩和操作图标状态。' },
        { key: 'Shell', panel: 'components', previewTarget: 'Shell', title: '外壳与内容面', caption: '菜单 / 卡片 / 弹窗', description: '单独配置导航菜单、内容卡片和弹窗的基础质感。' },
      ],
    },
    {
      key: 'layout',
      title: '界面布局',
      items: [
        { key: 'layout', panel: 'layout', previewTarget: 'layout', title: '布局外观', caption: '顶栏 / 菜单 / 留白', description: '控制导航宽度、顶栏高度、内容留白和页面密度。' },
        { key: 'behavior', panel: 'behavior', previewTarget: 'behavior', title: '界面行为', caption: '导航 / 页签 / 动画', description: '配置导航模式、面包屑、多页签和页面动画。' },
      ],
    },
    {
      key: 'exchange',
      title: '导入导出',
      items: [
        { key: 'io', panel: 'io', previewTarget: 'io', title: '配置流转', caption: '导入 / 导出', description: '导出主题覆盖或完整外观配置，也可导入已有配置。' },
      ],
    },
  ];

  const studioPages = computed(() => studioNavigation.flatMap((section) => section.items));
  const activePanelConfig = computed(() => {
    return studioPages.value.find((page) => page.key === activePageKey.value) || studioPages.value[0];
  });

  const activePanelTitle = computed(() => activePanelConfig.value.title);
  const activePanelGroup = computed(() => {
    return studioNavigation.find((section) => section.items.some((page) => page.key === activePageKey.value))?.title || '工作台';
  });
  const activePanelDescription = computed(() => activePanelConfig.value.description);
  const activePanel = computed(() => activePanelConfig.value.panel);
  const activePreviewTarget = computed(() => activePanelConfig.value.previewTarget);

  async function setActivePage(page: StudioPageKey) {
    if (activePageKey.value === page) return;
    activePageKey.value = page;
    await nextTick();
    resetWorkbenchScroll();
  }

  function resetWorkbenchScroll() {
    const scrollTargets = [
      navPane.value,
      editorPane.value,
      previewPane.value,
      document.querySelector<HTMLElement>('.layout-content'),
      document.querySelector<HTMLElement>('.n-layout-scroll-container'),
      document.scrollingElement as HTMLElement | null,
      document.documentElement,
      document.body,
    ].filter(Boolean) as HTMLElement[];

    scrollTargets.forEach((target) => {
      target.scrollTo({ top: 0, left: 0 });
    });
    window.scrollTo({ top: 0, left: 0 });
  }

  function statusLabel(status?: string) {
    if (status === 'published') return '已发布';
    if (status === 'disabled') return '已停用';
    return '草稿';
  }

  function statusTagType(status?: string) {
    if (status === 'published') return 'success';
    if (status === 'disabled') return 'default';
    return 'warning';
  }

  function previewStyle(theme: ThemeItem) {
    const draft = theme.draft || theme;
    const semantic = (draft.tokenOverrides?.semantic || draft.token_overrides?.semantic || {}) as Record<string, string>;
    return {
      '--preview-primary': semantic.primaryColor || '#2563eb',
      '--preview-accent': semantic.successColor || '#18a058',
      '--preview-bg': semantic.pageBgColor || '#f8fafc',
      '--preview-text': semantic.textColorBase || '#0f172a',
      '--preview-border': semantic.borderColorBase || '#e2e8f0',
      '--preview-nav': semantic.menuDarkBgColor || '#172033',
    };
  }

  function themeActionOptions(theme: ThemeItem) {
    return [
      {
        label: '设为平台默认',
        key: 'platform-default',
        show: canSetDefaultTheme.value,
        disabled: theme.status !== 'published' || theme.is_platform_default,
      },
      {
        label: '发布',
        key: 'publish',
        show: canPublishTheme.value,
        disabled: theme.status === 'published',
      },
      {
        label: '停用',
        key: 'disable',
        show: canDisableTheme.value,
        disabled: theme.status === 'disabled',
      },
    ].filter((option) => option.show !== false);
  }

  function handleThemeAction(key: string | number, theme: ThemeItem) {
    if (key === 'platform-default') return setPlatformDefault(theme.id);
    if (key === 'publish') return publishTheme(theme.id);
    if (key === 'disable') return disableThemeItem(theme.id);
    return undefined;
  }

  async function loadThemes(state?: ListRuntimeState) {
    themesLoading.value = true;
    try {
      const payload = await getAppearanceThemes({
        ...runtimeListParams(state, { pageSize: 12 }),
        keyword: themeSearch.value.trim() || undefined,
        status: statusFilter.value === 'all' ? undefined : statusFilter.value,
      });
      themes.value = payload.items || [];
      themePaginationTotal.value = payload.pagination?.total || themes.value.length;
    } finally {
      themesLoading.value = false;
    }
  }

  async function createTheme() {
    const payload = await createAppearanceTheme({
      name: '未命名主题',
      version: 1,
      presetId: 'default',
      tokenOverrides: {},
      layoutOverrides: {},
      skinClass: '',
    });
    activePageKey.value = 'presets';
    await appearanceStore.loadThemeDraft(Number(payload.item.id));
  }

  async function editTheme(themeId?: number) {
    if (!themeId) return;
    activePageKey.value = 'presets';
    await appearanceStore.loadThemeDraft(themeId);
  }

  async function publishTheme(themeId?: number) {
    if (!themeId) return;
    await publishAppearanceTheme(themeId);
    if (appearanceStore.backendThemeId === themeId) {
      await appearanceStore.loadEffectiveThemeForCurrentTenant({ forceRefresh: true });
    }
    window.$message?.success('主题已发布');
    await loadThemes();
  }

  async function setPlatformDefault(themeId?: number) {
    if (!themeId) return;
    await setPlatformDefaultAppearanceTheme(themeId);
    if (appearanceStore.backendThemeSource !== 'tenant') {
      await appearanceStore.loadEffectiveThemeForCurrentTenant({ forceRefresh: true });
    }
    window.$message?.success('已设为平台默认主题');
    await loadThemes();
  }

  async function disableThemeItem(themeId?: number) {
    if (!themeId) return;
    await disableAppearanceTheme(themeId);
    if (appearanceStore.backendThemeId === themeId) {
      await appearanceStore.loadEffectiveThemeForCurrentTenant({ forceRefresh: true });
    }
    window.$message?.success('主题已停用');
    await loadThemes();
  }

  async function saveDraft() {
    await appearanceStore.saveEditingThemeDraft();
    window.$message?.success('草稿已保存');
  }

  async function publishEditingTheme() {
    if (!appearanceStore.editingThemeId) return;
    publishingTheme.value = true;
    try {
      await appearanceStore.saveEditingThemeDraft();
      await publishAppearanceTheme(appearanceStore.editingThemeId);
      if (appearanceStore.backendThemeId === appearanceStore.editingThemeId) {
        await appearanceStore.loadEffectiveThemeForCurrentTenant({ forceRefresh: true });
      }
      window.$message?.success('主题已发布');
    } finally {
      publishingTheme.value = false;
    }
  }

  async function backToThemes() {
    appearanceStore.clearEditingTheme();
    await loadThemes();
  }

  watch([themeSearch, statusFilter], () => {
    loadThemes();
  });

  onMounted(loadThemes);
</script>

<style lang="less" scoped>
  .appearance-theme-page {
    min-width: 0;
    font-family: var(--app-font-family-base);
    font-size: var(--app-font-size-base, 14px);
  }

  .appearance-studio-page {
    display: grid;
    gap: 16px;
    padding: var(--app-content-padding);
    font-family: var(--app-font-family-base);
    font-size: var(--app-font-size-base, 14px);
  }

  .theme-filter-search {
    flex: 0 1 360px;
    min-width: 220px;
  }

  .theme-status-filter {
    display: inline-flex;
    flex: 0 0 auto;
    min-width: 0;
    padding: 2px;
    background: var(--app-page-bg);
    border: 1px solid var(--app-border-color);
    border-radius: 8px;
  }

  .theme-status-filter__item {
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

  .theme-status-filter__item--active {
    color: var(--app-primary-color);
    background: var(--app-surface-bg);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  }

  .theme-filter-summary {
    margin-left: auto;
    color: var(--app-icon-color);
    font-size: var(--app-font-size-sm, 13px);
    white-space: nowrap;
  }

  .theme-resource-card {
    display: grid;
    grid-template-rows: auto 1fr;
    min-width: 0;
    overflow: hidden;
    background: var(--app-card-bg, var(--app-surface-bg));
    border: 1px solid var(--app-card-border-color, var(--app-border-color));
    border-radius: var(--app-card-radius, 8px);
    box-shadow: var(--app-card-shadow, none);
    transition:
      border-color 0.18s ease,
      box-shadow 0.18s ease,
      transform 0.18s ease;
  }

  .theme-resource-card:hover {
    border-color: color-mix(in srgb, var(--preview-primary) 38%, var(--app-border-color));
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
    transform: translateY(-1px);
  }

  .theme-resource-card__preview {
    display: block;
    width: 100%;
    padding: 14px;
    font: inherit;
    text-align: left;
    cursor: pointer;
    background:
      linear-gradient(135deg, color-mix(in srgb, var(--preview-primary) 10%, transparent), transparent 46%),
      var(--preview-bg);
    border: 0;
    border-bottom: 1px solid color-mix(in srgb, var(--preview-border) 86%, transparent);
  }

  .theme-resource-card__preview:focus-visible {
    outline: 2px solid var(--preview-primary);
    outline-offset: -3px;
  }

  .theme-preview-shell {
    display: grid;
    grid-template-columns: 64px minmax(0, 1fr);
    gap: 10px;
    height: 106px;
    min-width: 0;
  }

  .theme-preview-shell__nav,
  .theme-preview-shell__main {
    min-width: 0;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--preview-border) 78%, transparent);
    border-radius: 8px;
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
  }

  .theme-preview-shell__nav {
    display: grid;
    align-content: start;
    gap: 10px;
    padding: 12px 10px;
    background: var(--preview-nav);
  }

  .theme-preview-shell__nav span {
    display: block;
    height: 6px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.48);
  }

  .theme-preview-shell__nav span:first-child {
    background: var(--preview-primary);
  }

  .theme-preview-shell__nav span:nth-child(2) {
    width: 78%;
  }

  .theme-preview-shell__nav span:nth-child(3) {
    width: 54%;
  }

  .theme-preview-shell__main {
    display: grid;
    gap: 9px;
    padding: 12px;
    background: color-mix(in srgb, var(--preview-bg) 74%, #fff);
  }

  .theme-preview-shell__topline {
    width: 48%;
    height: 10px;
    border-radius: 999px;
    background: var(--preview-primary);
  }

  .theme-preview-shell__metric-row {
    display: grid;
    grid-template-columns: 1fr 0.72fr;
    gap: 8px;
  }

  .theme-preview-shell__metric-row span {
    height: 20px;
    border-radius: 6px;
    background: color-mix(in srgb, var(--preview-primary) 12%, #fff);
  }

  .theme-preview-shell__table {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;
  }

  .theme-preview-shell__table span {
    height: 10px;
    border-radius: 4px;
    background: color-mix(in srgb, var(--preview-border) 70%, #fff);
  }

  .theme-resource-card__body {
    display: grid;
    gap: 10px;
    min-width: 0;
    padding: 12px;
  }

  .theme-resource-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
  }

  .theme-resource-card__title-block {
    min-width: 0;
  }

  .theme-resource-card__title-block h2 {
    margin: 0;
    overflow: hidden;
    color: var(--app-text-color);
    font-size: 15px;
    font-weight: 650;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .theme-resource-card__title-block p {
    margin: 2px 0 0;
    color: var(--app-icon-color);
    font-size: 13px;
    line-height: 18px;
  }

  .theme-resource-card__palette {
    display: grid;
    grid-template-columns: 1.4fr 1fr 1fr;
    gap: 6px;
    height: 6px;
  }

  .theme-resource-card__palette span {
    border-radius: 999px;
    background: var(--preview-primary);
  }

  .theme-resource-card__palette span:nth-child(2) {
    background: var(--preview-accent);
  }

  .theme-resource-card__palette span:nth-child(3) {
    background: var(--preview-border);
  }

  .theme-resource-card__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;
  }

  .theme-resource-card__actions {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 4px;
  }

  .studio-topbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    min-width: 0;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--app-border-color);

    &__main {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      min-width: 0;
    }

    &__identity {
      display: grid;
      gap: 4px;
      min-width: 0;
    }

    &__meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      color: var(--app-icon-color);
      font-size: var(--app-font-size-sm, 13px);
      line-height: 20px;
    }

    &__name-input {
      width: min(420px, 54vw);
      --n-color: transparent !important;
      --n-color-focus: transparent !important;
      --n-color-disabled: transparent !important;

      :deep(.n-input-wrapper) {
        padding-inline: 8px;
        margin-left: -8px;
        background: transparent;
        border-radius: 6px;
      }

      :deep(.n-input__border),
      :deep(.n-input__state-border) {
        border-color: transparent;
      }

      :deep(.n-input__input) {
        height: 36px;
      }

      :deep(.n-input__input-el),
      :deep(.n-input__placeholder) {
        height: 36px;
        color: var(--app-text-color);
        font-size: calc(var(--app-font-size-lg, 16px) + 6px);
        font-weight: 650;
        line-height: 36px;
      }

      &:hover,
      &:focus-within {
        :deep(.n-input-wrapper) {
          background: color-mix(in srgb, var(--app-hover-color) 76%, transparent);
        }
      }
    }
  }

  .studio-shell {
    display: grid;
    grid-template-columns: 220px minmax(360px, 0.82fr) minmax(460px, 1.18fr);
    gap: 12px;
    align-items: start;
    min-width: 0;
  }

  .studio-nav,
  .studio-editor,
  .studio-preview {
    min-width: 0;
  }

  .studio-nav {
    position: sticky;
    top: calc(var(--app-header-height, 64px) + var(--app-tabs-height, 44px) + 12px);
    display: grid;
    gap: 12px;
    max-height: calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 24px);
    overflow-y: auto;
    scrollbar-gutter: stable;

    &__summary {
      display: grid;
      gap: 3px;
      padding: 0 4px 10px;
      border-bottom: 1px solid var(--app-border-color);

      strong {
        color: var(--app-text-color);
        font-size: var(--app-font-size-md, 14px);
      }

      p {
        margin: 0;
        color: var(--app-icon-color);
        font-size: var(--app-font-size-xs, 12px);
        line-height: 18px;
      }
    }

    &__label,
    &__item span {
      color: var(--app-icon-color);
      font-size: var(--app-font-size-sm, 13px);
      line-height: 18px;
    }

    &__groups {
      display: grid;
      gap: 14px;
    }

    &__group {
      display: grid;
      gap: 4px;
    }

    &__group-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 0 4px 4px;
      color: var(--app-icon-color);
      font-size: var(--app-font-size-sm, 13px);
      line-height: 18px;

      span {
        font-weight: 650;
      }

      em {
        min-width: 18px;
        color: color-mix(in srgb, var(--app-icon-color) 72%, transparent);
        font-style: normal;
        text-align: right;
      }
    }

    &__item {
      display: grid;
      gap: 2px;
      width: 100%;
      padding: 8px 10px 8px 12px;
      font: inherit;
      text-align: left;
      cursor: pointer;
      background: transparent;
      border: 0;
      border-left: 2px solid transparent;
      border-radius: 0 6px 6px 0;

      strong {
        color: var(--app-text-color);
        font-size: var(--app-font-size-md, 14px);
        font-weight: 650;
        line-height: 20px;
      }

      &:hover {
        background: var(--app-hover-color);
      }

      &:focus-visible {
        outline: 2px solid color-mix(in srgb, var(--app-primary-color) 42%, transparent);
        outline-offset: 1px;
      }

      &--active {
        background: var(--app-primary-soft-bg, var(--app-surface-muted-bg));
        border-left-color: var(--app-primary-color);

        strong {
          color: var(--app-primary-color);
        }
      }
    }
  }

  .studio-editor {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    gap: 12px;
    max-height: calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 24px);
    overflow-y: auto;
    padding: 14px 16px;
    background: var(--app-surface-bg);
    border-left: 1px solid var(--app-border-color);
    border-radius: 0;
    scrollbar-gutter: stable;

    &__header {
      display: grid;
      grid-template-columns: minmax(124px, 0.42fr) minmax(240px, 1fr);
      align-items: start;
      gap: 16px;
      min-width: 0;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--app-border-color);

      > div {
        min-width: 0;
      }

      h2 {
        margin: 0;
        color: var(--app-text-color);
        font-size: calc(var(--app-font-size-base, 14px) + 4px);
        font-weight: 700;
        line-height: 24px;
        overflow-wrap: anywhere;
      }

      p {
        max-width: 56ch;
        margin: 0;
        color: var(--app-icon-color);
        font-size: var(--app-font-size-base, 14px);
        line-height: 1.55;
      }

      span {
        color: var(--app-icon-color);
        font-size: var(--app-font-size-sm, 13px);
        line-height: 18px;
        white-space: nowrap;
      }
    }

    &__panel {
      min-height: 560px;
    }
  }

  .studio-preview {
    position: sticky;
    top: calc(var(--app-header-height, 64px) + var(--app-tabs-height, 44px) + 12px);
    display: grid;
    gap: 12px;
    max-height: calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 24px);
    overflow-y: auto;
    scrollbar-gutter: stable;

    &__alert-title {
      margin-bottom: 4px;
      font-weight: 650;
    }
  }

  @media (max-width: 1280px) {
    .studio-shell {
      grid-template-columns: 198px minmax(340px, 0.9fr) minmax(400px, 1.1fr);
    }
  }

  @media (max-width: 920px) {
    .studio-topbar {
      flex-direction: column;
    }

    .theme-filter-search {
      flex-basis: auto;
      width: 100%;
      min-width: 0;
    }

    .theme-filter-summary {
      margin-left: 0;
      white-space: normal;
    }

    .theme-status-filter {
      overflow-x: auto;
    }

    .studio-editor__header {
      grid-template-columns: minmax(0, 1fr);
    }

    .studio-shell {
      grid-template-columns: minmax(0, 1fr);
    }

    .studio-nav {
      position: static;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      max-height: none;
      overflow: visible;

      &__summary {
        grid-column: 1 / -1;
      }
    }

    .studio-editor {
      max-height: none;
      overflow: visible;
    }

    .studio-preview {
      position: static;
      max-height: none;
      overflow: visible;
    }
  }

  @media (max-width: 560px) {
    .studio-topbar__name-input {
      width: 100%;
    }

    .studio-nav {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
