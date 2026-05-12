<template>
  <footer v-if="pagination !== false" class="app-pagination">
    <n-pagination
      v-bind="resolvedPagination"
      @update:page="handlePageUpdate"
      @update:page-size="handlePageSizeUpdate"
    />
  </footer>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import type { PaginationProps } from 'naive-ui';

  const props = defineProps<{
    pagination?: false | PaginationProps;
    itemCount?: number;
  }>();

  const emit = defineEmits<{
    'update:page': [page: number];
    'update:page-size': [pageSize: number];
  }>();

  const resolvedPagination = computed<PaginationProps>(() => ({
    page: 1,
    pageSize: 20,
    pageSizes: [20, 50, 100],
    showSizePicker: true,
    itemCount: props.itemCount,
    ...(props.pagination || {}),
  }));

  function handlePageUpdate(page: number) {
    emit('update:page', page);
  }

  function handlePageSizeUpdate(pageSize: number) {
    emit('update:page-size', pageSize);
  }
</script>

<style lang="less" scoped>
  .app-pagination {
    display: flex;
    justify-content: flex-end;
    min-width: 0;
  }
</style>
