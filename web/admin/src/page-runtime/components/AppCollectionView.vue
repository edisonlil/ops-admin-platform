<template>
  <section ref="collectionViewRef" class="app-collection-view" :class="`app-collection-view--${schema.type}`">
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
        :remote="schema.sort?.remote"
        v-bind="resolvedTableProps"
        @update:sorter="handleSorterUpdate"
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

    <n-spin v-else-if="schema.type === 'tree'" :show="loading">
      <n-tree
        class="app-collection-view__tree"
        block-line
        :data="schema.treeData || []"
        :selected-keys="schema.selectedKeys || []"
        v-bind="resolvedTreeProps"
        :render-label="renderTreeNode"
        @update:selected-keys="handleTreeSelectedKeys"
      />
      <n-dropdown
        trigger="manual"
        placement="bottom-start"
        :show="treeContextMenu.show"
        :x="treeContextMenu.x"
        :y="treeContextMenu.y"
        :options="treeContextOptions"
        @select="handleTreeContextSelect"
        @clickoutside="hideTreeContextMenu"
      />
    </n-spin>

    <div v-else class="app-collection-view__placeholder">
      <strong>{{ viewDefinition.label }}</strong>
      <span>{{ viewDefinition.description }}</span>
      <small>该视图已进入 CollectionView 注册表，可按业务形态接入专用渲染 adapter。</small>
    </div>
  </section>
</template>

<script lang="ts" setup generic="Row extends Record<string, unknown>">
  import { computed, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
  import { NIcon, NTooltip, useDialog } from 'naive-ui';
  import { LockOutlined, UnlockOutlined } from '@vicons/antd';
  import { getCollectionViewDefinition } from '../collectionRegistry';
  import type { CollectionViewSchema, TableSortState, TreeNodeAction } from '../types';
  import type { DataTableBaseColumn, DataTableColumn, DataTableColumnKey, DataTableColumns, DataTableSortState, DropdownOption, TreeRenderProps } from 'naive-ui';
  import type { VNodeChild } from 'vue';

  const SELECTION_COLUMN_KEY = '__selection__';
  const DEFAULT_TABLE_COLUMN_WIDTH = 140;
  const SORT_SUPPRESS_AFTER_COLUMN_RESIZE_MS = 450;
  const lockedColumnKeys = ref<Array<string | number>>([]);
  const lastColumnResizeAt = ref(0);
  const collectionViewRef = ref<HTMLElement | null>(null);
  const tableViewportWidth = ref(0);
  const dialog = useDialog();
  let tableResizeObserver: ResizeObserver | undefined;

  const props = withDefaults(
    defineProps<{
      schema: CollectionViewSchema<Row>;
      rows?: Row[];
      loading?: boolean;
      sortState?: TableSortState;
    }>(),
    {
      rows: () => [],
      loading: false,
    }
  );
  const emit = defineEmits<{
    sortChange: [state: TableSortState];
    columnResize: [payload: TableColumnResizePayload<Row>];
  }>();

  const viewDefinition = computed(() => getCollectionViewDefinition(props.schema.type));
  const resolvedRowKey = computed(() => {
    const key = props.schema.rowKey || props.schema.itemKey || 'id';
    if (typeof key === 'function') return key;
    return (row: Row) => row[key] as string | number;
  });
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

    return stabilizeColumnsForViewport(orderRuntimeColumns(applyPreferenceOrder(filterVisibleColumns(normalizeColumns(runtimeColumns)))));
  });
  const resolvedTableProps = computed(() => {
    if (props.schema.type !== 'table') return props.schema.tableProps || {};
    const tableLayout = props.schema.tableLayout || {};
    const tableProps = props.schema.tableProps || {};
    const rowHeight = tableLayout.rowHeight;
    const heightMode = tableLayout.heightMode || 'natural';
    const fillHeight = tableLayout.fillHeight || 'clamp(320px, calc(100vh - 440px), 560px)';
    const naturalMaxHeight = tableLayout.maxHeight || 'calc(100vh - 300px)';
    const runtimeProps = {
      maxHeight: heightMode === 'fill' ? undefined : naturalMaxHeight,
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
      pagination: normalizeTablePagination(tableProps.pagination),
      style: [
        heightMode === 'fill'
          ? { height: formatCssSize(tableLayout.height || fillHeight) }
          : tableLayout.height
            ? { height: formatCssSize(tableLayout.height) }
            : undefined,
        tableProps.style,
      ],
      onUnstableColumnResize: handleColumnResize,
    };
  });
  const treeContextMenu = reactive<{
    show: boolean;
    x: number;
    y: number;
    node: TreeRenderProps['option'] | null;
  }>({
    show: false,
    x: 0,
    y: 0,
    node: null,
  });
  const treeContextActions = computed<TreeNodeAction[]>(() => {
    if (!treeContextMenu.node) return [];
    const actions =
      typeof props.schema.treeNodeActions === 'function'
        ? props.schema.treeNodeActions(treeContextMenu.node)
        : props.schema.treeNodeActions || [];
    return actions.filter((action) => action.show !== false);
  });
  const treeContextOptions = computed<DropdownOption[]>(() =>
    treeContextActions.value.map((action) => ({
      key: action.key,
      label: action.label,
      disabled: action.disabled,
    }))
  );
  const resolvedTreeProps = computed(() => {
    const treeProps = props.schema.treeProps || {};
    const userNodeProps = treeProps.nodeProps as ((props: TreeRenderProps) => TreeNodeRuntimeProps) | undefined;
    return {
      ...treeProps,
      nodeProps: (nodeProps: TreeRenderProps) => {
        const originalProps = userNodeProps?.(nodeProps) || {};
        return {
          ...originalProps,
          onContextmenu: (event: MouseEvent) => {
            const originalContextMenu = originalProps.onContextmenu;
            if (typeof originalContextMenu === 'function') {
              originalContextMenu(event);
            }
            if (!event.defaultPrevented) {
              showTreeContextMenu(event, nodeProps.option);
            }
          },
        };
      },
    };
  });

  onMounted(() => {
    updateTableViewportWidth();
    if (typeof ResizeObserver === 'undefined') return;
    tableResizeObserver = new ResizeObserver(() => updateTableViewportWidth());
    if (collectionViewRef.value) {
      tableResizeObserver.observe(collectionViewRef.value);
    }
  });

  onBeforeUnmount(() => {
    tableResizeObserver?.disconnect();
  });

  watch(
    () => props.schema.type,
    () => nextTick(updateTableViewportWidth)
  );

  function resolveItemKey(row: Row, index: number) {
    const key = props.schema.itemKey || props.schema.rowKey || 'id';
    if (typeof key === 'function') return key(row);
    return row[key] ?? index;
  }

  function handleTreeSelectedKeys(keys: Array<string | number>) {
    props.schema.onUpdateSelectedKeys?.(keys);
  }

  function showTreeContextMenu(event: MouseEvent, node: TreeRenderProps['option']) {
    if (!treeContextActionsForNode(node).length) return;
    event.preventDefault();
    treeContextMenu.show = false;
    treeContextMenu.node = node;
    props.schema.onUpdateSelectedKeys?.([node.key as string | number]);
    nextTick(() => {
      treeContextMenu.x = event.clientX;
      treeContextMenu.y = event.clientY;
      treeContextMenu.show = true;
    });
  }

  function hideTreeContextMenu() {
    treeContextMenu.show = false;
  }

  function handleTreeContextSelect(key: string | number) {
    const action = treeContextActions.value.find((entry) => entry.key === key);
    const node = treeContextMenu.node;
    hideTreeContextMenu();
    if (!action || !node) return;
    if (action.confirm) {
      dialog.warning({
        title: action.confirmTitle || '确认操作',
        content: action.confirmContent || '确认执行该操作吗？',
        positiveText: action.positiveText || '确认',
        negativeText: action.negativeText || '取消',
        onPositiveClick: () => action.onClick?.(node),
      });
      return;
    }
    action.onClick?.(node);
  }

  function treeContextActionsForNode(node: TreeRenderProps['option']) {
    const actions =
      typeof props.schema.treeNodeActions === 'function'
        ? props.schema.treeNodeActions(node)
        : props.schema.treeNodeActions || [];
    return actions.filter((action) => action.show !== false);
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

      const preference = findColumnPreference(columnKey);
      if (preference?.fixed && !nextColumn.fixed) {
        nextColumn.fixed = preference.fixed;
      }
      if (isPositiveNumber(preference?.width)) {
        nextColumn.width = preference.width;
      }
      const stableWidth = resolveStableColumnWidth(nextColumn, preference?.width, runtime.defaultWidth);
      if (preference?.sortable) {
        nextColumn.sorter = nextColumn.sorter || true;
        nextColumn.sortOrder = currentSortField.value === resolveColumnSortField(columnKey) ? currentSortOrder.value : false;
      }

      if (!('resizable' in nextColumn) && defaultResizable && !disabledResizable) {
        nextColumn.resizable = true;
      }

      if (!('width' in nextColumn) && nextColumn.resizable) {
        nextColumn.width = stableWidth;
      }

      if (nextColumn.resizable) {
        delete nextColumn.minWidth;
      } else if (!('minWidth' in nextColumn) && runtime.minWidth !== undefined) {
        nextColumn.minWidth = runtime.minWidth;
      }

      if (runtime.maxWidth && !('maxWidth' in nextColumn)) {
        nextColumn.maxWidth = runtime.maxWidth;
      }

      if (!disabledFreeze && columnKey !== undefined) {
        if (isColumnLocked(columnKey)) {
          nextColumn.fixed = 'left';
          nextColumn.width = stableWidth;
          nextColumn.minWidth = stableWidth;
        } else if (!nextColumn.fixed && runtime.freeze?.left?.includes(columnKey)) {
          nextColumn.fixed = 'left';
          nextColumn.width = stableWidth;
          nextColumn.minWidth = stableWidth;
        } else if (!nextColumn.fixed && runtime.freeze?.right?.includes(columnKey)) {
          nextColumn.fixed = 'right';
          nextColumn.width = stableWidth;
          nextColumn.minWidth = stableWidth;
        }
      }

      if (lockable && nextColumn.fixed !== 'right') {
        nextColumn.title = renderColumnTitle(nextColumn, columnKey);
      }

      return nextColumn;
    });
  }

  function handleColumnResize(
    resizedWidth: number,
    limitedWidth: number,
    column: DataTableBaseColumn<Row>,
    getColumnWidth: (key: DataTableColumnKey) => number | undefined
  ) {
    const originalHandler = props.schema.type === 'table' ? props.schema.tableProps?.onUnstableColumnResize : undefined;
    if (typeof originalHandler === 'function') {
      originalHandler(resizedWidth, limitedWidth, column, getColumnWidth);
    }

    const columnKey = column.key;
    const width = Number.isFinite(limitedWidth) ? limitedWidth : resizedWidth;
    if (columnKey === undefined || !isPositiveNumber(width)) return;

    lastColumnResizeAt.value = Date.now();
    emit('columnResize', {
      columnKey,
      width,
      resizedWidth,
      limitedWidth,
      column,
      getColumnWidth,
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

  function stabilizeColumnsForViewport(columns: DataTableColumns<Row>): DataTableColumns<Row> {
    if (props.schema.type !== 'table') return columns;

    const leaves = flattenLeafColumns(columns);
    const currentWidth = leaves.reduce((total, column) => total + resolveStableColumnWidth(column, undefined, undefined), 0);
    const scrollX = typeof props.schema.scrollX === 'number' ? props.schema.scrollX : 0;
    const requiredWidth = Math.ceil(Math.max(scrollX, tableViewportWidth.value));
    const delta = requiredWidth - currentWidth;
    if (delta <= 0) return columns;

    const targetColumn = [...leaves]
      .reverse()
      .find((column) => !isControlColumn(column) && !('fixed' in column && (column.fixed === 'left' || column.fixed === 'right')));
    const targetKey = targetColumn ? getColumnKey(targetColumn) : undefined;
    if (targetKey === undefined) return columns;

    return columns.map((column) => patchColumnWidth(column as DataTableColumn<Row>, targetKey, delta));
  }

  function flattenLeafColumns(columns: DataTableColumns<Row>): DataTableColumn<Row>[] {
    return columns.flatMap((column) => {
      if ('children' in column && column.children) {
        return flattenLeafColumns(column.children as DataTableColumns<Row>);
      }
      return [column as DataTableColumn<Row>];
    });
  }

  function patchColumnWidth(column: DataTableColumn<Row>, targetKey: string | number, delta: number): DataTableColumn<Row> {
    if ('children' in column && column.children) {
      return {
        ...column,
        children: (column.children as DataTableColumns<Row>).map((childColumn) => patchColumnWidth(childColumn as DataTableColumn<Row>, targetKey, delta)),
      } as DataTableColumn<Row>;
    }

    if (String(getColumnKey(column)) !== String(targetKey)) return column;

    const width = resolveStableColumnWidth(column, undefined, undefined) + delta;
    return {
      ...column,
      width,
      minWidth: width,
    } as DataTableColumn<Row>;
  }

  function applyPreferenceOrder(columns: DataTableColumns<Row>): DataTableColumns<Row> {
    const preferences = props.schema.columnRuntime?.columns || [];
    if (!preferences.length) return columns;

    const orderMap = new Map(preferences.map((preference, index) => [String(preference.key), index]));
    const controlColumns: DataTableColumns<Row> = [];
    const sortableColumns: DataTableColumns<Row> = [];
    const unsortedColumns: DataTableColumns<Row> = [];

    columns.forEach((column) => {
      if (isControlColumn(column)) {
        controlColumns.push(column);
        return;
      }

      const columnKey = getColumnKey(column);
      if (columnKey !== undefined && orderMap.has(String(columnKey))) {
        sortableColumns.push(column);
        return;
      }

      unsortedColumns.push(column);
    });

    sortableColumns.sort((left, right) => {
      const leftIndex = orderMap.get(String(getColumnKey(left))) ?? Number.MAX_SAFE_INTEGER;
      const rightIndex = orderMap.get(String(getColumnKey(right))) ?? Number.MAX_SAFE_INTEGER;
      return leftIndex - rightIndex;
    });

    return [...controlColumns, ...sortableColumns, ...unsortedColumns];
  }

  function filterVisibleColumns(columns: DataTableColumns<Row>): DataTableColumns<Row> {
    return columns.flatMap((column) => {
      if ('children' in column && column.children) {
        const visibleChildren = filterVisibleColumns(column.children as DataTableColumns<Row>);
        return visibleChildren.length ? [{ ...column, children: visibleChildren } as DataTableColumn<Row>] : [];
      }
      if (isControlColumn(column)) return [column];
      const columnKey = getColumnKey(column);
      if (columnKey === undefined) return [column];
      const preference = findColumnPreference(columnKey);
      if (preference?.defaultVisible === false && !preference.required) return [];
      return [column];
    });
  }

  const currentSortField = computed(() => props.sortState?.sort_by || props.schema.sort?.defaultSort?.sort_by || '');
  const currentSortOrder = computed(() => {
    const direction = props.sortState?.sort_dir || props.schema.sort?.defaultSort?.sort_dir;
    return direction === 'asc' ? 'ascend' : direction === 'desc' ? 'descend' : false;
  });

  function handleSorterUpdate(sorter: DataTableSortState | DataTableSortState[] | null) {
    if (Date.now() - lastColumnResizeAt.value < SORT_SUPPRESS_AFTER_COLUMN_RESIZE_MS) {
      return;
    }
    const state = Array.isArray(sorter) ? sorter[0] : sorter;
    if (!state || !state.order) {
      emit('sortChange', {});
      return;
    }
    const columnKey = state.columnKey;
    if (columnKey === undefined) {
      emit('sortChange', {});
      return;
    }
    const sortField = resolveColumnSortField(columnKey);
    if (!sortField) {
      emit('sortChange', {});
      return;
    }
    emit('sortChange', {
      sort_by: sortField,
      sort_dir: state.order === 'ascend' ? 'asc' : 'desc',
    });
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
    const freezableKeys = getFreezableColumnKeys(props.schema.columns || []);
    const targetIndex = freezableKeys.findIndex((key) => key === columnKey);
    if (targetIndex < 0) return;

    const nextLockedKeys = freezableKeys.slice(0, targetIndex + 1);
    const currentBoundaryKey = lockedColumnKeys.value[lockedColumnKeys.value.length - 1];

    lockedColumnKeys.value = currentBoundaryKey === columnKey ? [] : nextLockedKeys;
  }

  function isColumnLocked(columnKey: string | number) {
    return lockedColumnKeys.value.includes(columnKey);
  }

  function getColumnKey(column: DataTableColumn<Row>) {
    if ('key' in column && column.key !== undefined) return column.key;
    return undefined;
  }

  function findColumnPreference(columnKey: string | number | undefined) {
    if (columnKey === undefined) return undefined;
    return props.schema.columnRuntime?.columns?.find((item) => String(item.key) === String(columnKey));
  }

  function resolveColumnSortField(columnKey: string | number | undefined) {
    if (columnKey === undefined) return '';
    const preference = findColumnPreference(columnKey);
    if (!preference?.sortable) return '';
    return preference.sortField || String(columnKey);
  }

  function isPositiveNumber(value: unknown): value is number {
    return typeof value === 'number' && Number.isFinite(value) && value > 0;
  }

  function resolveStableColumnWidth(column: DataTableColumn<Row>, preferredWidth: unknown, defaultWidth: unknown) {
    if (isPositiveNumber(preferredWidth)) return Math.round(preferredWidth);
    if ('width' in column && isPositiveNumber(column.width)) return Math.round(column.width);
    if ('minWidth' in column && isPositiveNumber(column.minWidth)) return Math.round(column.minWidth);
    if (isPositiveNumber(defaultWidth)) return Math.round(defaultWidth);
    return DEFAULT_TABLE_COLUMN_WIDTH;
  }

  function isControlColumn(column: DataTableColumn<Row>) {
    return 'type' in column && (column.type === 'selection' || column.type === 'expand');
  }

  function getFreezableColumnKeys(columns: DataTableColumns<Row>): Array<string | number> {
    const runtime = props.schema.columnRuntime || {};

    return columns.flatMap((column) => {
      if ('children' in column && column.children) {
        return getFreezableColumnKeys(column.children as DataTableColumns<Row>);
      }

      if (isControlColumn(column)) return [];

      const columnKey = getColumnKey(column);
      if (columnKey === undefined) return [];

      const disabledFreeze = runtime.disabledFreezeKeys?.includes(columnKey);
      const isSystemFrozen = runtime.freeze?.left?.includes(columnKey) || runtime.freeze?.right?.includes(columnKey);
      if (disabledFreeze || isSystemFrozen || column.fixed) return [];

      return [columnKey];
    });
  }

  function compactObject<T extends Record<string, unknown>>(value: T) {
    return Object.fromEntries(Object.entries(value).filter(([, entry]) => entry !== undefined));
  }

  function formatCssSize(value: number | string) {
    return typeof value === 'number' ? `${value}px` : value;
  }

  function updateTableViewportWidth() {
    if (props.schema.type !== 'table') {
      tableViewportWidth.value = 0;
      return;
    }
    tableViewportWidth.value = Math.ceil(collectionViewRef.value?.getBoundingClientRect().width || 0);
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

  function renderTreeNode(props: TreeRenderProps): VNodeChild {
    const renderLabel = schemaTreeRenderLabel.value;
    const content = renderLabel ? renderLabel(props) : props.option.label;
    return h(
      'span',
      {
        class: 'app-collection-view__tree-node',
      },
      [content as VNodeChild]
    );
  }

  const schemaTreeRenderLabel = computed(() => props.schema.treeProps?.renderLabel as ((props: TreeRenderProps) => VNodeChild) | undefined);

  type TreeNodeRuntimeProps = {
    onContextmenu?: (event: MouseEvent) => void;
    [key: string]: unknown;
  };

  type TableColumnResizePayload<Row extends Record<string, unknown>> = {
    columnKey: DataTableColumnKey;
    width: number;
    resizedWidth: number;
    limitedWidth: number;
    column: DataTableBaseColumn<Row>;
    getColumnWidth: (key: DataTableColumnKey) => number | undefined;
  };
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
      border-color: color-mix(in srgb, var(--app-border-color, #d9e1ec) 62%, transparent);
    }

    :deep(.n-data-table-td) {
      height: var(--app-page-table-row-height);
      padding-right: var(--app-page-table-cell-padding-inline);
      padding-left: var(--app-page-table-cell-padding-inline);
      border-color: color-mix(in srgb, var(--app-border-color, #d9e1ec) 58%, transparent);
    }

    :deep(.n-data-table-td:not(.n-data-table-td--selection, .n-data-table-td--expand) .n-data-table-td__ellipsis),
    :deep(.app-table-cell-clamp) {
      display: -webkit-box;
      max-height: calc(var(--app-page-table-row-height) * 2 - 8px);
      overflow: hidden;
      line-height: 1.55;
      overflow-wrap: anywhere;
      text-overflow: ellipsis;
      white-space: normal;
      word-break: break-word;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }

    :deep(.n-data-table-thead) {
      background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 30%, var(--app-surface-bg, #ffffff));
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
      right: -8px;
      width: 18px;
      opacity: 0.38;
      z-index: 2;
    }

    :deep(.n-data-table-resize-button::after) {
      top: 18%;
      bottom: 18%;
      width: 1px;
      background-color: color-mix(in srgb, var(--app-border-color, #d9e1ec) 44%, transparent);
      border-radius: 999px;
      transition:
        background-color 0.16s ease,
        opacity 0.16s ease;
    }

    :deep(.n-data-table-th:hover .n-data-table-resize-button),
    :deep(.n-data-table-resize-button--active) {
      opacity: 1;
    }

    :deep(.n-data-table-resize-button--active) {
      cursor: col-resize;
    }

    :deep(.n-data-table-th:hover .n-data-table-resize-button::after) {
      background-color: color-mix(in srgb, var(--app-border-color, #d9e1ec) 68%, transparent);
    }

    :deep(.n-data-table-resize-button--active::after) {
      background-color: color-mix(in srgb, var(--app-primary-color) 72%, transparent);
    }
  }

  .app-collection-view__tree-node {
    display: inline-flex;
    align-items: center;
    min-width: 0;
    max-width: 100%;
  }

  .app-collection-view--table {
    gap: 0;
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
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
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 26%, transparent);
  }

  .app-collection-view__table {
    min-width: 0;
  }

  .app-collection-view__table :deep(.n-data-table-th--fixed-left),
  .app-collection-view__table :deep(.n-data-table-td--fixed-left),
  .app-collection-view__table :deep(.n-data-table-th--fixed-right),
  .app-collection-view__table :deep(.n-data-table-td--fixed-right) {
    transition: none;
  }

  .app-collection-view--table :deep(.n-data-table) {
    border-radius: 0;
  }

  .app-collection-view--table :deep(.n-data-table-base-table-header) {
    border-top-color: color-mix(in srgb, var(--app-border-color, #d9e1ec) 22%, transparent);
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

  .app-collection-view__tree {
    min-width: 0;
    padding: 8px;
  }

  .app-collection-view__card-fallback,
  .app-collection-view__placeholder {
    display: grid;
    gap: 4px;
    min-height: 160px;
    padding: var(--app-page-card-padding);
    color: var(--app-icon-color);
    background: var(--app-surface-bg);
    border: 1px dashed var(--app-border-color, #d9e1ec);
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
