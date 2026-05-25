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
    const explicitKey = String(route.params.pageKey || route.params.pathMatch || route.query.page_key || '')
      .split('/')
      .filter(Boolean)
      .pop();
    if (explicitKey) return explicitKey;
    return route.path.split('/').filter(Boolean).pop() || '';
  }

  watch(() => route.fullPath, load, { immediate: true });
</script>

<style lang="less" scoped>
  .page-designer-runtime {
    min-width: 0;
  }

  .page-designer-runtime__header {
    margin-bottom: 16px;

    h1 {
      margin: 0 0 6px;
      font-size: 22px;
    }

    p {
      margin: 0;
      color: #64748b;
    }
  }
</style>
