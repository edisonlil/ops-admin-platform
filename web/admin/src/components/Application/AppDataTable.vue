<template>
  <section class="app-data-table">
    <AppTableToolbar
      v-if="title || description || $slots.search || $slots.actions || selectedCount > 0 || $slots.batch"
      :title="title"
      :description="description"
      :selected-count="selectedCount"
      :compact-search="compactSearch"
    >
      <template v-if="$slots.search" #search>
        <slot name="search"></slot>
      </template>
      <template v-if="$slots.actions" #actions>
        <slot name="actions"></slot>
      </template>
      <template v-if="$slots.batch" #batch>
        <slot name="batch"></slot>
      </template>
    </AppTableToolbar>

    <n-data-table class="app-data-table__table" v-bind="$attrs">
      <template #[name]="slotProps" v-for="(_, name) in $slots" :key="name">
        <slot v-if="!reservedSlots.includes(String(name))" :name="name" v-bind="slotProps"></slot>
      </template>
    </n-data-table>
  </section>
</template>

<script lang="ts" setup>
  import AppTableToolbar from './AppTableToolbar.vue';

  defineOptions({
    inheritAttrs: false,
  });

  withDefaults(
    defineProps<{
      title?: string;
      description?: string;
      selectedCount?: number;
      compactSearch?: boolean;
    }>(),
    {
      title: '',
      description: '',
      selectedCount: 0,
      compactSearch: false,
    }
  );

  const reservedSlots = ['search', 'actions', 'batch'];
</script>

<style lang="less" scoped>
  .app-data-table {
    display: grid;
    gap: var(--app-table-search-row-gap, 10px);
    min-width: 0;
  }

  .app-data-table__table {
    min-width: 0;
  }
</style>
