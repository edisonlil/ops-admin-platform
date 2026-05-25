<template>
  <div class="page-designer-detail">
    <div class="page-designer-detail__header">
      <div>
        <n-button text @click="router.push('/page-designer/pages')">返回页面管理</n-button>
        <h1>{{ page?.name || '页面设计' }}</h1>
        <p>{{ page?.description || '拖拽组件并配置仪表盘布局' }}</p>
      </div>
      <n-space>
        <n-button :loading="loading" @click="load">刷新</n-button>
        <n-button :loading="previewing" @click="openPreview">预览</n-button>
        <n-button type="primary" :loading="saving" @click="saveDraft">保存草稿</n-button>
        <n-button type="success" :loading="publishing" @click="publish">发布</n-button>
      </n-space>
    </div>

    <div class="page-designer-detail__workspace">
      <aside class="page-designer-detail__palette">
        <h2>组件</h2>
        <button v-for="widget in widgetDefinitions" :key="widget.type" type="button" @click="addWidget(widget.type)">
          <strong>{{ widget.label }}</strong>
          <span>{{ widget.defaultTitle }}</span>
        </button>
      </aside>

      <main class="page-designer-detail__canvas">
        <DashboardGridCanvas v-model:layout="layout" :components="components" :selected-id="selectedId" @select="selectedId = $event" />
      </main>

      <aside class="page-designer-detail__props">
        <h2>属性</h2>
        <template v-if="selectedComponent">
          <n-form label-placement="top">
            <n-form-item label="标题">
              <n-input v-model:value="selectedComponent.title" />
            </n-form-item>
            <n-form-item v-if="selectedComponent.type === 'metric_card'" label="指标值">
              <n-input v-model:value="selectedComponent.props.value" />
            </n-form-item>
            <n-form-item v-if="selectedComponent.type === 'metric_card'" label="趋势">
              <n-input v-model:value="selectedComponent.props.trend" />
            </n-form-item>
            <n-form-item v-if="selectedComponent.type === 'text_block'" label="内容">
              <n-input v-model:value="selectedComponent.props.content" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
            </n-form-item>
            <n-form-item v-if="selectedComponent.type === 'quick_link'" label="按钮文字">
              <n-input v-model:value="selectedComponent.props.text" />
            </n-form-item>
            <n-form-item v-if="selectedComponent.type === 'quick_link'" label="跳转地址">
              <n-input v-model:value="selectedComponent.props.href" />
            </n-form-item>
            <n-button block tertiary type="error" @click="removeSelected">删除组件</n-button>
          </n-form>
        </template>
        <n-empty v-else description="请选择画布组件" />
      </aside>
    </div>

    <n-modal v-model:show="previewVisible" preset="card" title="页面预览" class="page-designer-detail__preview">
      <DashboardGridCanvas v-if="previewRuntime" :layout="previewRuntime.layout" :components="previewRuntime.components" readonly />
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import DashboardGridCanvas from '@/components/PageDesigner/DashboardGridCanvas.vue';
  import { widgetDefinition, widgetDefinitions } from '@/components/PageDesigner/widgets';
  import {
    getPageDesignerPage,
    previewPageDesignerPage,
    publishPageDesignerPage,
    savePageDesignerDraft,
    type DashboardLayout,
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
  const page = ref<PageDefinition | null>(null);
  const previewRuntime = ref<PageDesignerRuntime | null>(null);
  const selectedId = ref('');
  const layout = reactive<DashboardLayout>({ cols: 24, rowHeight: 64, items: [] });
  const components = ref<PageComponentConfig[]>([]);

  const selectedComponent = computed(() => components.value.find((component) => component.id === selectedId.value));

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
      components.value = version?.components || [];
      selectedId.value = components.value[0]?.id || '';
    } finally {
      loading.value = false;
    }
  }

  function addWidget(type: string) {
    const definition = widgetDefinition(type);
    const id = `w_${Date.now().toString(36)}`;
    const maxY = layout.items.reduce((value, item) => Math.max(value, item.y + item.h), 0);
    layout.items.push({
      id,
      type,
      x: 0,
      y: maxY,
      w: definition.defaultSize.w,
      h: definition.defaultSize.h,
      props: {},
    });
    components.value.push({
      id,
      type,
      title: definition.defaultTitle,
      props: { ...definition.defaultProps },
    });
    selectedId.value = id;
  }

  function removeSelected() {
    if (!selectedId.value) return;
    layout.items = layout.items.filter((item) => item.id !== selectedId.value);
    components.value = components.value.filter((component) => component.id !== selectedId.value);
    selectedId.value = components.value[0]?.id || '';
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
  .page-designer-detail {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
  }

  .page-designer-detail__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;

    h1 {
      margin: 8px 0 4px;
      font-size: 22px;
      line-height: 1.3;
    }

    p {
      margin: 0;
      color: #64748b;
    }
  }

  .page-designer-detail__workspace {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr) 280px;
    gap: 14px;
    align-items: start;
  }

  .page-designer-detail__palette,
  .page-designer-detail__props {
    min-width: 0;
    padding: 14px;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;

    h2 {
      margin: 0 0 12px;
      font-size: 15px;
    }
  }

  .page-designer-detail__palette {
    display: grid;
    gap: 8px;

    button {
      display: grid;
      gap: 4px;
      width: 100%;
      padding: 10px;
      text-align: left;
      background: #f8fafc;
      border: 1px solid #dbe3ee;
      border-radius: 5px;
      cursor: pointer;

      &:hover {
        border-color: #2563eb;
      }

      strong {
        font-size: 13px;
      }

      span {
        color: #64748b;
        font-size: 12px;
      }
    }
  }

  .page-designer-detail__canvas {
    min-width: 0;
  }

  .page-designer-detail__preview {
    width: min(1200px, 92vw);
  }

  @media (max-width: 1100px) {
    .page-designer-detail__workspace {
      grid-template-columns: 1fr;
    }
  }
</style>
