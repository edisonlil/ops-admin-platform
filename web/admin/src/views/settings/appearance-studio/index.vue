<template>
  <div v-if="!isEditorMode" class="appearance-theme-page">
    <section class="theme-workbench-header">
      <div class="theme-workbench-header__copy">
        <span class="theme-workbench-header__eyebrow">Appearance Studio</span>
        <h1>主题管理</h1>
        <p>集中管理后台外观主题。主题发布后，可在租户管理中分配给具体租户。</p>
      </div>
      <n-space class="theme-workbench-header__actions" align="center">
        <n-button :loading="themesLoading" @click="loadThemes">刷新</n-button>
        <n-button type="primary" @click="createTheme">新建主题</n-button>
      </n-space>
    </section>

    <section class="theme-toolbar" aria-label="主题筛选">
      <n-input
        v-model:value="themeSearch"
        clearable
        class="theme-toolbar__search"
        placeholder="搜索主题名称或状态"
      />
      <div class="theme-toolbar__filters" role="group" aria-label="主题状态筛选">
        <button
          v-for="option in statusFilterOptions"
          :key="option.value"
          type="button"
          :class="{ 'theme-toolbar__filter--active': statusFilter === option.value }"
          @click="statusFilter = option.value"
        >
          {{ option.label }}
        </button>
      </div>
      <div class="theme-toolbar__summary">
        共 {{ themes.length }} 个主题，当前显示 {{ filteredThemes.length }} 个
      </div>
    </section>

    <section class="theme-card-grid" aria-label="主题资产">
      <article v-for="theme in filteredThemes" :key="theme.id" class="theme-card">
        <button class="theme-card__preview" type="button" :style="previewStyle(theme)" @click="editTheme(theme.id)">
          <div class="theme-card__preview-nav">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div class="theme-card__preview-main">
            <div class="theme-card__preview-bar"></div>
            <div class="theme-card__preview-row">
              <span></span>
              <span></span>
            </div>
            <div class="theme-card__preview-table">
              <span v-for="index in 9" :key="index"></span>
            </div>
          </div>
        </button>

        <div class="theme-card__body">
          <div class="theme-card__title-row">
            <div class="theme-card__title">
              <span class="theme-card__mark" :style="previewStyle(theme)">{{ themeInitial(theme) }}</span>
              <div>
                <h2>{{ theme.name || '未命名主题' }}</h2>
                <p>版本 {{ theme.version || 1 }}</p>
              </div>
            </div>
            <n-space size="small" align="center">
              <n-tag v-if="theme.is_platform_default" size="small" type="info">平台默认</n-tag>
              <n-tag size="small" :type="statusTagType(theme.status)">
                {{ statusLabel(theme.status) }}
              </n-tag>
            </n-space>
          </div>

          <div class="theme-card__facts">
            <span>分配租户 {{ theme.tenant_assignment_count || 0 }}</span>
            <span>预设 {{ theme.presetId || theme.preset_id || 'default' }}</span>
          </div>

          <n-space class="theme-card__actions" justify="end" :wrap="true">
            <n-button size="small" type="primary" secondary @click="editTheme(theme.id)">编辑</n-button>
            <n-button
              size="small"
              type="info"
              secondary
              :disabled="theme.status !== 'published' || theme.is_platform_default"
              @click="setPlatformDefault(theme.id)"
            >
              设为平台默认
            </n-button>
            <n-button
              size="small"
              type="primary"
              secondary
              :disabled="theme.status === 'published'"
              @click="publishTheme(theme.id)"
            >
              发布
            </n-button>
            <n-button
              size="small"
              type="warning"
              secondary
              :disabled="theme.status === 'disabled'"
              @click="disableThemeItem(theme.id)"
            >
              停用
            </n-button>
          </n-space>
        </div>
      </article>
    </section>

    <n-empty
      v-if="!themesLoading && !filteredThemes.length"
      class="theme-empty"
      description="没有匹配的主题"
    />
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
        <n-button type="primary" secondary :loading="appearanceStore.isPublishing" @click="saveDraft">保存草稿</n-button>
        <n-button type="primary" :loading="publishingTheme" @click="publishEditingTheme">发布主题</n-button>
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
  import { computed, nextTick, onMounted, ref } from 'vue';
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
  const themes = ref<ThemeItem[]>([]);
  const themesLoading = ref(false);
  const publishingTheme = ref(false);
  const themeSearch = ref('');
  const statusFilter = ref('all');
  const activePageKey = ref<StudioPageKey>('presets');
  const navPane = ref<HTMLElement | null>(null);
  const editorPane = ref<HTMLElement | null>(null);
  const previewPane = ref<HTMLElement | null>(null);
  const isEditorMode = computed(() => !!appearanceStore.editingThemeId);

  const statusFilterOptions = [
    { label: '全部', value: 'all' },
    { label: '已发布', value: 'published' },
    { label: '草稿', value: 'draft' },
    { label: '已停用', value: 'disabled' },
  ];

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

  const filteredThemes = computed(() => {
    const keyword = themeSearch.value.trim().toLowerCase();
    return themes.value.filter((theme) => {
      const status = theme.status || 'draft';
      const matchesStatus = statusFilter.value === 'all' || status === statusFilter.value;
      const searchable = [theme.name || '未命名主题', statusLabel(theme.status), theme.presetId || theme.preset_id || 'default']
        .join(' ')
        .toLowerCase();
      return matchesStatus && (!keyword || searchable.includes(keyword));
    });
  });

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

  function themeInitial(theme: ThemeItem) {
    return (theme.name || '主题').trim().slice(0, 1).toUpperCase();
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

  async function loadThemes() {
    themesLoading.value = true;
    try {
      const payload = await getAppearanceThemes();
      themes.value = payload.items || [];
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
      await appearanceStore.loadEffectiveThemeForCurrentTenant();
    }
    window.$message?.success('主题已发布');
    await loadThemes();
  }

  async function setPlatformDefault(themeId?: number) {
    if (!themeId) return;
    await setPlatformDefaultAppearanceTheme(themeId);
    if (appearanceStore.backendThemeSource !== 'tenant') {
      await appearanceStore.loadEffectiveThemeForCurrentTenant();
    }
    window.$message?.success('已设为平台默认主题');
    await loadThemes();
  }

  async function disableThemeItem(themeId?: number) {
    if (!themeId) return;
    await disableAppearanceTheme(themeId);
    if (appearanceStore.backendThemeId === themeId) {
      await appearanceStore.loadEffectiveThemeForCurrentTenant();
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
        await appearanceStore.loadEffectiveThemeForCurrentTenant();
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

  onMounted(loadThemes);
</script>

<style lang="less" scoped>
  .appearance-theme-page,
  .appearance-studio-page {
    display: grid;
    gap: 16px;
    padding: var(--app-content-padding);
    font-family: var(--app-font-family-base);
    font-size: var(--app-font-size-base, 14px);
  }

  .theme-workbench-header,
  .studio-topbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    min-width: 0;
  }

  .theme-workbench-header {
    padding-bottom: 4px;

    &__copy {
      min-width: 0;
    }

    &__eyebrow {
      display: block;
      margin-bottom: 4px;
      color: var(--app-primary-color);
      font-size: var(--app-font-size-xs, 12px);
      font-weight: 700;
      line-height: 18px;
    }

    h1 {
      margin: 0;
      color: var(--app-text-color);
      font-size: calc(var(--app-font-size-lg, 16px) + 6px);
      font-weight: 650;
      line-height: 30px;
    }

    p {
      margin: 4px 0 0;
      color: var(--app-icon-color);
      line-height: 22px;
    }
  }

  .theme-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
    padding: 12px;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-card-radius);

    &__search {
      flex: 0 1 320px;
      min-width: 220px;
    }

    &__summary {
      margin-left: auto;
      color: var(--app-icon-color);
      font-size: var(--app-font-size-sm, 13px);
      white-space: nowrap;
    }

    &__filters {
      display: inline-flex;
      flex: 0 0 auto;
      min-width: 0;
      padding: 2px;
      background: var(--app-page-bg);
      border: 1px solid var(--app-border-color);
      border-radius: 8px;

      button {
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

        &:hover {
          color: var(--app-text-color);
          background: var(--app-hover-color);
        }
      }
    }

    &__filter--active {
      color: var(--app-primary-color) !important;
      background: var(--app-surface-bg) !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    }
  }

  .theme-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
    align-items: stretch;
  }

  .theme-card {
    display: grid;
    grid-template-rows: auto 1fr;
    min-width: 0;
    overflow: hidden;
    background: var(--app-card-bg, var(--app-surface-bg));
    border: 1px solid var(--app-card-border-color, var(--app-border-color));
    border-radius: var(--app-card-radius);
    box-shadow: var(--app-card-shadow, none);

    &__preview {
      display: grid;
      grid-template-columns: 82px minmax(0, 1fr);
      gap: 12px;
      width: 100%;
      height: 156px;
      padding: 14px;
      font: inherit;
      color: var(--preview-text);
      text-align: left;
      cursor: pointer;
      background: var(--preview-bg);
      border: 0;
      border-bottom: 1px solid color-mix(in srgb, var(--preview-border) 88%, transparent);
      transition:
        filter 0.18s ease,
        background 0.18s ease;

      &:hover {
        filter: saturate(1.04);
        background: color-mix(in srgb, var(--preview-bg) 90%, var(--preview-primary));
      }

      &:focus-visible {
        outline: 2px solid var(--preview-primary);
        outline-offset: -3px;
      }
    }

    &__preview-nav,
    &__preview-main {
      min-width: 0;
      overflow: hidden;
      border: 1px solid color-mix(in srgb, var(--preview-border) 76%, transparent);
      border-radius: 8px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    }

    &__preview-nav {
      display: grid;
      align-content: start;
      gap: 10px;
      padding: 14px 12px;
      background: var(--preview-nav);

      span {
        display: block;
        height: 8px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.45);
      }

      span:first-child {
        background: var(--preview-primary);
      }

      span:nth-child(2) {
        width: 78%;
      }

      span:nth-child(3) {
        width: 54%;
      }
    }

    &__preview-main {
      display: grid;
      gap: 12px;
      padding: 14px;
      background: color-mix(in srgb, var(--preview-bg) 72%, #fff);
    }

    &__preview-bar {
      width: 48%;
      height: 12px;
      border-radius: 999px;
      background: var(--preview-primary);
    }

    &__preview-row {
      display: grid;
      grid-template-columns: 1fr 0.72fr;
      gap: 8px;

      span {
        height: 24px;
        border-radius: 6px;
        background: color-mix(in srgb, var(--preview-primary) 12%, #fff);
      }
    }

    &__preview-table {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 7px;

      span {
        height: 13px;
        border-radius: 4px;
        background: color-mix(in srgb, var(--preview-border) 70%, #fff);
      }
    }

    &__body {
      display: grid;
      gap: 14px;
      min-width: 0;
      padding: 14px;
    }

    &__title-row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      min-width: 0;
    }

    &__title {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;

      h2 {
        margin: 0;
        color: var(--app-text-color);
        font-size: var(--app-font-size-lg, 16px);
        font-weight: 700;
        line-height: 24px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      p {
        margin: 1px 0 0;
        color: var(--app-icon-color);
        font-size: var(--app-font-size-sm, 13px);
        line-height: 18px;
      }
    }

    &__mark {
      display: inline-grid;
      flex: 0 0 34px;
      width: 34px;
      height: 34px;
      color: #fff;
      font-size: calc(var(--app-font-size-lg, 16px) + 1px);
      font-weight: 800;
      place-items: center;
      background: var(--preview-primary);
      border-radius: 8px;
    }

    &__facts {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;

      span {
        padding: 3px 8px;
        color: var(--app-icon-color);
        font-size: var(--app-font-size-xs, 12px);
        line-height: 18px;
        background: var(--app-surface-muted-bg);
        border: 1px solid var(--app-border-color);
        border-radius: 999px;
      }
    }

    &__actions {
      min-width: 0;
    }
  }

  .theme-empty {
    padding: 48px 0;
  }

  .studio-topbar {
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
    .theme-workbench-header,
    .studio-topbar {
      flex-direction: column;
    }

    .studio-editor__header {
      grid-template-columns: minmax(0, 1fr);
    }

    .theme-toolbar {
      align-items: stretch;
      flex-direction: column;

      &__search {
        flex-basis: auto;
        width: 100%;
        min-width: 0;
      }

      &__summary {
        margin-left: 0;
        white-space: normal;
      }

      &__filters {
        overflow-x: auto;
      }
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
    .theme-card-grid {
      grid-template-columns: minmax(0, 1fr);
    }

    .theme-card__preview {
      grid-template-columns: 64px minmax(0, 1fr);
      height: 136px;
      padding: 10px;
    }

    .studio-topbar__name-input {
      width: 100%;
    }

    .studio-nav {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
