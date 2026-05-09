<template>
  <div class="app-status-group">
    <AppStatusTag
      v-for="item in visibleItems"
      :key="item.key || item.statusKey || item.label"
      :status-key="item.statusKey"
      :label="item.label"
      :tone="item.tone"
    />
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import AppStatusTag from './AppStatusTag.vue';
  import type { AppStatusTone } from './statusSemantic';

  export interface AppStatusGroupItem {
    key?: string;
    statusKey?: string;
    label?: string;
    tone?: AppStatusTone | string;
    show?: boolean;
  }

  const props = defineProps<{
    items: AppStatusGroupItem[];
  }>();

  const visibleItems = computed(() => props.items.filter((item) => item.show !== false));
</script>

<style lang="less" scoped>
  .app-status-group {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    min-width: 0;
  }
</style>
