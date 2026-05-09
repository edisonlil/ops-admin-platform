<template>
  <footer v-if="pagination !== false" class="app-pagination">
    <n-pagination v-bind="resolvedPagination" />
  </footer>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import type { PaginationProps } from 'naive-ui';

  const props = defineProps<{
    pagination?: false | PaginationProps;
  }>();

  const resolvedPagination = computed<PaginationProps>(() => ({
    page: 1,
    pageSize: 20,
    pageSizes: [20, 50, 100],
    showSizePicker: true,
    ...(props.pagination || {}),
  }));
</script>

<style lang="less" scoped>
  .app-pagination {
    display: flex;
    justify-content: flex-end;
    min-width: 0;
  }
</style>
