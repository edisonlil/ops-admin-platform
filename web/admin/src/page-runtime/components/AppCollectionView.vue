<template>
  <section class="app-collection-view" :class="`app-collection-view--${schema.type}`">
    <template v-if="schema.type === 'table'">
      <div v-if="$slots['table-tools']" class="app-collection-view__table-tools">
        <slot name="table-tools"></slot>
      </div>
      <n-data-table
        class="app-collection-view__table"
        :class="tableClass"
        :columns="resolvedColumns"
        :data="rows"
        :loading="loading"
        :row-key="resolvedRowKey"
        :scroll-x="schema.scrollX"
        v-bind="resolvedTableProps"
      >
        <template #[name]="slotProps" v-for="(_, name) in $slots" :key="name">
          <slot v-if="name !== 'table-tools'" :name="name" v-bind="slotProps"></slot>
        </template>
      </n-data-table>
    </template>

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
  import { computed, h, ref } from 'vue';
  import { NIcon, NTooltip } from 'naive-ui';
  import { LockOutlined, UnlockOutlined } from '@vicons/antd';
  import { getCollectionViewDefinition } from '../collectionRegistry';
  import type { CollectionViewSchema } from '../types';
  import type { DataTableColumn, DataTableColumns } from 'naive-ui';
  import type { VNodeChild } from 'vue';

  const SELECTION_COLUMN_KEY = '__selection__';
  const DEFAULT_TABLE_COLUMN_WIDTH = 140;
  const DEFAULT_TABLE_COLUMN_MIN_WIDTH = 80;
  const lockedColumnKeys = ref<Array<string | number>>([]);

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
  const tableClass = computed(() => {
    if (props.schema.type !== 'table') return undefined;
    return [
      `app-collection-view__table--height-${props.schema.tableLayout?.heightMode || 'natural'}`,
      `app-collection-view__table--row-${props.schema.tableLayout?.rowDensity || 'default'}`,
    ];
  });
  const resolvedColumns = computed<DataTableColumns<Row>>(() => {
    const columns = props.schema.columns || [];
    if (props.schema.type !== 'table') return columns;

    const runtimeColumns = columns.some((column) => 'type' in column && column.type === 'selection')
      ? columns
      : props.schema.selectable
        ? [createSelectionColumn(), ...columns]
        : columns;

    return orderRuntimeColumns(normalizeColumns(runtimeColumns));
  });
  const resolvedTableProps = computed(() => {
    if (props.schema.type !== 'table') return props.schema.tableProps || {};
    const tableLayout = props.schema.tableLayout || {};
    const rowHeight = tableLayout.rowHeight;
    const heightMode = tableLayout.heightMode || 'natural';
    const fillHeight = tableLayout.fillHeight || 'clamp(320px, calc(100vh - 440px), 560px)';
    const runtimeProps = {
      maxHeight: heightMode === 'fill' ? undefined : tableLayout.maxHeight,
      flexHeight: heightMode === 'fill' ? true : tableLayout.flexHeight,
      headerHeight: tableLayout.headerHeight,
      minRowHeight: tableLayout.minRowHeight,
      heightForRow:
        typeof rowHeight === 'function'
          ? rowHeight
          : typeof rowHeight === 'number'
            ? () => rowHeight
            : undefined,
      tableLayout: tableLayout.tableLayout,
    };
    return {
      ...compactObject(runtimeProps),
      ...(props.schema.tableProps || {}),
      pagination: normalizeTablePagination(props.schema.tableProps?.pagination),
      style: [
        heightMode === 'fill'
          ? { height: formatCssSize(tableLayout.height || fillHeight) }
          : tableLayout.height
            ? { height: formatCssSize(tableLayout.height) }
            : undefined,
        props.schema.tableProps?.style,
      ],
    };
  });

  function resolveItemKey(row: Row, index: number) {
    const key = props.schema.itemKey || props.schema.rowKey || 'id';
    if (typeof key === 'function') return key(row);
    return row[key] ?? index;
  }

  function createSelectionColumn(): DataTableColumn<Row> {
    return {
      type: 'selection',
      key: SELECTION_COLUMN_KEY,
      width: props.schema.selectionColumn?.width || 48,
      fixed: props.schema.selectionColumn?.fixed || 'left',
      disabled: props.schema.selectionColumn?.disabled,
    };
  }

  function normalizeColumns(columns: DataTableColumns<Row>): DataTableColumns<Row> {
    return columns.map((column) => {
      if ('children' in column && column.children) {
        return {
          ...column,
          children: normalizeColumns(column.children as DataTableColumns<Row>),
        };
      }

      if ('type' in column && (column.type === 'selection' || column.type === 'expand')) {
        return column;
      }

      const columnKey = getColumnKey(column);
      const runtime = props.schema.columnRuntime || {};
      const defaultResizable = runtime.defaultResizable !== false;
      const disabledResizable = columnKey !== undefined && runtime.disabledResizableKeys?.includes(columnKey);
      const disabledFreeze = columnKey !== undefined && runtime.disabledFreezeKeys?.includes(columnKey);
      const isSystemFrozen =
        columnKey !== undefined && (runtime.freeze?.left?.includes(columnKey) || runtime.freeze?.right?.includes(columnKey));
      const lockable = columnKey !== undefined && !disabledFreeze && !isSystemFrozen && !column.fixed;
      const nextColumn = {
        ...column,
      } as DataTableColumn<Row>;

      if (!('resizable' in nextColumn) && defaultResizable && !disabledResizable) {
        nextColumn.resizable = true;
      }

      if (!('width' in nextColumn) && nextColumn.resizable) {
        nextColumn.width = runtime.defaultWidth || DEFAULT_TABLE_COLUMN_WIDTH;
      }

      if (!('minWidth' in nextColumn)) {
        nextColumn.minWidth = runtime.minWidth || DEFAULT_TABLE_COLUMN_MIN_WIDTH;
      }

      if (runtime.maxWidth && !('maxWidth' in nextColumn)) {
        nextColumn.maxWidth = runtime.maxWidth;
      }

      if (!disabledFreeze && columnKey !== undefined) {
        if (isColumnLocked(columnKey)) {
          nextColumn.fixed = 'left';
        } else if (!nextColumn.fixed && runtime.freeze?.left?.includes(columnKey)) {
          nextColumn.fixed = 'left';
        } else if (!nextColumn.fixed && runtime.freeze?.right?.includes(columnKey)) {
          nextColumn.fixed = 'right';
        }
      }

      if (lockable && nextColumn.fixed !== 'right') {
        nextColumn.title = renderColumnTitle(nextColumn, columnKey);
      }

      return nextColumn;
    });
  }

  function orderRuntimeColumns(columns: DataTableColumns<Row>): DataTableColumns<Row> {
    if (!lockedColumnKeys.value.length) return columns;

    const controlLeftColumns: DataTableColumns<Row> = [];
    const staticLeftColumns: DataTableColumns<Row> = [];
    const lockedLeftColumns: DataTableColumns<Row> = [];
    const normalColumns: DataTableColumns<Row> = [];
    const rightColumns: DataTableColumns<Row> = [];

    columns.forEach((column) => {
      if (isControlColumn(column)) {
        controlLeftColumns.push(column);
        return;
      }

      const columnKey = getColumnKey(column);

      if ('fixed' in column && column.fixed === 'right') {
        rightColumns.push(column);
        return;
      }

      if (columnKey !== undefined && isColumnLocked(columnKey)) {
        lockedLeftColumns.push(column);
        return;
      }

      if ('fixed' in column && column.fixed === 'left') {
        staticLeftColumns.push(column);
        return;
      }

      normalColumns.push(column);
    });

    return [...controlLeftColumns, ...staticLeftColumns, ...lockedLeftColumns, ...normalColumns, ...rightColumns];
  }

  function renderColumnTitle(column: DataTableColumn<Row>, columnKey: string | number) {
    const originalTitle = 'title' in column ? column.title : undefined;
    return () =>
      h('div', { class: 'app-table-column-title' }, [
        h('span', { class: 'app-table-column-title__text' }, [renderOriginalTitle(originalTitle, column)]),
        h(
          NTooltip,
          { trigger: 'hover' },
          {
            trigger: () =>
              h(
                'button',
                {
                  type: 'button',
                  class: [
                    'app-table-column-title__lock',
                    isColumnLocked(columnKey) ? 'app-table-column-title__lock--active' : '',
                  ],
                  'aria-label': isColumnLocked(columnKey) ? '取消冻结列' : '冻结列',
                  onClick: (event: MouseEvent) => {
                    event.stopPropagation();
                    toggleColumnLock(columnKey);
                  },
                },
                [
                  h(NIcon, null, {
                    default: () => h(isColumnLocked(columnKey) ? LockOutlined : UnlockOutlined),
                  }),
                ]
              ),
            default: () => (isColumnLocked(columnKey) ? '取消冻结列' : '冻结列'),
          }
        ),
      ]);
  }

  function renderOriginalTitle(title: unknown, column: DataTableColumn<Row>): VNodeChild {
    if (typeof title === 'function') return title(column as never) as VNodeChild;
    return (title || '') as VNodeChild;
  }

  function toggleColumnLock(columnKey: string | number) {
    lockedColumnKeys.value = isColumnLocked(columnKey)
      ? lockedColumnKeys.value.filter((key) => key !== columnKey)
      : [...lockedColumnKeys.value, columnKey];
  }

  function isColumnLocked(columnKey: string | number) {
    return lockedColumnKeys.value.includes(columnKey);
  }

  function getColumnKey(column: DataTableColumn<Row>) {
    if ('key' in column && column.key !== undefined) return column.key;
    return undefined;
  }

  function isControlColumn(column: DataTableColumn<Row>) {
    return 'type' in column && (column.type === 'selection' || column.type === 'expand');
  }

  function compactObject<T extends Record<string, unknown>>(value: T) {
    return Object.fromEntries(Object.entries(value).filter(([, entry]) => entry !== undefined));
  }

  function formatCssSize(value: number | string) {
    return typeof value === 'number' ? `${value}px` : value;
  }

  function normalizeTablePagination(pagination: unknown) {
    if (pagination === false) return false;
    if (!pagination) return pagination;
    return {
      page: 1,
      pageSize: 20,
      pageSizes: [20, 50, 100],
      showSizePicker: true,
      ...(pagination as Record<string, unknown>),
    };
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
      color: var(--app-text-color);
      background: color-mix(in srgb, var(--app-surface-muted-bg) 34%, var(--app-surface-bg));
      border-color: color-mix(in srgb, var(--app-border-color) 62%, transparent);
    }

    :deep(.n-data-table-td) {
      height: var(--app-page-table-row-height);
      padding-right: var(--app-page-table-cell-padding-inline);
      padding-left: var(--app-page-table-cell-padding-inline);
      border-color: color-mix(in srgb, var(--app-border-color) 58%, transparent);
    }

    :deep(.n-data-table-thead) {
      background: color-mix(in srgb, var(--app-surface-muted-bg) 30%, var(--app-surface-bg));
    }

    :deep(.n-data-table-th--selection),
    :deep(.n-data-table-td--selection) {
      padding-right: 0;
      padding-left: 0;
      text-align: center;
    }

    :deep(.app-table-column-title) {
      display: inline-grid;
      grid-template-columns: minmax(0, auto) 22px;
      gap: 6px;
      align-items: center;
      min-width: 0;
      max-width: 100%;
    }

    :deep(.app-table-column-title__text) {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    :deep(.app-table-column-title__lock) {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 22px;
      height: 22px;
      padding: 0;
      color: var(--app-icon-color);
      cursor: pointer;
      background: transparent;
      border: 0;
      border-radius: 6px;
      opacity: 0.42;
      transition:
        color 0.16s ease,
        background-color 0.16s ease,
        opacity 0.16s ease;
    }

    :deep(.n-data-table-th:hover .app-table-column-title__lock),
    :deep(.app-table-column-title__lock:focus-visible),
    :deep(.app-table-column-title__lock--active) {
      opacity: 1;
    }

    :deep(.app-table-column-title__lock:hover),
    :deep(.app-table-column-title__lock--active) {
      color: var(--app-primary-color);
      background: var(--app-primary-soft-bg);
    }

    :deep(.n-data-table-resize-button) {
      width: 10px;
      opacity: 0.38;
    }

    :deep(.n-data-table-resize-button::after) {
      top: 18%;
      bottom: 18%;
      width: 1px;
      background-color: color-mix(in srgb, var(--app-border-color) 44%, transparent);
      border-radius: 999px;
      transition:
        background-color 0.16s ease,
        opacity 0.16s ease;
    }

    :deep(.n-data-table-th:hover .n-data-table-resize-button),
    :deep(.n-data-table-resize-button--active) {
      opacity: 1;
    }

    :deep(.n-data-table-th:hover .n-data-table-resize-button::after) {
      background-color: color-mix(in srgb, var(--app-border-color) 68%, transparent);
    }

    :deep(.n-data-table-resize-button--active::after) {
      background-color: color-mix(in srgb, var(--app-primary-color) 72%, transparent);
    }
  }

  .app-collection-view--table {
    gap: 0;
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-card-radius);
  }

  .app-collection-view__table-tools {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 4px;
    min-height: 34px;
    padding: 4px 12px;
    background: var(--app-surface-bg);
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color) 26%, transparent);
  }

  .app-collection-view__table {
    min-width: 0;
  }

  .app-collection-view--table :deep(.n-data-table) {
    border-radius: 0;
  }

  .app-collection-view--table :deep(.n-data-table-base-table-header) {
    border-top-color: color-mix(in srgb, var(--app-border-color) 22%, transparent);
  }

  .app-collection-view__table--height-fill {
    min-height: 320px;
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
