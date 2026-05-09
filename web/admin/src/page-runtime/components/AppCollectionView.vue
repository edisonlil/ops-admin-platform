<template>
  <section class="app-collection-view" :class="`app-collection-view--${schema.type}`">
    <n-data-table
      v-if="schema.type === 'table'"
      class="app-collection-view__table"
      :columns="resolvedColumns"
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

    <n-spin v-else-if="isCardCollection" :show="loading">
      <div
        v-if="rows.length"
        class="app-collection-view__card-grid"
        :style="{ '--app-card-list-min-width': schema.cardMinWidth || '320px' }"
      >
        <slot
          v-for="(row, index) in rows"
          name="item"
          :row="row"
          :index="index"
          :key="resolveItemKey(row, index)"
        >
          <article class="app-collection-view__card-fallback">
            <strong>{{ resolveItemKey(row, index) }}</strong>
          </article>
        </slot>
      </div>
      <n-empty v-else description="暂无数据" class="app-collection-view__empty" />
    </n-spin>

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
  import type { DataTableColumn, DataTableColumns } from 'naive-ui';

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
  const isCardCollection = computed(() => ['card-list', 'product-list', 'gallery'].includes(props.schema.type));
  const resolvedColumns = computed<DataTableColumns<Row>>(() => {
    const columns = props.schema.columns || [];
    if (props.schema.type !== 'table' || !props.schema.selectable) return columns;
    if (columns.some((column) => 'type' in column && column.type === 'selection')) return columns;

    const selectionColumn: DataTableColumn<Row> = {
      type: 'selection',
      width: props.schema.selectionColumn?.width || 48,
      fixed: props.schema.selectionColumn?.fixed || 'left',
      disabled: props.schema.selectionColumn?.disabled,
    };
    return [selectionColumn, ...columns];
  });

  function resolveItemKey(row: Row, index: number) {
    const key = props.schema.itemKey || props.schema.rowKey || 'id';
    if (typeof key === 'function') return key(row);
    return row[key] ?? index;
  }
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

    :deep(.n-data-table-th--selection),
    :deep(.n-data-table-td--selection) {
      padding-right: 0;
      padding-left: 0;
      text-align: center;
    }
  }

  .app-collection-view__table {
    min-width: 0;
  }

  .app-collection-view__card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--app-card-list-min-width)), 1fr));
    gap: var(--app-page-collection-gap);
    align-items: stretch;
    min-width: 0;
  }

  .app-collection-view__card-fallback,
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
  }

  .app-collection-view__card-fallback strong,
  .app-collection-view__placeholder strong {
    color: var(--app-text-color);
    font-size: 15px;
    font-weight: 650;
  }

  .app-collection-view__placeholder {
    span,
    small {
      font-size: 13px;
      line-height: 1.45;
    }
  }

  .app-collection-view__empty {
    padding: 48px 0;
  }
</style>
