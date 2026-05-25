<template>
  <footer v-if="pagination !== false" class="app-pagination">
    <n-pagination
      v-bind="resolvedPagination"
      @update:page="handlePageUpdate"
      @update:page-size="handlePageSizeUpdate"
    />
    <div class="app-pagination__summary">
      <span>共 {{ totalItems }} 条</span>
      <span>共 {{ totalPages }} 页</span>
    </div>
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

  const totalItems = computed(() => Number(resolvedPagination.value.itemCount || 0));
  const totalPages = computed(() => {
    const itemCount = totalItems.value;
    const pageSize = Math.max(1, Number(resolvedPagination.value.pageSize || 20));
    return itemCount === 0 ? 0 : Math.ceil(itemCount / pageSize);
  });

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
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  min-width: 0;
}

.app-pagination__summary {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  color: var(--app-icon-color);
  font-size: 12px;
}
</style>
