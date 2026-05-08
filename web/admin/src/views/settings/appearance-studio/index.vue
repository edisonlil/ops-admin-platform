<template>
  <div v-if="!isEditorMode" class="appearance-theme-page">
    <div class="appearance-theme-page__header">
      <div>
        <h1>主题管理</h1>
        <p>管理可复用的后台外观主题。租户使用哪个主题，请在租户管理中分配。</p>
      </div>
      <n-space>
        <n-button :loading="themesLoading" @click="loadThemes">刷新</n-button>
        <n-button type="primary" @click="createTheme">新建主题</n-button>
      </n-space>
    </div>

    <div class="theme-card-grid">
      <article v-for="theme in themes" :key="theme.id" class="theme-card">
        <button class="theme-card__showcase" type="button" :style="previewStyle(theme)" @click="editTheme(theme.id)">
          <div class="theme-card__brand">
            <span class="theme-card__mark">{{ themeInitial(theme) }}</span>
            <strong>{{ theme.name || '未命名主题' }}</strong>
          </div>
          <div class="theme-card__mock">
            <div class="theme-card__mock-main">
              <div class="theme-card__topline"></div>
              <div class="theme-card__metric-row">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div class="theme-card__chart">
                <span v-for="index in 7" :key="index"></span>
              </div>
            </div>
            <div class="theme-card__mock-side">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </button>

        <div class="theme-card__meta">
          <div class="theme-card__info">
            <h3>{{ theme.name || '未命名主题' }}</h3>
            <p>版本 {{ theme.version }} · 已分配 {{ theme.tenant_assignment_count || 0 }} 个租户</p>
          </div>
          <n-space size="small" align="center">
            <n-tag v-if="theme.is_platform_default" size="small" type="info">平台默认</n-tag>
            <n-tag size="small" :type="theme.status === 'published' ? 'success' : theme.status === 'draft' ? 'warning' : 'default'">
              {{ statusLabel(theme.status) }}
            </n-tag>
          </n-space>
        </div>

        <n-space class="theme-card__actions" justify="end">
          <n-button size="small" @click="editTheme(theme.id)">编辑</n-button>
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
      </article>
    </div>

    <n-empty v-if="!themesLoading && !themes.length" description="暂无主题" />
  </div>

  <div v-else class="appearance-studio-page">
    <div class="appearance-studio-page__header">
      <div>
        <div class="appearance-studio-page__title-row">
          <n-input
            v-model:value="appearanceStore.editingThemeName"
            class="appearance-studio-page__name-input"
            maxlength="40"
            placeholder="请输入主题名称"
          />
          <n-tag size="small" :type="appearanceStore.editingThemeStatus === 'published' ? 'success' : 'warning'">
            {{ statusLabel(appearanceStore.editingThemeStatus) }}
          </n-tag>
        </div>
        <p>编辑当前主题草稿。保存草稿不会影响租户，发布后租户分配才会使用新版本。</p>
      </div>
      <n-space>
        <n-button @click="backToThemes">返回主题管理</n-button>
        <n-button secondary @click="appearanceStore.resetToPreset">重置当前预设</n-button>
        <n-button type="primary" secondary :loading="appearanceStore.isPublishing" @click="saveDraft">保存草稿</n-button>
        <n-button type="primary" :loading="publishingTheme" @click="publishEditingTheme">发布主题</n-button>
        <n-button type="primary" @click="appearanceStore.applyPreset('primevue-like')">
          应用 PrimeVue 风格
        </n-button>
      </n-space>
    </div>

    <n-grid :cols="24" :x-gap="16" :y-gap="16" responsive="screen">
      <n-grid-item :span="15">
        <n-card :bordered="true" class="appearance-studio-page__panel">
          <n-tabs type="line" animated>
            <n-tab-pane name="presets" tab="风格预设">
              <PresetPanel />
            </n-tab-pane>
            <n-tab-pane name="primitive" tab="基础变量">
              <PrimitivePanel />
            </n-tab-pane>
            <n-tab-pane name="semantic" tab="语义变量">
              <SemanticPanel />
            </n-tab-pane>
            <n-tab-pane name="visual" tab="圆角 / 字体">
              <VisualTokenPanel />
            </n-tab-pane>
            <n-tab-pane name="components" tab="组件样式">
              <ComponentPanel />
            </n-tab-pane>
            <n-tab-pane name="layout" tab="布局外观">
              <LayoutPanel />
            </n-tab-pane>
            <n-tab-pane name="behavior" tab="界面行为">
              <BehaviorPanel />
            </n-tab-pane>
            <n-tab-pane name="io" tab="导入 / 导出">
              <ImportExportPanel />
            </n-tab-pane>
          </n-tabs>
        </n-card>
      </n-grid-item>
      <n-grid-item :span="9">
        <n-space vertical :size="16">
          <n-alert v-if="appearanceStore.editorValidationErrors.length" type="warning" :bordered="false">
            <div v-for="error in appearanceStore.editorValidationErrors.slice(0, 6)" :key="error.path">
              {{ error.path }}: {{ error.message }}
            </div>
          </n-alert>
          <PreviewPanel />
        </n-space>
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref } from 'vue';
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

  const appearanceStore = useAppearanceStore();
  const themes = ref<NonNullable<EffectiveAppearanceTheme['theme'][]>>([]);
  const themesLoading = ref(false);
  const publishingTheme = ref(false);
  const isEditorMode = computed(() => !!appearanceStore.editingThemeId);

  function statusLabel(status?: string) {
    if (status === 'published') return '已发布';
    if (status === 'disabled') return '已停用';
    return '草稿';
  }

  function themeInitial(theme: NonNullable<EffectiveAppearanceTheme['theme']>) {
    return (theme.name || '主题').trim().slice(0, 1).toUpperCase();
  }

  function previewStyle(theme: NonNullable<EffectiveAppearanceTheme['theme']>) {
    const draft = theme.draft || theme;
    const semantic = (draft.tokenOverrides?.semantic || draft.token_overrides?.semantic || {}) as Record<string, string>;
    return {
      '--preview-primary': semantic.primaryColor || '#2563eb',
      '--preview-accent': semantic.successColor || '#18a058',
      '--preview-bg': semantic.pageBgColor || '#f8fafc',
      '--preview-text': semantic.textColorBase || '#0f172a',
      '--preview-border': semantic.borderColorBase || '#e2e8f0',
      '--preview-nav': semantic.menuDarkBgColor || '#001b33',
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
    await appearanceStore.loadThemeDraft(Number(payload.item.id));
  }

  async function editTheme(themeId?: number) {
    if (!themeId) return;
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
  .appearance-theme-page {
    display: grid;
    gap: 16px;
    padding: var(--app-content-padding);

    &__header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;

      h1 {
        margin: 0;
        color: var(--app-text-color);
        font-size: 22px;
        font-weight: 650;
        line-height: 30px;
      }

      p {
        margin: 4px 0 0;
        color: var(--app-icon-color);
        line-height: 22px;
      }
    }
  }

  .theme-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 20px;
    align-items: stretch;
    max-width: 1360px;
  }

  .theme-card {
    display: grid;
    grid-template-rows: auto 1fr auto;
    gap: 14px;
    min-width: 0;
    padding: 12px;
    background: var(--app-card-bg, var(--app-surface-bg));
    border: 1px solid var(--app-card-border-color, var(--app-border-color));
    border-radius: var(--app-card-radius);
    box-shadow: var(--app-card-shadow, none);

    &__showcase {
      position: relative;
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      min-height: 210px;
      padding: 24px;
      overflow: hidden;
      font: inherit;
      color: var(--preview-text);
      text-align: left;
      cursor: pointer;
      background:
        radial-gradient(circle at 3px 3px, color-mix(in srgb, var(--preview-primary) 22%, transparent) 1.4px, transparent 1.6px) 0 0 / 16px 16px,
        linear-gradient(135deg, color-mix(in srgb, var(--preview-primary) 14%, #fff), color-mix(in srgb, var(--preview-accent) 12%, #fff));
      border: 1px solid color-mix(in srgb, var(--preview-border) 76%, transparent);
      border-radius: max(8px, calc(var(--app-card-radius) - 2px));
      box-shadow: none;
      transition:
        border-color 0.2s ease,
        filter 0.2s ease,
        transform 0.2s ease;

      &:hover {
        border-color: color-mix(in srgb, var(--preview-primary) 36%, var(--preview-border));
        filter: saturate(1.04);
        transform: translateY(-2px);
      }

      &:focus-visible {
        outline: 2px solid var(--preview-primary);
        outline-offset: 3px;
      }
    }

    &__brand {
      position: relative;
      z-index: 1;
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;

      strong {
        min-width: 0;
        color: #0b1220;
        font-size: 26px;
        font-weight: 800;
        line-height: 34px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    &__mark {
      display: inline-grid;
      flex: 0 0 38px;
      width: 38px;
      height: 38px;
      color: #fff;
      font-size: 20px;
      font-weight: 800;
      place-items: center;
      background: var(--preview-primary);
      border-radius: 10px;
      box-shadow: 0 10px 20px color-mix(in srgb, var(--preview-primary) 28%, transparent);
    }

    &__mock {
      position: absolute;
      right: 22px;
      bottom: 0;
      left: 18%;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 27%;
      gap: 12px;
      align-items: end;
      min-width: 0;
    }

    &__mock-main,
    &__mock-side {
      overflow: hidden;
      background: color-mix(in srgb, var(--preview-bg) 88%, #fff);
      border: 1px solid color-mix(in srgb, var(--preview-border) 68%, #fff);
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
    }

    &__mock-main {
      display: grid;
      gap: 12px;
      min-width: 0;
      height: 142px;
      padding: 16px;
      border-radius: 12px 12px 0 0;
    }

    &__mock-side {
      display: grid;
      align-content: start;
      gap: 10px;
      height: 116px;
      padding: 14px;
      background: var(--preview-nav);
      border-color: color-mix(in srgb, var(--preview-nav) 84%, #fff);
      border-radius: 16px 16px 0 0;

      span {
        display: block;
        height: 9px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.4);
      }

      span:nth-child(2) {
        width: 78%;
      }

      span:nth-child(3) {
        width: 54%;
        background: var(--preview-primary);
      }
    }

    &__topline {
      width: 56%;
      height: 12px;
      border-radius: 999px;
      background: color-mix(in srgb, var(--preview-border) 78%, #fff);
    }

    &__metric-row {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;

      span {
        height: 28px;
        border-radius: 7px;
        background: color-mix(in srgb, var(--preview-primary) 13%, #fff);
      }
    }

    &__chart {
      display: flex;
      align-items: flex-end;
      gap: 7px;
      height: 56px;

      span {
        flex: 1 1 0;
        min-width: 0;
        border-radius: 999px 999px 0 0;
        background: var(--preview-primary);
      }

      span:nth-child(1) {
        height: 32%;
      }

      span:nth-child(2) {
        height: 55%;
      }

      span:nth-child(3) {
        height: 42%;
      }

      span:nth-child(4) {
        height: 74%;
      }

      span:nth-child(5) {
        height: 64%;
      }

      span:nth-child(6) {
        height: 88%;
      }

      span:nth-child(7) {
        height: 58%;
      }
    }

    &__actions {
      min-width: 0;
      padding-top: 2px;
    }

    &__info {
      min-width: 0;
    }

    &__meta {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      min-width: 0;
      padding: 0 2px;

      h3 {
        margin: 0;
        color: var(--app-text-color);
        font-size: 17px;
        font-weight: 700;
        line-height: 24px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      p {
        margin: 2px 0 0;
        color: var(--app-icon-color);
        line-height: 20px;
      }
    }

    @media (max-width: 520px) {
      &__showcase {
        min-height: 190px;
        padding: 18px;
      }

      &__brand strong {
        font-size: 22px;
        line-height: 28px;
      }

      &__mock {
        left: 10%;
        grid-template-columns: minmax(0, 1fr);
      }

      &__mock-side {
        display: none;
      }
    }
  }

  :deep(html.dark) {
    .theme-card {
      background: var(--app-card-bg, var(--app-surface-bg));
      border-color: var(--app-card-border-color, var(--app-border-color));

      &__brand strong {
        color: #fff;
      }

      &__showcase {
        background:
          radial-gradient(circle at 3px 3px, color-mix(in srgb, var(--preview-primary) 26%, transparent) 1.4px, transparent 1.6px) 0 0 / 16px 16px,
          linear-gradient(135deg, color-mix(in srgb, var(--preview-nav) 82%, var(--preview-primary)), color-mix(in srgb, #111827 72%, var(--preview-primary)));
      }

      &__mock-main {
        background: color-mix(in srgb, #111827 88%, var(--preview-primary));
        border-color: rgba(255, 255, 255, 0.14);
      }
    }
  }

  .appearance-studio-page {
    display: grid;
    gap: 16px;
    padding: var(--app-content-padding);

    &__header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;

      p {
        margin: 4px 0 0;
        color: var(--app-icon-color);
        line-height: 22px;
      }
    }

    &__title-row {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
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
        transition: background 0.16s ease;
      }

      :deep(.n-input__border),
      :deep(.n-input__state-border) {
        border-color: transparent;
      }

      :deep(.n-input__input) {
        height: 38px;
      }

      :deep(.n-input__input-el) {
        height: 38px;
        color: var(--app-text-color);
        font-size: 22px;
        font-weight: 650;
        line-height: 38px;
      }

      :deep(.n-input__placeholder) {
        font-size: 22px;
        font-weight: 650;
      }

      &:hover,
      &:focus-within {
        :deep(.n-input-wrapper) {
          background: color-mix(in srgb, var(--app-hover-color) 76%, transparent);
        }
      }

      &:focus-within {
        :deep(.n-input__state-border) {
          border-color: transparent transparent var(--app-primary-color) transparent;
          border-radius: 0;
          box-shadow: none;
        }
      }
    }

    &__panel {
      min-height: 640px;
    }
  }
</style>
