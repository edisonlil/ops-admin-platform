<template>
  <footer v-if="pagination !== false" class="app-pagination">
    <n-pagination v-bind="pagination" />
  </footer>
</template>

<script lang="ts" setup>
  import type { PaginationProps } from 'naive-ui';

  defineProps<{
    pagination?: false | PaginationProps;
  }>();
</script>

<style lang="less" scoped>
  .app-pagination {
    display: flex;
    justify-content: flex-end;
    min-width: 0;
  }
</style>
