<template>
  <div class="page-designer-studio" :class="{ 'is-fullscreen': fullscreen }">
    <header class="page-designer-studio__toolbar">
      <div class="page-designer-studio__main-tools">
        <n-button quaternary size="small" @click="router.push('/page-designer/pages')">
          <template #icon>
            <n-icon><ArrowLeftOutlined /></n-icon>
          </template>
          页面管理
        </n-button>
        <div class="page-designer-studio__title">
          <strong>{{ page?.name || '页面设计' }}</strong>
          <span>{{ components.length }} 个组件</span>
        </div>
        <n-divider vertical />
        <n-popover v-model:show="widgetPickerVisible" trigger="click" placement="bottom-start" display-directive="show">
          <template #trigger>
            <n-button type="primary" secondary>
              <template #icon>
                <n-icon><PlusOutlined /></n-icon>
              </template>
              添加组件
            </n-button>
          </template>
          <div class="widget-picker">
            <section v-for="group in widgetGroups" :key="group.title" class="widget-picker__group">
              <h3>{{ group.title }}</h3>
              <div class="widget-picker__grid">
                <button v-for="widget in group.items" :key="widget.type" type="button" class="widget-picker__item" @click="addWidget(widget.type)">
                  <span class="widget-picker__icon" :class="`is-${widget.type}`" aria-hidden="true">
                    <i></i>
                    <i></i>
                    <i></i>
                  </span>
                  <strong>{{ widget.label }}</strong>
                </button>
              </div>
            </section>
          </div>
        </n-popover>
        <n-button quaternary>
          <template #icon>
            <n-icon><FilterOutlined /></n-icon>
          </template>
          筛选器
        </n-button>
        <n-button quaternary @click="openConfigure(selectedId)">
          <template #icon>
            <n-icon><FontSizeOutlined /></n-icon>
          </template>
          标题
        </n-button>
        <n-button quaternary>
          <template #icon>
            <n-icon><BgColorsOutlined /></n-icon>
          </template>
          主题
        </n-button>
        <n-button quaternary @click="fullscreen = !fullscreen">
          <template #icon>
            <n-icon><FullscreenOutlined /></n-icon>
          </template>
          {{ fullscreen ? '退出全屏' : '全屏显示' }}
        </n-button>
      </div>

      <n-space class="page-designer-studio__actions" align="center" :size="8">
        <n-button :loading="loading" @click="load">刷新</n-button>
        <n-button :loading="previewing" @click="openPreview">预览</n-button>
        <n-button type="primary" secondary :loading="saving" @click="saveDraft">保存草稿</n-button>
        <n-button type="primary" :loading="publishing" @click="publish">发布</n-button>
      </n-space>
    </header>

    <main class="page-designer-studio__stage">
      <DashboardGridCanvas
        :layout="layout"
        :components="components"
        :selected-id="selectedId"
        @update:layout="assignLayout"
        @select="selectedId = $event"
        @configure="openConfigure"
        @duplicate="duplicateWidget"
        @remove="removeWidget"
      />
    </main>

    <n-modal v-model:show="configVisible" preset="card" class="page-designer-config-modal" :mask-closable="false">
      <template #header>
        <div class="page-designer-config-modal__header">
          <span>{{ selectedDefinition.label }}</span>
          <strong>{{ selectedComponent?.title || '组件配置' }}</strong>
        </div>
      </template>
      <div v-if="selectedComponent" class="page-designer-config">
        <section class="page-designer-config__preview">
          <DashboardGridCanvas :layout="selectedPreviewLayout" :components="[selectedComponent]" readonly />
        </section>
        <section class="page-designer-config__panel">
          <n-tabs type="line" animated>
            <n-tab-pane name="data" tab="类型与数据">
              <n-form label-placement="top">
                <n-form-item label="标题">
                  <n-input v-model:value="selectedComponent.title" placeholder="请输入组件标题" />
                </n-form-item>
                <template v-if="isSelectedDataDriven">
                  <n-form-item label="数据来源">
                    <n-select
                      v-model:value="selectedDataSource.type"
                      :options="dataSourceOptions"
                      @update:value="handleDataSourceTypeChange"
                    />
                  </n-form-item>
                  <n-form-item v-if="selectedDataSource.type === 'static_json'" label="静态 JSON">
                    <CodePreview
                      v-model:value="selectedDataSource.staticJson"
                      language="json"
                      height="260px"
                      :auto-height="false"
                      :read-only="false"
                      class="page-designer-config__json"
                    />
                    <template #feedback>
                      <n-button text type="primary" @click="fillSelectedSampleData">填入当前组件样例</n-button>
                    </template>
                  </n-form-item>
                  <n-form-item v-else label="数据集">
                    <n-select disabled placeholder="后续接入数据集后可选择" />
                  </n-form-item>
                </template>
                <n-form-item v-if="selectedComponent.type === 'metric_card'" label="指标值">
                  <n-input v-model:value="selectedComponent.props.value" placeholder="例如 128.6万" />
                </n-form-item>
                <n-form-item v-if="selectedComponent.type === 'metric_card'" label="趋势">
                  <n-input v-model:value="selectedComponent.props.trend" placeholder="例如 +12.8%" />
                </n-form-item>
                <n-form-item v-if="selectedComponent.type === 'text_block'" label="内容">
                  <n-input v-model:value="selectedComponent.props.content" type="textarea" :autosize="{ minRows: 5, maxRows: 10 }" />
                </n-form-item>
                <n-form-item v-if="selectedComponent.type === 'quick_link'" label="按钮文字">
                  <n-input v-model:value="selectedComponent.props.text" />
                </n-form-item>
                <n-form-item v-if="selectedComponent.type === 'quick_link'" label="跳转地址">
                  <n-input v-model:value="selectedComponent.props.href" />
                </n-form-item>
                <n-form-item v-if="selectedComponent.type === 'data_table'" label="行数">
                  <n-input-number v-model:value="selectedComponent.props.rows" :min="1" :max="20" />
                </n-form-item>
              </n-form>
            </n-tab-pane>
            <n-tab-pane name="style" tab="图表样式">
              <n-form label-placement="top">
                <n-form-item label="组件宽度">
                  <n-input-number v-model:value="selectedLayoutItem.w" :min="2" :max="layout.cols || 24" @update:value="syncSelectedLayout" />
                </n-form-item>
                <n-form-item label="组件高度">
                  <n-input-number v-model:value="selectedLayoutItem.h" :min="2" :max="12" @update:value="syncSelectedLayout" />
                </n-form-item>
                <n-form-item label="横向位置">
                  <n-input-number v-model:value="selectedLayoutItem.x" :min="0" :max="layout.cols || 24" @update:value="syncSelectedLayout" />
                </n-form-item>
                <n-form-item label="纵向位置">
                  <n-input-number v-model:value="selectedLayoutItem.y" :min="0" :max="99" @update:value="syncSelectedLayout" />
                </n-form-item>
              </n-form>
            </n-tab-pane>
          </n-tabs>
        </section>
      </div>
      <template #footer>
        <n-space justify="space-between" align="center">
          <n-button tertiary type="error" @click="removeWidget(selectedId)">删除组件</n-button>
          <n-space>
            <n-button @click="configVisible = false">取消</n-button>
            <n-button type="primary" @click="configVisible = false">确定</n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="previewVisible" preset="card" title="页面预览" class="page-designer-detail__preview">
      <DashboardGridCanvas v-if="previewRuntime" :layout="previewRuntime.layout" :components="previewRuntime.components" readonly />
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import {
    ArrowLeftOutlined,
    BgColorsOutlined,
    FilterOutlined,
    FontSizeOutlined,
    FullscreenOutlined,
    PlusOutlined,
  } from '@vicons/antd';
  import CodePreview from '@/components/CodePreview/index.vue';
  import DashboardGridCanvas from '@/components/PageDesigner/DashboardGridCanvas.vue';
  import {
    chartWidgetTypes,
    defaultDataSourceForWidget,
    isDataDrivenWidget,
    sampleDataJsonForWidget,
    widgetDefinition,
    widgetDefinitions,
    withDefaultDataSource,
    type WidgetDataSourceConfig,
    type WidgetDefinition,
  } from '@/components/PageDesigner/widgets';
  import {
    getPageDesignerPage,
    previewPageDesignerPage,
    publishPageDesignerPage,
    savePageDesignerDraft,
    type DashboardLayout,
    type DashboardLayoutItem,
    type PageComponentConfig,
    type PageDefinition,
    type PageDesignerRuntime,
  } from '@/api/pageDesigner';

  const route = useRoute();
  const router = useRouter();
  const message = useMessage();
  const pageId = Number(route.params.id || 0);
  const loading = ref(false);
  const saving = ref(false);
  const publishing = ref(false);
  const previewing = ref(false);
  const previewVisible = ref(false);
  const widgetPickerVisible = ref(false);
  const configVisible = ref(false);
  const fullscreen = ref(false);
  const page = ref<PageDefinition | null>(null);
  const previewRuntime = ref<PageDesignerRuntime | null>(null);
  const selectedId = ref('');
  const layout = reactive<DashboardLayout>({ cols: 24, rowHeight: 64, items: [] });
  const selectedLayoutItem = reactive<DashboardLayoutItem>({ id: '', type: '', x: 0, y: 0, w: 6, h: 3, props: {} });
  const components = ref<PageComponentConfig[]>([]);

  const selectedComponent = computed(() => components.value.find((component) => component.id === selectedId.value));
  const selectedDefinition = computed(() => widgetDefinition(selectedComponent.value?.type || 'metric_card'));
  const isSelectedDataDriven = computed(() => Boolean(selectedComponent.value && isDataDrivenWidget(selectedComponent.value.type)));
  const selectedDataSource = computed<WidgetDataSourceConfig>({
    get() {
      if (!selectedComponent.value) return defaultDataSourceForWidget('metric_card');
      return ensureComponentDataSource(selectedComponent.value);
    },
    set(value) {
      if (!selectedComponent.value) return;
      selectedComponent.value.props.dataSource = value;
    },
  });
  const selectedPreviewLayout = computed<DashboardLayout>(() => ({
    cols: 12,
    rowHeight: 70,
    items: [{ ...selectedLayoutItem, id: selectedId.value, x: 0, y: 0, w: 12, h: Math.max(3, Math.min(6, selectedLayoutItem.h || 3)) }],
  }));
  const widgetGroups = computed(() => [
    { title: '图表', items: widgetDefinitions.filter((widget) => chartWidgetTypes.includes(widget.type)) },
    { title: '视图', items: widgetDefinitions.filter((widget) => widget.type === 'data_table') },
    { title: '其他', items: widgetDefinitions.filter((widget) => ['text_block', 'quick_link'].includes(widget.type)) },
  ]);
  const dataSourceOptions = [
    { label: '静态 JSON', value: 'static_json' },
    { label: '数据集（即将支持）', value: 'dataset', disabled: true },
  ];

  function assignLayout(nextLayout: DashboardLayout) {
    layout.cols = nextLayout.cols || 24;
    layout.rowHeight = nextLayout.rowHeight || 64;
    layout.items = [...(nextLayout.items || [])];
  }

  function draftPayload() {
    return {
      schema_version: '1.0',
      layout: { ...layout, items: [...layout.items] },
      components: components.value,
      data_bindings: {},
      interactions: {},
    };
  }

  async function load() {
    loading.value = true;
    try {
      const payload = await getPageDesignerPage(pageId);
      page.value = payload.item;
      const version = payload.item.version;
      assignLayout(version?.layout || { cols: 24, rowHeight: 64, items: [] });
      components.value = normalizeComponents(version?.components || []);
      selectedId.value = components.value[0]?.id || '';
    } finally {
      loading.value = false;
    }
  }

  function addWidget(type: string) {
    const definition = widgetDefinition(type);
    const id = `w_${Date.now().toString(36)}`;
    const maxY = layout.items.reduce((value, item) => Math.max(value, item.y + item.h), 0);
    layout.items.push(createLayoutItem(id, type, definition, maxY));
    components.value.push({
      id,
      type,
      title: definition.defaultTitle,
      props: withDefaultDataSource(type, { ...definition.defaultProps }),
    });
    selectedId.value = id;
    widgetPickerVisible.value = false;
  }

  function duplicateWidget(id: string) {
    const sourceComponent = components.value.find((component) => component.id === id);
    const sourceLayout = layout.items.find((item) => item.id === id);
    if (!sourceComponent || !sourceLayout) return;
    const nextId = `w_${Date.now().toString(36)}`;
    layout.items.push({ ...sourceLayout, id: nextId, y: sourceLayout.y + sourceLayout.h, props: { ...(sourceLayout.props || {}) } });
    components.value.push({
      ...sourceComponent,
      id: nextId,
      title: `${sourceComponent.title || widgetDefinition(sourceComponent.type).defaultTitle} 副本`,
      props: withDefaultDataSource(sourceComponent.type, { ...(sourceComponent.props || {}) }),
    });
    selectedId.value = nextId;
  }

  function removeWidget(id: string) {
    if (!id) return;
    layout.items = layout.items.filter((item) => item.id !== id);
    components.value = components.value.filter((component) => component.id !== id);
    selectedId.value = components.value[0]?.id || '';
    if (!selectedId.value) configVisible.value = false;
  }

  function openConfigure(id: string) {
    if (!id) {
      message.warning('请先选择组件');
      return;
    }
    selectedId.value = id;
    syncSelectedLayoutState();
    configVisible.value = true;
  }

  function syncSelectedLayoutState() {
    const item = layout.items.find((layoutItem) => layoutItem.id === selectedId.value);
    if (!item) return;
    selectedLayoutItem.id = item.id;
    selectedLayoutItem.type = item.type;
    selectedLayoutItem.x = item.x;
    selectedLayoutItem.y = item.y;
    selectedLayoutItem.w = item.w;
    selectedLayoutItem.h = item.h;
    selectedLayoutItem.props = item.props || {};
  }

  function syncSelectedLayout() {
    layout.items = layout.items.map((item) => (item.id === selectedId.value ? { ...item, ...selectedLayoutItem } : item));
  }

  function normalizeComponents(items: PageComponentConfig[]) {
    return items.map((component) => ({
      ...component,
      props: withDefaultDataSource(component.type, { ...(component.props || {}) }),
    }));
  }

  function ensureComponentDataSource(component: PageComponentConfig) {
    const props = (component.props ||= {});
    props.dataSource = withDefaultDataSource(component.type, props).dataSource as WidgetDataSourceConfig;
    return props.dataSource;
  }

  function handleDataSourceTypeChange(value: string) {
    if (!selectedComponent.value) return;
    selectedDataSource.value = {
      ...selectedDataSource.value,
      type: value === 'dataset' ? 'dataset' : 'static_json',
      staticJson: selectedDataSource.value.staticJson || sampleDataJsonForWidget(selectedComponent.value.type),
    };
  }

  function fillSelectedSampleData() {
    if (!selectedComponent.value) return;
    selectedDataSource.value = {
      ...selectedDataSource.value,
      type: 'static_json',
      staticJson: sampleDataJsonForWidget(selectedComponent.value.type),
    };
  }

  function createLayoutItem(id: string, type: string, definition: WidgetDefinition, y: number): DashboardLayoutItem {
    return {
      id,
      type,
      x: 0,
      y,
      w: definition.defaultSize.w,
      h: definition.defaultSize.h,
      props: {},
    };
  }

  async function saveDraft() {
    saving.value = true;
    try {
      const payload = await savePageDesignerDraft(pageId, draftPayload());
      page.value = payload.item;
      message.success('草稿已保存');
    } finally {
      saving.value = false;
    }
  }

  async function openPreview() {
    previewing.value = true;
    try {
      const payload = await previewPageDesignerPage(pageId, draftPayload());
      previewRuntime.value = payload.item.runtime;
      previewVisible.value = true;
    } finally {
      previewing.value = false;
    }
  }

  async function publish() {
    await saveDraft();
    publishing.value = true;
    try {
      const payload = await publishPageDesignerPage(pageId);
      page.value = payload.item;
      message.success('页面已发布');
    } finally {
      publishing.value = false;
    }
  }

  load();
</script>

<style lang="less" scoped>
  .page-designer-studio {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-height: calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 24px);
    min-width: 0;
    overflow: hidden;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
  }

  .page-designer-studio.is-fullscreen {
    position: fixed;
    inset: 8px;
    z-index: 3000;
    min-height: auto;
    border-radius: 8px;
    box-shadow: 0 24px 72px rgba(15, 23, 42, 0.22);
  }

  .page-designer-studio__toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
    min-height: 56px;
    padding: 8px 14px;
    background: rgba(255, 255, 255, 0.96);
    border-bottom: 1px solid #e2e8f0;
  }

  .page-designer-studio__main-tools,
  .page-designer-studio__actions {
    min-width: 0;
  }

  .page-designer-studio__main-tools {
    display: flex;
    flex: 1 1 auto;
    align-items: center;
    gap: 6px;
    overflow-x: auto;
    scrollbar-width: thin;
  }

  .page-designer-studio__title {
    display: grid;
    flex: 0 0 auto;
    gap: 1px;
    max-width: 260px;
    padding: 0 8px;

    strong,
    span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: #0f172a;
      font-size: 15px;
      line-height: 20px;
    }

    span {
      color: #64748b;
      font-size: 12px;
      line-height: 16px;
    }
  }

  .page-designer-studio__stage {
    min-width: 0;
    min-height: 0;
    overflow: auto;
    background: #fbfdff;
  }

  .page-designer-studio__stage :deep(.dashboard-grid-canvas) {
    min-height: calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 84px);
    padding: 16px;
    background:
      linear-gradient(#eef2f7 1px, transparent 1px),
      linear-gradient(90deg, #eef2f7 1px, transparent 1px),
      transparent;
    border: 0;
    border-radius: 0;
  }

  .is-fullscreen .page-designer-studio__stage :deep(.dashboard-grid-canvas) {
    min-height: calc(100vh - 80px);
  }

  .widget-picker {
    width: min(520px, calc(100vw - 32px));
    max-height: min(680px, 72vh);
    overflow: auto;
    padding: 6px;
  }

  .widget-picker__group {
    display: grid;
    gap: 10px;
    padding: 10px 6px 14px;
    border-bottom: 1px solid #e2e8f0;

    &:last-child {
      border-bottom: 0;
    }

    h3 {
      margin: 0;
      color: #64748b;
      font-size: 13px;
      font-weight: 650;
      line-height: 18px;
    }
  }

  .widget-picker__grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .widget-picker__item {
    display: grid;
    gap: 8px;
    min-width: 0;
    min-height: 92px;
    padding: 12px 10px;
    color: #1e293b;
    font: inherit;
    text-align: center;
    cursor: pointer;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease,
      transform 0.16s ease;

    &:hover,
    &:focus-visible {
      border-color: #2563eb;
      outline: none;
      box-shadow: 0 10px 22px rgba(37, 99, 235, 0.12);
      transform: translateY(-1px);
    }

    strong {
      overflow: hidden;
      font-size: 13px;
      font-weight: 650;
      line-height: 18px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .widget-picker__icon {
    display: flex;
    align-items: end;
    justify-content: center;
    gap: 5px;
    height: 38px;

    i {
      display: block;
      width: 9px;
      border-radius: 2px 2px 0 0;
      background: #60a5fa;
    }

    i:nth-child(1) {
      height: 20px;
    }

    i:nth-child(2) {
      height: 34px;
      background: #2563eb;
    }

    i:nth-child(3) {
      height: 26px;
      background: #f97316;
    }
  }

  .widget-picker__icon.is_metric_card {
    align-items: center;

    i {
      width: 32px;
      height: 10px;
      border-radius: 999px;
    }
  }

  .widget-picker__icon.is_line_chart i {
    width: 30px;
    height: 4px;
    transform: rotate(-28deg);
    transform-origin: center;
  }

  .widget-picker__icon.is_pie_chart {
    align-items: center;

    i {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      background: conic-gradient(#2563eb 0 42%, #14b8a6 42% 68%, #f97316 68% 100%);
    }
  }

  .widget-picker__icon.is_stacked_area_chart {
    position: relative;
    align-items: end;

    i {
      width: 28px;
      height: 16px;
      border-radius: 12px 12px 2px 2px;
      opacity: 0.76;
      transform: skewX(-18deg);
    }

    i:nth-child(1) {
      height: 18px;
      background: #93c5fd;
    }

    i:nth-child(2) {
      height: 26px;
      background: #5eead4;
    }

    i:nth-child(3) {
      height: 34px;
      background: #fdba74;
    }
  }

  .widget-picker__icon.is_scatter_chart {
    position: relative;
    display: block;

    i {
      position: absolute;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #2563eb;
    }

    i:nth-child(1) {
      left: 18px;
      bottom: 9px;
    }

    i:nth-child(2) {
      left: 32px;
      bottom: 25px;
      background: #14b8a6;
    }

    i:nth-child(3) {
      right: 16px;
      bottom: 16px;
      background: #f97316;
    }
  }

  .widget-picker__icon.is_radar_chart {
    position: relative;
    align-items: center;

    i {
      width: 30px;
      height: 30px;
      clip-path: polygon(50% 0, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%);
      border-radius: 0;
      background: rgba(37, 99, 235, 0.18);
      outline: 2px solid #2563eb;
      outline-offset: -2px;
    }

    i:nth-child(2) {
      position: absolute;
      width: 18px;
      height: 18px;
      background: rgba(20, 184, 166, 0.22);
      outline-color: #14b8a6;
    }

    i:nth-child(3) {
      display: none;
    }
  }

  .widget-picker__icon.is_gauge_chart {
    position: relative;
    align-items: end;

    i {
      width: 34px;
      height: 18px;
      border: 4px solid #2563eb;
      border-bottom: 0;
      border-radius: 34px 34px 0 0;
      background: transparent;
    }

    i:nth-child(2) {
      position: absolute;
      bottom: 7px;
      left: 50%;
      width: 22px;
      height: 3px;
      border: 0;
      border-radius: 999px;
      background: #0f172a;
      transform: translateX(-50%) rotate(-28deg);
      transform-origin: 3px center;
    }

    i:nth-child(3) {
      display: none;
    }
  }

  .widget-picker__icon.is_data_table {
    display: grid;
    grid-template-columns: repeat(3, 12px);
    align-content: center;

    i {
      width: 12px;
      height: 12px;
      border-radius: 2px;
    }
  }

  .widget-picker__icon.is_text_block,
  .widget-picker__icon.is_quick_link {
    display: grid;
    align-content: center;

    i {
      width: 44px;
      height: 6px;
      border-radius: 999px;
    }
  }

  :deep(.page-designer-config-modal) {
    width: min(1480px, calc(100vw - 48px));
  }

  .page-designer-config-modal__header {
    display: flex;
    align-items: baseline;
    gap: 10px;

    span {
      color: #2563eb;
      font-size: 13px;
      font-weight: 650;
    }

    strong {
      color: #0f172a;
      font-size: 18px;
    }
  }

  .page-designer-config {
    display: grid;
    grid-template-columns: minmax(420px, 1fr) 420px;
    gap: 18px;
    min-height: min(720px, 68vh);
  }

  .page-designer-config__preview {
    min-width: 0;
    overflow: auto;
    padding: 12px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
  }

  .page-designer-config__panel {
    min-width: 0;
    padding: 4px 2px;
    border-left: 1px solid #e2e8f0;
    padding-left: 18px;
  }

  .page-designer-config__json {
    min-height: 260px;
    border: 1px solid #dbe3ee;
    border-radius: 6px;
  }

  .page-designer-detail__preview {
    width: min(1200px, 92vw);
  }

  @media (max-width: 1100px) {
    .page-designer-studio {
      min-height: calc(100vh - var(--app-header-height, 64px) - 24px);
    }

    .page-designer-studio__toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .page-designer-studio__actions {
      width: 100%;
    }

    .page-designer-config {
      grid-template-columns: 1fr;
    }

    .page-designer-config__panel {
      padding-left: 0;
      border-left: 0;
    }
  }
</style>
