<template>
  <n-config-provider :theme-overrides="appearanceStore.editorThemeOverrides">
    <section
      class="theme-preview"
      :class="appearanceStore.editorEffectiveSkinClass"
      :style="previewCssVars"
    >
      <header class="theme-preview__header">
        <div>
          <span>{{ previewMeta.kicker }}</span>
          <strong>{{ previewMeta.title }}</strong>
          <p>{{ previewMeta.description }}</p>
        </div>
      </header>

      <div class="theme-preview__stage">
        <section v-if="previewMode === 'preset'" class="sample-panel preset-preview">
          <div class="sample-heading">
            <span>Preset</span>
            <strong>{{ appearanceStore.editorPreset.name }}</strong>
          </div>
          <p class="sample-note">{{ appearanceStore.editorPreset.description }}</p>

          <div class="preset-strip">
            <span v-for="item in primarySwatches" :key="item.label" :style="{ background: item.value }">
              {{ item.label }}
            </span>
          </div>

          <div class="preset-preview__surface">
            <div>
              <strong>功能点复核</strong>
              <span>当前预设会同步影响主色、内容面、边框、字号和按钮质感。</span>
            </div>
            <button class="sample-button sample-button--primary" type="button">保存配置</button>
          </div>
        </section>

        <section v-else-if="previewMode === 'color'" class="sample-panel color-preview">
          <div class="sample-heading">
            <span>Color System</span>
            <strong>颜色落地样张</strong>
          </div>

          <div class="color-preview__grid">
            <div v-for="item in colorSwatches" :key="item.label" class="color-chip">
              <i :style="{ background: item.value }"></i>
              <span>{{ item.label }}</span>
              <em>{{ item.value }}</em>
            </div>
          </div>

          <div class="color-preview__surface">
            <strong>业务内容面</strong>
            <p>页面背景、内容面、边框和正文色会在这里形成真实层次。</p>
            <div>
              <span class="status-pill status-pill--info">草稿</span>
              <span class="status-pill status-pill--success">已匹配</span>
              <span class="status-pill status-pill--warning">待复核</span>
            </div>
          </div>
        </section>

        <section v-else-if="previewMode === 'visual'" class="sample-panel visual-preview">
          <div class="sample-heading">
            <span>{{ visualPreviewMeta.kicker }}</span>
            <strong>{{ visualPreviewMeta.title }}</strong>
          </div>

          <div v-if="visualTarget === 'type'" class="type-showcase">
            <div>
              <strong>Aa</strong>
              <span>Take what you want.</span>
            </div>
            <div>
              <strong>123</strong>
              <span>0123456789</span>
            </div>
            <div>
              <strong>速</strong>
              <span>速搭你所想</span>
            </div>
          </div>

          <div v-if="visualTarget === 'type'" class="type-scale">
            <div v-for="item in fontRows" :key="item.label" class="type-scale__row">
              <span>
                <em>{{ item.token }}</em>
                {{ item.value }} · {{ item.label }}
              </span>
              <strong :style="{ fontSize: item.value }">速搭你所想</strong>
            </div>
          </div>

          <div v-if="visualTarget === 'radius'" class="radius-focus">
            <div
              v-for="item in radiusRows"
              :key="item.label"
              :style="{ borderRadius: item.value, boxShadow: item.shadow }"
            >
              <strong>{{ item.label }}</strong>
              <span>{{ item.value }}</span>
            </div>
          </div>

          <div v-if="visualTarget === 'radius'" class="radius-grid">
            <span
              v-for="item in radiusRows"
              :key="item.label"
              :style="{ borderRadius: item.value, boxShadow: item.shadow }"
            >
              {{ item.label }} {{ item.value }}
            </span>
          </div>

          <div v-if="visualTarget === 'shadow'" class="shadow-focus">
            <div :style="{ boxShadow: tokens.primitive.shadowNone }">
              <strong>无阴影</strong>
              <span>{{ tokens.primitive.shadowNone }}</span>
            </div>
            <div :style="{ boxShadow: tokens.primitive.shadowSm }">
              <strong>弱阴影</strong>
              <span>{{ tokens.primitive.shadowSm }}</span>
            </div>
            <div :style="{ boxShadow: tokens.primitive.shadowMd }">
              <strong>中阴影</strong>
              <span>{{ tokens.primitive.shadowMd }}</span>
            </div>
          </div>

          <div v-if="visualTarget !== 'type'" class="field-sample">
            <button class="sample-button sample-button--primary" type="button">主要操作</button>
            <label>
              <span>输入框</span>
              <input value="圆角和字号会同步变化" readonly />
            </label>
          </div>
        </section>

        <section v-else-if="previewMode === 'component'" class="sample-panel component-preview">
          <div class="sample-heading">
            <span>{{ componentPreviewMeta.kicker }}</span>
            <strong>{{ componentPreviewMeta.title }}</strong>
          </div>

          <div v-if="componentTarget === 'Button'" class="button-matrix">
            <div class="button-matrix__head">
              <span>类型</span>
              <span>常规</span>
              <span>悬停</span>
              <span>点击</span>
              <span>禁用</span>
            </div>
            <div v-for="row in buttonRows" :key="row.label" class="button-matrix__row">
              <strong>{{ row.label }}</strong>
              <button
                v-for="state in buttonStates"
                :key="state.key"
                type="button"
                :disabled="state.key === 'disabled'"
                :style="buttonStyle(row, state.key)"
              >
                {{ state.label }}
              </button>
            </div>
          </div>

          <div v-if="componentTarget === 'Field'" class="field-sample component-preview__fields component-preview__fields--focus">
            <label>
              <span>输入框</span>
              <input value="功能点关键词" readonly />
            </label>
            <label>
              <span>下拉框</span>
              <select value="review" disabled>
                <option value="review">待复核</option>
              </select>
            </label>
          </div>

          <div v-if="componentTarget === 'DataTable'" class="table-sample table-sample--focus">
            <div class="table-sample__head">
              <span>名称</span>
              <span>状态</span>
              <span>操作</span>
            </div>
            <div v-for="row in tableRows" :key="row.name" class="table-sample__row">
              <span>{{ row.name }}</span>
              <span :class="['status-pill', `status-pill--${row.tone}`]">{{ row.status }}</span>
              <span class="table-actions">
                <button type="button">查看</button>
                <button type="button">复核</button>
              </span>
            </div>
          </div>

          <div v-if="componentTarget === 'StatusAction'" class="status-action-preview">
            <div>
              <span class="status-pill status-pill--success">已匹配</span>
              <span class="status-pill status-pill--warning">待复核</span>
              <span class="status-pill status-pill--error">错误</span>
              <span class="status-pill status-pill--info">草稿</span>
            </div>
            <div class="table-actions">
              <button type="button">查看</button>
              <button type="button">复核</button>
              <button type="button">分配</button>
            </div>
          </div>

          <div v-if="componentTarget === 'Shell'" class="shell-component-preview">
            <aside>
              <strong>ops</strong>
              <span class="is-active">主题管理</span>
              <span>租户管理</span>
              <span>角色权限</span>
            </aside>
            <main>
              <div></div>
              <section></section>
              <section></section>
            </main>
          </div>
        </section>

        <section v-else-if="previewMode === 'layout'" class="sample-panel layout-preview">
          <div class="sample-heading">
            <span>Layout</span>
            <strong>布局比例示意</strong>
          </div>

          <div class="layout-metrics">
            <span>顶栏 {{ layout.headerHeight }}px</span>
            <span>菜单 {{ layout.menuWidth }}px</span>
            <span>折叠 {{ layout.collapsedMenuWidth }}px</span>
            <span>内容 {{ layout.contentPadding }}px</span>
          </div>

          <div class="layout-wireframe">
            <i class="layout-wireframe__menu" :style="{ width: `${previewMenuWidth}px` }"></i>
            <div>
              <i class="layout-wireframe__header" :style="{ height: `${previewHeaderHeight}px` }"></i>
              <main :style="{ padding: `${previewContentPadding}px` }">
                <span></span>
                <span></span>
                <span></span>
              </main>
            </div>
          </div>
        </section>

        <section v-else-if="previewMode === 'behavior'" class="sample-panel behavior-preview">
          <div class="sample-heading">
            <span>Behavior</span>
            <strong>界面行为状态</strong>
          </div>

          <div class="behavior-list">
            <div>
              <span>导航模式</span>
              <strong>{{ projectConfig.navMode }}</strong>
            </div>
            <div>
              <span>导航风格</span>
              <strong>{{ projectConfig.navTheme }}</strong>
            </div>
            <div>
              <span>面包屑</span>
              <strong>{{ projectConfig.crumbsSetting.show ? '显示' : '隐藏' }}</strong>
            </div>
            <div>
              <span>多页签</span>
              <strong>{{ projectConfig.multiTabsSetting.show ? '显示' : '隐藏' }}</strong>
            </div>
          </div>

          <div v-if="projectConfig.multiTabsSetting.show" class="behavior-tabs">
            <span>平台管理</span>
            <span>租户管理</span>
            <span class="is-active">主题管理</span>
          </div>
        </section>

        <section v-else class="sample-panel io-preview">
          <div class="sample-heading">
            <span>Import / Export</span>
            <strong>{{ appearanceStore.editingThemeName || '未命名主题' }}</strong>
          </div>
          <p class="sample-note">导入内容会先进入当前编辑草稿，保存发布后才会成为平台主题资产。</p>
          <div class="io-flow">
            <span>导入 JSON</span>
            <span>进入草稿</span>
            <span>保存主题</span>
            <span>发布使用</span>
          </div>
        </section>
      </div>
    </section>
  </n-config-provider>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';

  const props = defineProps<{
    activePanel: string;
    previewTarget?: string;
  }>();

  const appearanceStore = useAppearanceStore();
  const tokens = computed(() => appearanceStore.editorResolvedTokens);
  const layout = computed(() => appearanceStore.editorLayoutConfig);
  const projectConfig = computed(() => appearanceStore.editorProjectConfig);

  type PreviewMode = 'preset' | 'color' | 'visual' | 'component' | 'layout' | 'behavior' | 'io';
  type ButtonTone = 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error';
  type ButtonState = 'default' | 'hover' | 'pressed' | 'disabled';

  const previewMode = computed<PreviewMode>(() => {
    if (props.activePanel === 'presets') return 'preset';
    if (props.activePanel === 'primitive' || props.activePanel === 'semantic') return 'color';
    if (props.activePanel === 'visual') return 'visual';
    if (props.activePanel === 'components') return 'component';
    if (props.activePanel === 'layout') return 'layout';
    if (props.activePanel === 'behavior') return 'behavior';
    return 'io';
  });

  const previewMeta = computed(() => {
    const map: Record<PreviewMode, { kicker: string; title: string; description: string }> = {
      preset: {
        kicker: 'Preset',
        title: '主题整体效果',
        description: '先看当前预设的基础气质，再进入变量微调。',
      },
      color: {
        kicker: 'Color',
        title: '颜色落地效果',
        description: '聚焦主色、状态色、背景、边框和文字色的组合关系。',
      },
      visual: {
        kicker: 'Visual',
        title: '全局视觉效果',
        description: '字体层级、圆角、阴影在同一个轻量画布中即时反馈。',
      },
      component: {
        kicker: 'Component',
        title: '组件最终效果',
        description: '只展示高频组件本身，方便判断按钮、表单、状态和表格是否成体系。',
      },
      layout: {
        kicker: 'Layout',
        title: '布局比例示意',
        description: '用结构示意判断壳层比例和工作区密度，不再塞完整页面。',
      },
      behavior: {
        kicker: 'Behavior',
        title: '界面行为状态',
        description: '确认导航、多页签和显示项的当前开关状态。',
      },
      io: {
        kicker: 'Config',
        title: '配置流转样张',
        description: '确认导入导出的影响范围和主题资产流转路径。',
      },
    };
    return map[previewMode.value];
  });

  const previewMenuWidth = computed(() => Math.max(44, Math.min(88, layout.value.menuWidth * 0.32)));
  const previewHeaderHeight = computed(() => Math.max(28, Math.min(48, layout.value.headerHeight * 0.68)));
  const previewContentPadding = computed(() => Math.max(8, Math.min(18, layout.value.contentPadding)));
  const visualTarget = computed(() => props.previewTarget || 'radius');
  const componentTarget = computed(() => props.previewTarget || 'Button');

  const visualPreviewMeta = computed(() => {
    const map: Record<string, { kicker: string; title: string }> = {
      radius: { kicker: 'Radius', title: '圆角形态样张' },
      type: { kicker: 'Typography', title: '字体层级样张' },
      shadow: { kicker: 'Shadow', title: '阴影层级样张' },
    };
    return map[visualTarget.value] || map.radius;
  });

  const componentPreviewMeta = computed(() => {
    const map: Record<string, { kicker: string; title: string }> = {
      Button: { kicker: 'Button', title: '按钮状态样张' },
      Field: { kicker: 'Field', title: '表单控件样张' },
      DataTable: { kicker: 'Data Table', title: '数据表格样张' },
      StatusAction: { kicker: 'Status / Action', title: '状态与操作样张' },
      Shell: { kicker: 'Shell', title: '外壳与内容面样张' },
    };
    return map[componentTarget.value] || map.Button;
  });

  const colorSwatches = computed(() => [
    { label: '主色', value: tokens.value.semantic.primaryColor },
    { label: '悬停', value: tokens.value.semantic.primaryColorHover },
    { label: '成功', value: tokens.value.semantic.successColor },
    { label: '警告', value: tokens.value.semantic.warningColor },
    { label: '错误', value: tokens.value.semantic.errorColor },
    { label: '页面', value: tokens.value.semantic.pageBgColor },
    { label: '内容面', value: tokens.value.semantic.surfaceColor },
    { label: '边框', value: tokens.value.semantic.borderColorBase },
  ]);

  const primarySwatches = computed(() => colorSwatches.value.slice(0, 6));

  const previewCssVars = computed(() => ({
    ...appearanceStore.editorCssVars,
    '--app-font-size': tokens.value.semantic.fontSizeBase,
    '--app-button-height': tokens.value.component.Button.height,
    '--app-button-padding-x': tokens.value.component.Button.paddingX,
    '--app-button-radius': tokens.value.component.Button.radius,
    '--app-button-primary-bg': tokens.value.component.Button.primaryBg,
    '--app-button-primary-text': tokens.value.component.Button.primaryText,
    '--app-input-height': tokens.value.component.Input.height,
    '--app-table-header-bg': tokens.value.component.DataTable.headerBg,
    '--app-table-action-height': tokens.value.component.TableAction.buttonHeight,
    '--app-table-action-padding-x': tokens.value.component.TableAction.buttonPaddingX,
    '--app-table-action-radius': tokens.value.component.TableAction.buttonRadius,
  }));

  const fontRows = computed(() => [
    { token: '--font-size-lg', label: '大号', value: tokens.value.primitive.fontSizeLg },
    { token: '--font-size-md', label: '基础', value: tokens.value.primitive.fontSizeMd },
    { token: '--font-size-sm', label: '小号', value: tokens.value.primitive.fontSizeSm },
    { token: '--font-size-xs', label: '辅助', value: tokens.value.primitive.fontSizeXs },
  ]);

  const radiusRows = computed(() => [
    { label: 'XS', value: tokens.value.primitive.radiusXs, shadow: tokens.value.primitive.shadowNone },
    { label: 'SM', value: tokens.value.primitive.radiusSm, shadow: tokens.value.primitive.shadowNone },
    { label: 'MD', value: tokens.value.primitive.radiusMd, shadow: tokens.value.primitive.shadowSm },
    { label: 'LG', value: tokens.value.primitive.radiusLg, shadow: tokens.value.primitive.shadowMd },
  ]);

  const buttonStates: Array<{ key: ButtonState; label: string }> = [
    { key: 'default', label: '常规' },
    { key: 'hover', label: '悬停' },
    { key: 'pressed', label: '点击' },
    { key: 'disabled', label: '禁用' },
  ];

  const buttonRows: Array<{ label: string; tone: ButtonTone; token: string }> = [
    { label: '默认按钮', tone: 'default', token: 'default' },
    { label: '主要按钮', tone: 'primary', token: 'primary' },
    { label: '信息按钮', tone: 'info', token: 'info' },
    { label: '成功按钮', tone: 'success', token: 'success' },
    { label: '警告按钮', tone: 'warning', token: 'warning' },
    { label: '错误按钮', tone: 'error', token: 'error' },
  ];

  const tableRows = [
    { name: '文档上传', status: '已匹配', tone: 'success' },
    { name: '审批流程', status: '待复核', tone: 'warning' },
    { name: '档案检索', status: '草稿', tone: 'info' },
  ];

  function toneColor(tone: ButtonTone, state: Exclude<ButtonState, 'disabled'>) {
    const semantic = tokens.value.semantic;
    if (tone === 'default') {
      if (state === 'hover') return semantic.surfaceMutedColor;
      if (state === 'pressed') return semantic.borderColorBase;
      return semantic.surfaceColor;
    }
    if (tone === 'primary') {
      if (state === 'hover') return tokens.value.component.Button.primaryBgHover;
      if (state === 'pressed') return tokens.value.component.Button.primaryBgPressed;
      return tokens.value.component.Button.primaryBg;
    }
    const toneMap = {
      info: semantic.infoColor,
      success: semantic.successColor,
      warning: semantic.warningColor,
      error: semantic.errorColor,
    };
    return shiftColor(toneMap[tone], state);
  }

  function shiftColor(color: string, state: Exclude<ButtonState, 'disabled'>) {
    if (state === 'hover') return `color-mix(in srgb, ${color} 86%, #ffffff)`;
    if (state === 'pressed') return `color-mix(in srgb, ${color} 84%, #0f172a)`;
    return color;
  }

  function buttonStyle(row: { tone: ButtonTone }, state: ButtonState) {
    const semantic = tokens.value.semantic;
    const component = tokens.value.component.Button;
    if (state === 'disabled') {
      return {
        color: semantic.textColorMuted,
        background: semantic.surfaceMutedColor,
        borderColor: semantic.borderColorBase,
      };
    }
    const background = toneColor(row.tone, state);
    const isDefault = row.tone === 'default';
    return {
      minHeight: component.height,
      padding: `0 ${component.paddingX}`,
      color: isDefault ? semantic.textColorBase : component.primaryText,
      background,
      borderColor: isDefault ? component.borderColor : background,
      borderRadius: component.radius,
    };
  }
</script>

<style lang="less" scoped>
  .theme-preview {
    display: grid;
    gap: 14px;
    min-width: 0;
    min-height: 620px;
    padding: 0;
    color: var(--app-text-color);
    background: transparent;
    border: 0;
    border-radius: 0;
  }

  .theme-preview__header {
    min-width: 0;
    padding: 2px 4px 0;

    div {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    span {
      color: var(--app-primary-color);
      font-size: 12px;
      font-weight: 700;
      line-height: 18px;
    }

    strong {
      color: var(--app-text-color);
      font-size: 18px;
      font-weight: 750;
      line-height: 26px;
    }

    p {
      margin: 0;
      color: var(--app-icon-color);
      font-size: 12px;
      line-height: 18px;
    }
  }

  .theme-preview__stage {
    min-width: 0;
  }

  .sample-panel {
    display: grid;
    align-content: start;
    gap: 18px;
    min-width: 0;
    min-height: 560px;
    padding: clamp(18px, 2.4vw, 28px);
    background: var(--app-page-bg);
    border: 0;
    border-radius: 8px;
  }

  .sample-heading {
    display: grid;
    gap: 2px;
    min-width: 0;

    span {
      color: var(--app-icon-color);
      font-size: 12px;
      font-weight: 700;
      line-height: 18px;
    }

    strong {
      color: var(--app-text-color);
      font-size: 16px;
      font-weight: 750;
      line-height: 24px;
    }
  }

  .sample-note {
    margin: 0;
    color: var(--app-icon-color);
    line-height: 22px;
  }

  .preset-strip,
  .color-preview__grid,
  .radius-grid,
  .layout-metrics,
  .io-flow {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .preset-strip span {
    display: flex;
    align-items: flex-end;
    min-height: 58px;
    padding: 8px;
    overflow: hidden;
    color: var(--app-text-color);
    font-size: 12px;
    font-weight: 650;
    line-height: 18px;
    border: 1px solid color-mix(in srgb, var(--app-border-color) 68%, transparent);
    border-radius: var(--app-card-radius);
  }

  .preset-preview__surface,
  .color-preview__surface,
  .field-sample,
  .behavior-list div {
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color) 76%, transparent);
    border-radius: var(--app-card-radius);
  }

  .preset-preview__surface {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
    padding: 12px;

    div {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    strong,
    span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: var(--app-icon-color);
      font-size: 12px;
    }
  }

  .color-chip {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 2px 8px;
    align-items: center;
    min-width: 0;
    padding: 8px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color) 68%, transparent);
    border-radius: var(--app-card-radius);

    i {
      grid-row: 1 / 3;
      width: 34px;
      height: 34px;
      border: 1px solid color-mix(in srgb, var(--app-border-color) 68%, transparent);
      border-radius: 7px;
    }

    span {
      color: var(--app-text-color);
      font-size: 13px;
      font-weight: 650;
      line-height: 18px;
    }

    em {
      overflow: hidden;
      color: var(--app-icon-color);
      font-size: 12px;
      font-style: normal;
      line-height: 18px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .color-preview__surface {
    display: grid;
    gap: 8px;
    padding: 12px;

    p {
      margin: 0;
      color: var(--app-icon-color);
      line-height: 22px;
    }

    div {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
  }

  .type-showcase {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    padding: 44px 18px;
    background: var(--app-surface-bg);
    border: 0;
    border-radius: 8px;

    div {
      display: grid;
      gap: 8px;
      place-items: center;
      min-width: 0;
    }

    strong {
      color: var(--app-text-color);
      font-size: clamp(44px, 5vw, 72px);
      font-weight: 780;
      line-height: 1;
    }

    span {
      max-width: 100%;
      color: var(--app-icon-color);
      font-size: 14px;
      line-height: 20px;
      text-align: center;
      overflow-wrap: anywhere;
    }
  }

  .type-scale {
    display: grid;
    gap: 8px;
  }

  .type-scale__row {
    display: grid;
    grid-template-columns: 94px minmax(0, 1fr);
    gap: 10px;
    align-items: center;
    min-width: 0;
    min-height: 54px;
    padding: 10px 12px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color) 76%, transparent);
    border-radius: var(--app-card-radius);

    span {
      display: grid;
      color: var(--app-icon-color);
      font-size: 12px;
      line-height: 18px;
    }

    em {
      color: var(--app-text-color);
      font-style: normal;
      font-weight: 650;
    }

    strong {
      overflow: hidden;
      color: var(--app-text-color);
      line-height: 1.35;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .radius-grid span,
  .layout-metrics span,
  .io-flow span {
    display: grid;
    min-height: 48px;
    padding: 8px;
    color: var(--app-primary-color);
    font-weight: 650;
    place-items: center;
    background: color-mix(in srgb, var(--app-primary-color) 10%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-primary-color) 28%, var(--app-border-color));
  }

  .radius-focus {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;

    div {
      display: grid;
      gap: 6px;
      min-height: 96px;
      padding: 14px;
      background: var(--app-surface-bg);
      border: 0;
    }

    strong {
      color: var(--app-primary-color);
      font-size: 24px;
      line-height: 1.2;
    }

    span {
      color: var(--app-icon-color);
      font-weight: 650;
    }
  }

  .shadow-focus {
    display: grid;
    gap: 12px;

    div {
      display: grid;
      gap: 6px;
      min-height: 82px;
      padding: 16px;
      background: var(--app-surface-bg);
      border: 0;
      border-radius: var(--app-card-radius);
    }

    strong {
      color: var(--app-text-color);
      font-size: 15px;
    }

    span {
      overflow: hidden;
      color: var(--app-icon-color);
      font-size: 12px;
      line-height: 18px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .field-sample {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 10px;
    align-items: end;
    padding: 12px;

    label {
      display: grid;
      gap: 6px;
      min-width: 0;
    }

    span {
      color: var(--app-icon-color);
      font-size: 12px;
      line-height: 18px;
    }

    input,
    select {
      width: 100%;
      min-width: 0;
      height: var(--app-input-height, 34px);
      padding: 0 10px;
      color: var(--app-text-color);
      background: var(--app-surface-bg);
      border: 1px solid color-mix(in srgb, var(--app-border-color) 76%, transparent);
      border-radius: var(--app-card-radius);
      outline: 0;
    }

    input:focus {
      border-color: var(--app-primary-color);
    }
  }

  .component-preview__fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .component-preview__fields--focus {
    min-height: 180px;
    align-items: center;
  }

  .sample-button,
  .button-matrix button,
  .table-actions button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    min-width: 0;
    white-space: nowrap;
    cursor: default;
    border: 1px solid;
    transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease;
  }

  .sample-button {
    min-height: var(--app-button-height, 34px);
    padding: 0 var(--app-button-padding-x, 12px);
    border-radius: var(--app-button-radius, var(--app-card-radius));
  }

  .sample-button--primary {
    color: var(--app-button-primary-text, #fff);
    background: var(--app-button-primary-bg, var(--app-primary-color));
    border-color: var(--app-button-primary-bg, var(--app-primary-color));
  }

  .button-matrix {
    display: grid;
    min-width: 0;
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color) 76%, transparent);
    border-radius: var(--app-card-radius);
  }

  .button-matrix__head,
  .button-matrix__row {
    display: grid;
    grid-template-columns: minmax(70px, 0.9fr) repeat(4, minmax(54px, 1fr));
    gap: 8px;
    align-items: center;
    min-width: 0;
    padding: 9px 10px;
  }

  .button-matrix__head {
    color: var(--app-icon-color);
    font-size: 12px;
    font-weight: 650;
    background: var(--app-surface-muted-bg);
  }

  .button-matrix__row {
    border-top: 1px solid color-mix(in srgb, var(--app-border-color) 72%, transparent);

    strong {
      overflow: hidden;
      color: var(--app-text-color);
      font-size: 13px;
      line-height: 20px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    button {
      min-width: 0;
      height: var(--app-button-height, 34px);
      padding: 0 8px;
      overflow: hidden;
      font-size: 12px;
      text-overflow: ellipsis;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.68;
    }
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: var(--app-status-tag-height, 24px);
    padding: 0 var(--app-status-tag-padding-x, 8px);
    font-size: 12px;
    font-weight: var(--app-status-tag-font-weight, 500);
    line-height: 1;
    white-space: nowrap;
    border: 1px solid;
    border-radius: var(--app-status-tag-radius, var(--app-card-radius));
  }

  .status-pill--success {
    color: var(--app-status-success-text);
    background: var(--app-status-success-bg);
    border-color: var(--app-status-success-border);
  }

  .status-pill--warning {
    color: var(--app-status-warning-text);
    background: var(--app-status-warning-bg);
    border-color: var(--app-status-warning-border);
  }

  .status-pill--error {
    color: var(--app-status-error-text);
    background: var(--app-status-error-bg);
    border-color: var(--app-status-error-border);
  }

  .status-pill--info {
    color: var(--app-status-info-text);
    background: var(--app-status-info-bg);
    border-color: var(--app-status-info-border);
  }

  .table-sample {
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color) 76%, transparent);
    border-radius: var(--app-table-radius);
  }

  .table-sample__head,
  .table-sample__row {
    display: grid;
    grid-template-columns: minmax(88px, 1fr) auto minmax(86px, auto);
    gap: 8px;
    align-items: center;
    min-width: 0;
    min-height: 38px;
    padding: 8px 10px;
  }

  .table-sample__head {
    color: var(--app-icon-color);
    font-size: 12px;
    font-weight: 650;
    background: var(--app-table-header-bg, var(--app-surface-muted-bg));
  }

  .table-sample__row {
    color: var(--app-text-color);
    border-top: 1px solid color-mix(in srgb, var(--app-border-color) 72%, transparent);

    &:nth-child(odd) {
      background: var(--app-surface-muted-bg);
    }
  }

  .table-actions {
    display: inline-flex;
    gap: var(--app-table-action-gap, 8px);
    justify-content: flex-end;

    button {
      height: var(--app-table-action-height, 30px);
      padding: 0 var(--app-table-action-padding-x, 12px);
      color: var(--app-primary-color);
      background: transparent;
      border-color: color-mix(in srgb, var(--app-border-color) 76%, transparent);
      border-radius: var(--app-table-action-radius, var(--app-card-radius));
    }
  }

  .table-sample--focus {
    min-height: 228px;
  }

  .status-action-preview {
    display: grid;
    gap: 16px;
    min-height: 188px;
    padding: 16px;
    background: var(--app-surface-bg);
    border: 0;
    border-radius: var(--app-card-radius);

    > div:first-child {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-content: start;
    }

    .table-actions {
      justify-content: flex-start;
    }
  }

  .shell-component-preview {
    display: grid;
    grid-template-columns: minmax(92px, 0.34fr) minmax(0, 1fr);
    min-height: 260px;
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 0;
    border-radius: var(--app-card-radius);

    aside {
      display: grid;
      align-content: start;
      gap: 10px;
      padding: 14px 12px;
      color: #fff;
      background: var(--app-menu-bg, #172033);
    }

    strong {
      font-size: 18px;
      line-height: 26px;
    }

    aside span {
      min-width: 0;
      padding: 8px 10px;
      overflow: hidden;
      color: rgba(255, 255, 255, 0.74);
      text-overflow: ellipsis;
      white-space: nowrap;
      border-radius: var(--app-card-radius);
    }

    aside .is-active {
      color: #fff;
      background: var(--app-primary-color);
    }

    main {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      padding: 14px;
      background: var(--app-page-bg);
    }

    main div,
    main section {
      min-height: 72px;
      background: var(--app-surface-bg);
      border: 1px solid color-mix(in srgb, var(--app-border-color) 72%, transparent);
      border-radius: var(--app-card-radius);
    }

    main div {
      grid-column: 1 / -1;
      min-height: 42px;
    }
  }

  .layout-wireframe {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    min-height: 220px;
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 0;
    border-radius: var(--app-card-radius);
  }

  .layout-wireframe__menu {
    display: block;
    background:
      linear-gradient(var(--app-primary-color), var(--app-primary-color)) 12px 20px / 60% 10px no-repeat,
      linear-gradient(var(--app-border-color), var(--app-border-color)) 12px 46px / 68% 8px no-repeat,
      linear-gradient(var(--app-border-color), var(--app-border-color)) 12px 68px / 54% 8px no-repeat,
      var(--app-menu-bg, #172033);
  }

  .layout-wireframe > div {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-width: 0;
  }

  .layout-wireframe__header {
    display: block;
    background: var(--app-surface-bg);
    border-bottom: 1px solid var(--app-border-color);
  }

  .layout-wireframe main {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    min-width: 0;
    background: var(--app-page-bg);

    span {
      min-height: 58px;
      background: var(--app-surface-bg);
      border: 1px solid var(--app-border-color);
      border-radius: var(--app-card-radius);
    }

    span:first-child {
      grid-column: 1 / -1;
    }
  }

  .behavior-list {
    display: grid;
    gap: 8px;

    div {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
    }

    span {
      color: var(--app-icon-color);
    }

    strong {
      color: var(--app-text-color);
    }
  }

  .behavior-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    span {
      padding: 7px 10px;
      color: var(--app-icon-color);
      background: var(--app-surface-bg);
      border: 1px solid var(--app-border-color);
      border-radius: var(--app-card-radius);
    }

    .is-active {
      color: var(--app-primary-color);
      border-color: color-mix(in srgb, var(--app-primary-color) 32%, var(--app-border-color));
    }
  }

  .io-flow span {
    position: relative;
    min-height: 42px;
    color: var(--app-text-color);
    background: var(--app-surface-bg);
  }

  @media (max-width: 1280px) {
    .theme-preview {
      padding: 10px;
    }

    .sample-panel {
      gap: 12px;
      padding: 12px;
    }

    .type-showcase {
      gap: 8px;
      padding: 12px 8px;

      strong {
        font-size: 34px;
      }
    }

    .button-matrix__head,
    .button-matrix__row {
      grid-template-columns: minmax(60px, 0.9fr) repeat(4, minmax(46px, 1fr));
      gap: 6px;
      padding: 8px;
    }
  }

  @media (max-width: 720px) {
    .preset-strip,
    .color-preview__grid,
    .radius-focus,
    .radius-grid,
    .layout-metrics,
    .component-preview__fields {
      grid-template-columns: minmax(0, 1fr);
    }

    .field-sample {
      grid-template-columns: minmax(0, 1fr);
    }

    .button-matrix {
      overflow-x: auto;
    }

    .button-matrix__head,
    .button-matrix__row {
      min-width: 460px;
    }

    .shell-component-preview {
      grid-template-columns: minmax(0, 1fr);

      aside {
        display: none;
      }
    }
  }
</style>
