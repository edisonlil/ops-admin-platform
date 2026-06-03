<template>
  <div class="page-designer-runtime">
    <div class="page-designer-runtime__header">
      <h1>{{ payload?.page.name || '页面' }}</h1>
      <p>{{ payload?.page.description }}</p>
    </div>
    <n-spin :show="loading">
      <DashboardGridCanvas v-if="payload" :layout="payload.runtime.layout" :components="payload.runtime.components" readonly />
      <n-empty v-else-if="!loading" description="页面不存在或未发布" />
    </n-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import DashboardGridCanvas from '@/components/PageDesigner/DashboardGridCanvas.vue';
  import { getPageDesignerRuntime, type PageRuntimePayload } from '@/api/pageDesigner';

  const route = useRoute();
  const loading = ref(false);
  const runtimePayload = ref<PageRuntimePayload | null>(null);
  const pageKey = computed(() => resolvePageKey());
  const payload = computed(() => runtimePayload.value?.item || null);

  async function load() {
    runtimePayload.value = null;
    if (!pageKey.value) return;
    loading.value = true;
    try {
      runtimePayload.value = await getPageDesignerRuntime(pageKey.value);
    } finally {
      loading.value = false;
    }
  }

  function resolvePageKey() {
    const queryKey = String(route.query.page_key || '').trim();
    if (queryKey) return queryKey;

    const parts = route.path.split('/').filter(Boolean);
    const runtimeIndex = parts.findIndex((part) => part === 'runtime');
    if (runtimeIndex >= 0 && parts[runtimeIndex + 1]) {
      return parts[runtimeIndex + 1];
    }

    const explicitKey = String(route.params.pageKey || route.params.pathMatch || '')
      .split('/')
      .filter(Boolean)
      .pop();
    if (explicitKey) return explicitKey;
    return parts.pop() || '';
  }

  watch(() => route.fullPath, load, { immediate: true });
</script>

<style lang="less" scoped>
  .page-designer-runtime {
    min-width: 0;
    color: var(--app-text-color, #111827);
    font-family: var(
      --app-font-family-base,
      system-ui,
      -apple-system,
      BlinkMacSystemFont,
      'Segoe UI',
      'Microsoft YaHei',
      'PingFang SC',
      sans-serif
    );
  }

  .page-designer-runtime__header {
    display: grid;
    gap: 6px;
    min-height: var(--app-page-header-min-height);
    margin-bottom: var(--app-page-section-gap, 16px);
    padding: var(--app-page-header-padding-block) var(--app-page-header-padding-inline);
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color, #dfe4ea) 72%, transparent);

    h1 {
      margin: 0;
      overflow: hidden;
      color: var(--app-text-color, #111827);
      font-size: var(--app-page-header-title-size, var(--app-font-size-lg, 16px));
      font-weight: 650;
      line-height: 1.25;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      margin: 0;
      overflow: hidden;
      color: var(--app-icon-color, var(--app-text-color-2, #4b5565));
      font-size: var(--app-page-header-description-size, var(--app-font-size-sm, 13px));
      line-height: 1.5;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
