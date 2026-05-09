<template>
  <section class="app-collection-view" :class="`app-collection-view--${schema.type}`">
    <n-data-table
      v-if="schema.type === 'table'"
      class="app-collection-view__table"
      :columns="schema.columns"
      :data="rows"
      :loading="loading"
      :row-key="resolvedRowKey"
      :scroll-x="schema.scrollX"
      v-bind="schema.tableProps"
    >
      <template #[name]="slotProps" v-for="(_, name) in $slots" :key="name">
        <slot :name="name" v-bind="slotProps"></slot>
      </template>
    </n-data-table>

    <div v-else class="app-collection-view__placeholder">
      <strong>{{ viewDefinition.label }}</strong>
      <span>{{ viewDefinition.description }}</span>
      <small>该视图已进入 CollectionView 注册表，可按业务形态接入专用渲染 adapter。</small>
    </div>
  </section>
</template>

<script lang="ts" setup generic="Row extends Record<string, unknown>">
  import { computed } from 'vue';
  import { getCollectionViewDefinition } from '../collectionRegistry';
  import type { CollectionViewSchema } from '../types';

  const props = withDefaults(
    defineProps<{
      schema: CollectionViewSchema<Row>;
      rows?: Row[];
      loading?: boolean;
    }>(),
    {
      rows: () => [],
      loading: false,
    }
  );

  const viewDefinition = computed(() => getCollectionViewDefinition(props.schema.type));
  const resolvedRowKey = computed(() => props.schema.rowKey || props.schema.itemKey || 'id');
</script>

<style lang="less" scoped>
  .app-collection-view {
    display: grid;
    gap: var(--app-page-collection-gap);
    min-width: 0;

    :deep(.n-data-table-th) {
      height: var(--app-page-table-header-height);
      padding-right: var(--app-page-table-cell-padding-inline);
      padding-left: var(--app-page-table-cell-padding-inline);
    }

    :deep(.n-data-table-td) {
      height: var(--app-page-table-row-height);
      padding-right: var(--app-page-table-cell-padding-inline);
      padding-left: var(--app-page-table-cell-padding-inline);
    }
  }

  .app-collection-view__table {
    min-width: 0;
  }

  .app-collection-view__placeholder {
    display: grid;
    gap: 4px;
    min-height: 160px;
    padding: var(--app-page-card-padding);
    color: var(--app-icon-color);
    background: var(--app-surface-bg);
    border: 1px dashed var(--app-border-color);
    border-radius: var(--app-card-radius);
    place-content: center;
    text-align: center;

    strong {
      color: var(--app-text-color);
      font-size: 15px;
      font-weight: 650;
    }

    span,
    small {
      font-size: 13px;
      line-height: 1.45;
    }
  }
</style>
