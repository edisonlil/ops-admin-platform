<template>
  <AppPage :density="schema.density" :variant="schema.variant" :embedded="schema.embedded">
    <AppPageHeader v-if="!schema.embedded" :title="schema.title" :description="schema.description">
      <template v-if="$slots['header-actions'] || schema.toolbar?.primaryAction || hasHeaderRefresh" #actions>
        <slot name="header-actions"></slot>
        <n-button
          v-if="schema.toolbar?.primaryAction"
          :type="schema.toolbar.primaryAction.type || 'primary'"
          :disabled="schema.toolbar.primaryAction.disabled"
          :loading="schema.toolbar.primaryAction.loading"
          @click="handleAction(schema.toolbar.primaryAction)"
        >
          {{ schema.toolbar.primaryAction.label }}
        </n-button>
        <n-button v-if="hasHeaderRefresh" size="small" quaternary @click="handleRefresh">刷新</n-button>
      </template>
    </AppPageHeader>
    <div
      v-else-if="schema.title || schema.description || schema.toolbar?.primaryAction || hasHeaderRefresh"
      class="app-list-page__embedded-header"
    >
      <div class="app-list-page__embedded-copy">
        <h3 v-if="schema.title">{{ schema.title }}</h3>
        <p v-if="schema.description">{{ schema.description }}</p>
      </div>
      <div v-if="schema.toolbar?.primaryAction || hasHeaderRefresh" class="app-list-page__embedded-actions">
        <n-button
          v-if="schema.toolbar?.primaryAction"
          size="small"
          :type="schema.toolbar.primaryAction.type || 'primary'"
          :disabled="schema.toolbar.primaryAction.disabled"
          :loading="schema.toolbar.primaryAction.loading"
          @click="handleAction(schema.toolbar.primaryAction)"
        >
          {{ schema.toolbar.primaryAction.label }}
        </n-button>
        <n-button v-if="hasHeaderRefresh" size="small" quaternary @click="handleRefresh">刷新</n-button>
      </div>
    </div>

    <AppFilterBar v-if="$slots.filters || hasDeclaredFilters">
      <slot name="filters"></slot>
    </AppFilterBar>

    <AppPageToolbar v-if="hasPageToolbar">
      <template #left>
        <slot name="toolbar-left"></slot>
        <n-button
          v-for="action in schema.toolbar?.batchActions || []"
          :key="action.key"
          size="small"
          :type="action.type || 'default'"
          :disabled="action.disabled"
          :loading="action.loading"
          @click="handleAction(action)"
        >
          {{ action.label }}
        </n-button>
      </template>
      <template #right>
        <slot name="toolbar-right"></slot>
        <n-button v-if="hasToolbarRefresh && !hasRuntimeTableTools" size="small" quaternary @click="handleRefresh">刷新</n-button>
      </template>
    </AppPageToolbar>

    <section v-if="$slots.collection" class="app-list-page__collection">
      <slot name="collection"></slot>
    </section>
    <section v-else-if="isSplitListView && splitView" class="app-list-page__split" :style="splitStyle">
      <section class="app-list-page__split-pane app-list-page__split-pane--master">
        <div v-if="splitView.master.title || splitView.master.description || splitView.master.primaryAction || splitView.master.actions?.length" class="app-list-page__pane-header">
          <div class="app-list-page__pane-title">
            <h3 v-if="splitView.master.title">{{ splitView.master.title }}</h3>
            <p v-if="splitView.master.description">{{ splitView.master.description }}</p>
          </div>
          <div class="app-list-page__pane-actions">
            <n-button
              v-for="action in splitView.master.actions || []"
              :key="action.key"
              size="small"
              :type="action.type || 'default'"
              :disabled="action.disabled"
              :loading="action.loading"
              @click="handleAction(action)"
            >
              {{ action.label }}
            </n-button>
            <n-button
              v-if="splitView.master.primaryAction"
              :type="splitView.master.primaryAction.type || 'primary'"
              :disabled="splitView.master.primaryAction.disabled"
              :loading="splitView.master.primaryAction.loading"
              @click="handleAction(splitView.master.primaryAction)"
            >
              {{ splitView.master.primaryAction.label }}
            </n-button>
          </div>
        </div>
        <AppCollectionView
          :schema="resolveTableViewSchema(splitView.master.view)"
          :rows="getPagedSplitRows('master')"
          :loading="splitView.master.loading || false"
          :sort-state="getSplitSortState('master')"
          @sort-change="(state) => handleSplitSortChange('master', state)"
        />
        <AppPagination
          :pagination="getSplitPagination('master')"
          :item-count="splitView.master.rows?.length || 0"
          @update:page="(page) => updateSplitPage('master', page)"
          @update:page-size="(pageSize) => updateSplitPageSize('master', pageSize)"
        />
      </section>
      <section class="app-list-page__split-pane app-list-page__split-pane--detail">
        <div v-if="splitView.detail.title || splitView.detail.description || splitView.detail.primaryAction || splitView.detail.actions?.length" class="app-list-page__pane-header">
          <div class="app-list-page__pane-title">
            <h3 v-if="splitView.detail.title">{{ splitView.detail.title }}</h3>
            <p v-if="splitView.detail.description">{{ splitView.detail.description }}</p>
          </div>
          <div class="app-list-page__pane-actions">
            <n-button
              v-for="action in splitView.detail.actions || []"
              :key="action.key"
              size="small"
              :type="action.type || 'default'"
              :disabled="action.disabled"
              :loading="action.loading"
              @click="handleAction(action)"
            >
              {{ action.label }}
            </n-button>
            <n-button
              v-if="splitView.detail.primaryAction"
              :type="splitView.detail.primaryAction.type || 'primary'"
              :disabled="splitView.detail.primaryAction.disabled"
              :loading="splitView.detail.primaryAction.loading"
              @click="handleAction(splitView.detail.primaryAction)"
            >
              {{ splitView.detail.primaryAction.label }}
            </n-button>
          </div>
        </div>
        <AppCollectionView
          :schema="resolveTableViewSchema(splitView.detail.view)"
          :rows="getPagedSplitRows('detail')"
          :loading="splitView.detail.loading || false"
          :sort-state="getSplitSortState('detail')"
          @sort-change="(state) => handleSplitSortChange('detail', state)"
        >
          <template v-if="splitView.detail.view.type === 'table'" #table-tools>
            <n-button v-if="hasToolbarRefresh" size="tiny" quaternary :loading="splitView.detail.loading" @click="handleSplitRefresh('detail')">
              刷新
            </n-button>
            <AppTableRuntimeControls
              v-model:fill-height="runtimeTableFillHeight"
              v-model:row-density="runtimeTableRowDensity"
              :columns="getRuntimeColumns(splitView.detail.view)"
              :visible-column-keys="getVisibleColumnKeys(splitView.detail.view)"
              :column-order-keys="getColumnOrderKeys(splitView.detail.view)"
              @update:visible-column-keys="(keys) => updateVisibleColumnKeys(splitView.detail.view, keys)"
              @update:column-order-keys="(keys) => updateColumnOrderKeys(splitView.detail.view, keys)"
              @reset-columns="resetColumnSettings(splitView.detail.view)"
            />
          </template>
        </AppCollectionView>
        <AppPagination
          :pagination="getSplitPagination('detail')"
          :item-count="splitView.detail.rows?.length || 0"
          @update:page="(page) => updateSplitPage('detail', page)"
          @update:page-size="(pageSize) => updateSplitPageSize('detail', pageSize)"
        />
      </section>
    </section>
    <section v-else-if="isTabbedListView" class="app-list-page__tabbed">
      <n-tabs v-model:value="activeTab" type="line" animated class="app-list-page__tabs">
        <n-tab-pane v-for="pane in tabbedPanes" :key="pane.name" :name="pane.name" :tab="formatPaneTab(pane)">
          <section class="app-list-page__pane">
            <div v-if="pane.title || pane.description || pane.primaryAction" class="app-list-page__pane-header">
              <div class="app-list-page__pane-title">
                <h3 v-if="pane.title">{{ pane.title }}</h3>
                <p v-if="pane.description">{{ pane.description }}</p>
              </div>
              <n-button
                v-if="pane.primaryAction"
                :type="pane.primaryAction.type || 'primary'"
                :disabled="pane.primaryAction.disabled"
                :loading="pane.primaryAction.loading"
                @click="handleAction(pane.primaryAction)"
              >
                {{ pane.primaryAction.label }}
              </n-button>
            </div>
            <AppCollectionView
              :schema="resolveTableViewSchema(pane.view)"
              :rows="getPagedPaneRows(pane)"
              :loading="pane.loading || false"
              :sort-state="getPaneSortState(pane.name)"
              @sort-change="(state) => handlePaneSortChange(pane, state)"
            >
              <template v-if="pane.view.type === 'table'" #table-tools>
                <n-button v-if="hasToolbarRefresh" size="tiny" quaternary :loading="pane.loading" @click="handlePaneRefresh(pane)">
                  刷新
                </n-button>
                <AppTableRuntimeControls
                  v-model:fill-height="runtimeTableFillHeight"
                  v-model:row-density="runtimeTableRowDensity"
                  :columns="getRuntimeColumns(pane.view)"
                  :visible-column-keys="getVisibleColumnKeys(pane.view)"
                  :column-order-keys="getColumnOrderKeys(pane.view)"
                  @update:visible-column-keys="(keys) => updateVisibleColumnKeys(pane.view, keys)"
                  @update:column-order-keys="(keys) => updateColumnOrderKeys(pane.view, keys)"
                  @reset-columns="resetColumnSettings(pane.view)"
                />
              </template>
            </AppCollectionView>
            <AppPagination
              :pagination="getPanePagination(pane)"
              :item-count="pane.rows?.length || 0"
              @update:page="(page) => updatePanePage(pane.name, page)"
              @update:page-size="(pageSize) => updatePanePageSize(pane.name, pageSize)"
            />
          </section>
        </n-tab-pane>
      </n-tabs>
    </section>
    <AppCollectionView
      v-else
      :schema="resolvedViewSchema"
      :rows="pagedRows"
      :loading="loading"
      :sort-state="sortState"
      @sort-change="handleSortChange"
    >
      <template v-if="hasRuntimeTableTools" #table-tools>
        <n-button v-if="hasToolbarRefresh" size="tiny" quaternary @click="handleRefresh">刷新</n-button>
        <AppTableRuntimeControls
          v-model:fill-height="runtimeTableFillHeight"
          v-model:row-density="runtimeTableRowDensity"
          :columns="getRuntimeColumns(props.schema.view)"
          :visible-column-keys="getVisibleColumnKeys(props.schema.view)"
          :column-order-keys="getColumnOrderKeys(props.schema.view)"
          @update:visible-column-keys="(keys) => updateVisibleColumnKeys(props.schema.view, keys)"
          @update:column-order-keys="(keys) => updateColumnOrderKeys(props.schema.view, keys)"
          @reset-columns="resetColumnSettings(props.schema.view)"
        />
      </template>
      <template #[name]="slotProps" v-for="(_, name) in $slots" :key="name">
        <slot v-if="!reservedSlots.includes(String(name))" :name="name" v-bind="slotProps"></slot>
      </template>
    </AppCollectionView>

    <AppPagination
      v-if="!isTabbedListView && !isSplitListView"
      :pagination="resolvedPagination"
      :item-count="rows.length"
      @update:page="updatePage"
      @update:page-size="updatePageSize"
    />
  </AppPage>
</template>

<script lang="ts" setup generic="Row extends Record<string, unknown>, Query extends Record<string, unknown>">
  import { computed, ref, watch, useSlots } from 'vue';
  import { useDialog } from 'naive-ui';
  import type { DataTableColumn, DataTableColumns, PaginationProps } from 'naive-ui';
  import AppCollectionView from '../components/AppCollectionView.vue';
  import AppFilterBar from '../components/AppFilterBar.vue';
  import AppPage from '../components/AppPage.vue';
  import AppPageHeader from '../components/AppPageHeader.vue';
  import AppPageToolbar from '../components/AppPageToolbar.vue';
  import AppPagination from '../components/AppPagination.vue';
  import AppTableRuntimeControls from '../components/AppTableRuntimeControls.vue';
  import type { CollectionViewSchema, ListPageSchema, ListRuntimeState, PageAction, PageRuntimeContext, TabbedListPaneSchema, TableColumnPreferenceSchema, TableRowDensity, TableSortState } from '../types';

  const ROW_HEIGHT_BY_DENSITY: Record<TableRowDensity, number> = {
    default: 56,
    medium: 48,
    compact: 40,
  };
  const DEFAULT_PAGE = 1;
  const DEFAULT_PAGE_SIZE = 20;
  const DEFAULT_PAGE_SIZES = [20, 50, 100];

  interface RuntimePaginationState {
    page: number;
    pageSize: number;
  }

  const props = withDefaults(
    defineProps<{
      schema: ListPageSchema<Row, Query>;
      rows?: Row[];
      loading?: boolean;
    }>(),
    {
      rows: () => [],
      loading: false,
    }
  );

  const emit = defineEmits<{
    refresh: [state?: ListRuntimeState];
    sortChange: [state: TableSortState];
    runtimeChange: [state: ListRuntimeState];
  }>();
  const dialog = useDialog();
  const slots = useSlots();
  const runtimeTableFillHeight = ref(props.schema.view.tableLayout?.heightMode === 'fill');
  const runtimeTableRowDensity = ref<TableRowDensity>(props.schema.view.tableLayout?.rowDensity || 'default');
  const activeTab = ref(props.schema.view.tabs?.[0]?.name || '');
  const paginationState = ref<RuntimePaginationState>({
    page: getInitialPage(props.schema.pagination),
    pageSize: getInitialPageSize(props.schema.pagination),
  });
  const panePaginationState = ref<Record<string, RuntimePaginationState>>({});
  const splitPaginationState = ref<Record<'master' | 'detail', RuntimePaginationState>>({
    master: { page: DEFAULT_PAGE, pageSize: DEFAULT_PAGE_SIZE },
    detail: { page: DEFAULT_PAGE, pageSize: DEFAULT_PAGE_SIZE },
  });
  const sortState = ref<TableSortState>(props.schema.view.sort?.defaultSort || {});
  const paneSortState = ref<Record<string, TableSortState>>({});
  const splitSortState = ref<Record<'master' | 'detail', TableSortState>>({
    master: props.schema.view.split?.master.view.sort?.defaultSort || {},
    detail: props.schema.view.split?.detail.view.sort?.defaultSort || {},
  });
  const visibleColumnState = ref<Record<string, string[]>>({});
  const columnOrderState = ref<Record<string, string[]>>({});

  const reservedSlots = ['filters', 'toolbar-left', 'toolbar-right', 'header-actions', 'collection'];
  const hasDeclaredFilters = computed(() => !!props.schema.filters?.length);
  const rightTools = computed(() => props.schema.toolbar?.rightTools || []);
  const hasRefreshTool = computed(() => rightTools.value.includes('refresh'));
  const isTabbedListView = computed(() => props.schema.view.type === 'tabbed-list');
  const isSplitListView = computed(() => props.schema.view.type === 'split-list');
  const splitView = computed(() => props.schema.view.split);
  const splitStyle = computed(() => ({
    '--app-list-page-master-width': formatCssSize(splitView.value?.masterWidth || 300),
    '--app-list-page-split-min-height': formatCssSize(splitView.value?.minHeight || 420),
  }));
  const tabbedPanes = computed(() => props.schema.view.tabs || []);
  const hasRuntimeTableTools = computed(() => props.schema.view.type === 'table' || isTabbedListView.value || isSplitListView.value);
  const hasOnlyRefreshTool = computed(() => hasRefreshTool.value && rightTools.value.length === 1);
  const hasBatchActions = computed(() => !!props.schema.toolbar?.batchActions?.length);
  const hasNonRefreshRightTools = computed(() => rightTools.value.some((tool) => tool !== 'refresh'));
  const hasToolbarRefresh = computed(() => hasRefreshTool.value);
  const hasHeaderRefresh = computed(
    () => hasOnlyRefreshTool.value && !hasRuntimeTableTools.value && !slots['toolbar-right'] && !hasBatchActions.value
  );
  const hasPageToolbar = computed(
    () =>
      !!slots['toolbar-left'] ||
      !!slots['toolbar-right'] ||
      hasBatchActions.value ||
      hasNonRefreshRightTools.value
  );
  const resolvedViewSchema = computed(() => {
    if (props.schema.view.type !== 'table') {
      return props.schema.view;
    }
    return resolveTableViewSchema(props.schema.view);
  });
  const context = computed<PageRuntimeContext>(() => ({
    pageId: props.schema.id,
    density: props.schema.density || 'comfortable',
    variant: props.schema.variant || 'enterprise',
  }));
  const resolvedPagination = computed(() => {
    return resolvePagination(props.schema.pagination, props.rows.length, paginationState.value);
  });
  const pagedRows = computed(() => {
    return sliceRows(sortRows(props.rows, props.schema.view, sortState.value), props.schema.pagination, paginationState.value);
  });

  watch(
    tabbedPanes,
    (panes) => {
      if (!panes.length) {
        activeTab.value = '';
        return;
      }
      if (!panes.some((pane) => pane.name === activeTab.value)) {
        activeTab.value = panes[0].name;
      }
    },
    { immediate: true }
  );

  function handleAction(action: PageAction) {
    if (action.confirm) {
      dialog.warning({
        title: action.confirmTitle || '确认操作',
        content: action.confirmContent || '确认执行该操作吗？',
        positiveText: action.positiveText || '确认',
        negativeText: action.negativeText || '取消',
        onPositiveClick: () => action.onClick?.(context.value),
      });
      return;
    }
    return action.onClick?.(context.value);
  }

  function resolveTableViewSchema(view: CollectionViewSchema<Row>) {
    if (view.type !== 'table') return view;
    const visibleKeys = getVisibleColumnKeys(view);
    const runtimeColumns = getOrderedRuntimeColumns(view);
    const rowHeight = ROW_HEIGHT_BY_DENSITY[runtimeTableRowDensity.value];
    return {
      ...view,
      selectable: view.selectable ?? true,
      columnRuntime: {
        defaultResizable: true,
        ...view.columnRuntime,
        columns: runtimeColumns.map((column) => ({
          ...column,
          defaultVisible: column.required ? true : visibleKeys.includes(String(column.key)),
        })),
      },
      tableLayout: {
        tableLayout: 'fixed',
        ...view.tableLayout,
        rowHeight,
        minRowHeight: rowHeight,
        heightMode: runtimeTableFillHeight.value ? 'fill' : 'natural',
        rowDensity: runtimeTableRowDensity.value,
      },
    };
  }

  function formatPaneTab(pane: TabbedListPaneSchema<Row>) {
    return typeof pane.count === 'number' ? `${pane.label} (${pane.count})` : pane.label;
  }

  function getPanePagination(pane: TabbedListPaneSchema<Row>) {
    return resolvePagination(pane.pagination, pane.rows?.length || 0, getPanePaginationState(pane));
  }

  function getPagedPaneRows(pane: TabbedListPaneSchema<Row>) {
    return sliceRows(sortRows(pane.rows || [], pane.view, getPaneSortState(pane.name)), pane.pagination, getPanePaginationState(pane));
  }

  function getPanePaginationState(pane: TabbedListPaneSchema<Row>) {
    return panePaginationState.value[pane.name] || {
      page: getInitialPage(pane.pagination),
      pageSize: getInitialPageSize(pane.pagination),
    };
  }

  function getSplitPane(name: 'master' | 'detail') {
    return splitView.value?.[name];
  }

  function getSplitPagination(name: 'master' | 'detail') {
    const pane = getSplitPane(name);
    return resolvePagination(pane?.pagination, pane?.rows?.length || 0, getSplitPaginationState(name));
  }

  function getPagedSplitRows(name: 'master' | 'detail') {
    const pane = getSplitPane(name);
    return sliceRows(sortRows(pane?.rows || [], pane?.view, getSplitSortState(name)), pane?.pagination, getSplitPaginationState(name));
  }

  function getSplitPaginationState(name: 'master' | 'detail') {
    return splitPaginationState.value[name] || {
      page: DEFAULT_PAGE,
      pageSize: DEFAULT_PAGE_SIZE,
    };
  }

  function updateSplitPage(name: 'master' | 'detail', page: number) {
    const pane = getSplitPane(name);
    const current = getSplitPaginationState(name);
    splitPaginationState.value = {
      ...splitPaginationState.value,
      [name]: {
        ...current,
        page: clampPage(page, pane?.rows?.length || 0, current.pageSize),
      },
    };
    emitRuntimeChange();
  }

  function updateSplitPageSize(name: 'master' | 'detail', pageSize: number) {
    splitPaginationState.value = {
      ...splitPaginationState.value,
      [name]: {
        page: DEFAULT_PAGE,
        pageSize,
      },
    };
    emitRuntimeChange();
  }

  function updatePage(page: number) {
    paginationState.value = {
      ...paginationState.value,
      page: clampPage(page, props.rows.length, paginationState.value.pageSize),
    };
    emitRuntimeChange();
  }

  function updatePageSize(pageSize: number) {
    paginationState.value = {
      page: DEFAULT_PAGE,
      pageSize,
    };
    emitRuntimeChange();
  }

  function updatePanePage(name: string, page: number) {
    const pane = tabbedPanes.value.find((entry) => entry.name === name);
    const current = pane ? getPanePaginationState(pane) : {
      page: DEFAULT_PAGE,
      pageSize: DEFAULT_PAGE_SIZE,
    };
    panePaginationState.value = {
      ...panePaginationState.value,
      [name]: {
        ...current,
        page: clampPage(page, pane?.rows?.length || 0, current.pageSize),
      },
    };
  }

  function updatePanePageSize(name: string, pageSize: number) {
    const pane = tabbedPanes.value.find((entry) => entry.name === name);
    const current = pane ? getPanePaginationState(pane) : {
      page: DEFAULT_PAGE,
      pageSize: DEFAULT_PAGE_SIZE,
    };
    panePaginationState.value = {
      ...panePaginationState.value,
      [name]: {
        ...current,
        page: DEFAULT_PAGE,
        pageSize,
      },
    };
  }

  function handleSortChange(state: TableSortState) {
    sortState.value = state;
    paginationState.value = {
      ...paginationState.value,
      page: DEFAULT_PAGE,
    };
    emit('sortChange', state);
    emitRuntimeChange();
    if (props.schema.view.sort?.remote) {
      handleRefresh();
    }
  }

  function handlePaneSortChange(pane: TabbedListPaneSchema<Row>, state: TableSortState) {
    paneSortState.value = {
      ...paneSortState.value,
      [pane.name]: state,
    };
    const current = getPanePaginationState(pane);
    panePaginationState.value = {
      ...panePaginationState.value,
      [pane.name]: {
        ...current,
        page: DEFAULT_PAGE,
      },
    };
    if (pane.view.sort?.remote) {
      pane.refresh?.({
        pagination: getPanePaginationState(pane),
        sort: state,
      });
    }
  }

  function handleSplitSortChange(name: 'master' | 'detail', state: TableSortState) {
    splitSortState.value = {
      ...splitSortState.value,
      [name]: state,
    };
    splitPaginationState.value = {
      ...splitPaginationState.value,
      [name]: {
        ...getSplitPaginationState(name),
        page: DEFAULT_PAGE,
      },
    };
    const pane = getSplitPane(name);
    if (pane?.view.sort?.remote) {
      pane.refresh?.({
        pagination: getSplitPaginationState(name),
        sort: state,
      });
    }
  }

  function getPaneSortState(name: string) {
    return paneSortState.value[name] || {};
  }

  function getSplitSortState(name: 'master' | 'detail') {
    return splitSortState.value[name] || {};
  }

  function emitRuntimeChange() {
    emit('runtimeChange', currentRuntimeState());
  }

  function currentRuntimeState(): ListRuntimeState {
    return {
      pagination: paginationState.value,
      sort: sortState.value,
    };
  }

  function handleRefresh() {
    emit('refresh', currentRuntimeState());
  }

  function getRuntimeColumns(view: CollectionViewSchema<Row>): TableColumnPreferenceSchema<Row>[] {
    if (view.type !== 'table') return [];
    const explicitColumns = view.columnRuntime?.columns || [];
    const explicitColumnMap = new Map(explicitColumns.map((column) => [String(column.key), column]));
    const discoveredColumns = collectColumnPreferences(view.columns || [], explicitColumnMap, explicitColumns.length > 0);
    const discoveredKeySet = new Set(discoveredColumns.map((column) => String(column.key)));
    const extraColumns = explicitColumns.filter((column) => !discoveredKeySet.has(String(column.key)));
    return [...discoveredColumns, ...extraColumns];
  }

  function getVisibleColumnKeys(view: CollectionViewSchema<Row>) {
    if (view.type !== 'table') return [];
    const key = getViewStorageKey(view);
    if (!visibleColumnState.value[key]) {
      visibleColumnState.value = {
        ...visibleColumnState.value,
        [key]: loadVisibleColumnKeys(view),
      };
    }
    return visibleColumnState.value[key];
  }

  function updateVisibleColumnKeys(view: CollectionViewSchema<Row>, keys: string[]) {
    const runtimeColumns = getRuntimeColumns(view);
    const requiredKeys = runtimeColumns.filter((column) => column.required).map((column) => String(column.key));
    const nextKeys = Array.from(new Set([...keys, ...requiredKeys]));
    const key = getViewStorageKey(view);
    visibleColumnState.value = {
      ...visibleColumnState.value,
      [key]: nextKeys,
    };
    saveVisibleColumnKeys(key, nextKeys);
  }

  function getColumnOrderKeys(view: CollectionViewSchema<Row>) {
    if (view.type !== 'table') return [];
    const key = getViewStorageKey(view);
    if (!columnOrderState.value[key]) {
      columnOrderState.value = {
        ...columnOrderState.value,
        [key]: loadColumnOrderKeys(view),
      };
    }
    return columnOrderState.value[key];
  }

  function updateColumnOrderKeys(view: CollectionViewSchema<Row>, keys: string[]) {
    const runtimeKeys = new Set(getRuntimeColumns(view).map((column) => String(column.key)));
    const nextKeys = keys.map(String).filter((key) => runtimeKeys.has(key));
    const key = getViewStorageKey(view);
    columnOrderState.value = {
      ...columnOrderState.value,
      [key]: nextKeys,
    };
    saveColumnOrderKeys(key, nextKeys);
  }

  function resetColumnSettings(view: CollectionViewSchema<Row>) {
    const key = getViewStorageKey(view);
    const nextVisibleKeys = defaultVisibleColumnKeys(view);
    const nextOrderKeys = defaultColumnOrderKeys(view);
    visibleColumnState.value = {
      ...visibleColumnState.value,
      [key]: nextVisibleKeys,
    };
    columnOrderState.value = {
      ...columnOrderState.value,
      [key]: nextOrderKeys,
    };
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(columnStorageKey(key));
      window.localStorage.removeItem(columnOrderStorageKey(key));
    }
  }

  function loadVisibleColumnKeys(view: CollectionViewSchema<Row>) {
    const key = getViewStorageKey(view);
    if (typeof window !== 'undefined') {
      const stored = window.localStorage.getItem(columnStorageKey(key));
      if (stored) {
        try {
          const payload = JSON.parse(stored);
          if (Array.isArray(payload)) {
            return payload.map(String);
          }
        } catch {
          // Ignore corrupted local preferences and fall back to schema defaults.
        }
      }
    }
    return defaultVisibleColumnKeys(view);
  }

  function saveVisibleColumnKeys(key: string, keys: string[]) {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(columnStorageKey(key), JSON.stringify(keys));
  }

  function loadColumnOrderKeys(view: CollectionViewSchema<Row>) {
    const key = getViewStorageKey(view);
    if (typeof window !== 'undefined') {
      const stored = window.localStorage.getItem(columnOrderStorageKey(key));
      if (stored) {
        try {
          const payload = JSON.parse(stored);
          if (Array.isArray(payload)) {
            return payload.map(String);
          }
        } catch {
          // Ignore corrupted local preferences and fall back to schema defaults.
        }
      }
    }
    return defaultColumnOrderKeys(view);
  }

  function saveColumnOrderKeys(key: string, keys: string[]) {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(columnOrderStorageKey(key), JSON.stringify(keys));
  }

  function defaultVisibleColumnKeys(view: CollectionViewSchema<Row>) {
    return getRuntimeColumns(view)
      .filter((column) => column.defaultVisible !== false || column.required)
      .map((column) => String(column.key));
  }

  function defaultColumnOrderKeys(view: CollectionViewSchema<Row>) {
    return getRuntimeColumns(view).map((column) => String(column.key));
  }

  function getOrderedRuntimeColumns(view: CollectionViewSchema<Row>) {
    const columns = getRuntimeColumns(view);
    const orderKeys = getColumnOrderKeys(view);
    if (!orderKeys.length) return columns;
    const columnMap = new Map(columns.map((column) => [String(column.key), column]));
    const orderedColumns = orderKeys
      .map((key) => columnMap.get(String(key)))
      .filter((column): column is TableColumnPreferenceSchema<Row> => !!column);
    const orderedKeySet = new Set(orderedColumns.map((column) => String(column.key)));
    const remainingColumns = columns.filter((column) => !orderedKeySet.has(String(column.key)));
    return [...orderedColumns, ...remainingColumns];
  }

  function collectColumnPreferences(
    columns: DataTableColumns<Row>,
    explicitColumnMap: Map<string, TableColumnPreferenceSchema<Row>>,
    hasExplicitColumns: boolean
  ): TableColumnPreferenceSchema<Row>[] {
    return columns.flatMap((column) => {
      if ('children' in column && column.children) {
        return collectColumnPreferences(column.children as DataTableColumns<Row>, explicitColumnMap, hasExplicitColumns);
      }

      if ('type' in column && (column.type === 'selection' || column.type === 'expand')) {
        return [];
      }

      const columnKey = getTableColumnKey(column);
      if (columnKey === undefined) return [];

      const explicitColumn = explicitColumnMap.get(String(columnKey));
      return [{
        key: columnKey,
        label: explicitColumn?.label || getTableColumnLabel(column) || String(columnKey),
        defaultVisible: explicitColumn?.defaultVisible ?? true,
        required: explicitColumn?.required ?? String(columnKey) === 'actions',
        sortable: explicitColumn ? explicitColumn.sortable === true : !hasExplicitColumns && isAutoSortableColumnKey(columnKey),
        sortField: explicitColumn?.sortField,
        width: explicitColumn?.width || getTableColumnWidth(column),
        fixed: explicitColumn?.fixed || getTableColumnFixed(column),
        getLabel: explicitColumn?.getLabel,
      }];
    });
  }

  function getTableColumnKey(column: DataTableColumn<Row>) {
    return 'key' in column ? column.key : undefined;
  }

  function getTableColumnLabel(column: DataTableColumn<Row>) {
    if ('title' in column && typeof column.title === 'string') return column.title;
    return '';
  }

  function getTableColumnWidth(column: DataTableColumn<Row>) {
    return 'width' in column && typeof column.width === 'number' ? column.width : undefined;
  }

  function getTableColumnFixed(column: DataTableColumn<Row>) {
    return 'fixed' in column && (column.fixed === 'left' || column.fixed === 'right') ? column.fixed : undefined;
  }

  function isAutoSortableColumnKey(key: string | number) {
    const text = String(key);
    return text !== 'actions' && !text.startsWith('__');
  }

  function getViewStorageKey(view: CollectionViewSchema<Row>) {
    const key = view.itemKey || view.rowKey;
    const keyLabel = typeof key === 'string' ? key : view.mode || 'default';
    return `${props.schema.id}:${view.type}:${keyLabel}`;
  }

  function columnStorageKey(key: string) {
    return `ops-admin:page-runtime:columns:${key}`;
  }

  function columnOrderStorageKey(key: string) {
    return `ops-admin:page-runtime:column-order:${key}`;
  }

  function resolvePagination(
    pagination: false | PaginationProps | undefined,
    itemCount: number,
    state: RuntimePaginationState
  ): false | PaginationProps {
    if (pagination === false) return false;
    return {
      pageSizes: DEFAULT_PAGE_SIZES,
      showSizePicker: true,
      ...(pagination || {}),
      itemCount,
      page: state.page,
      pageSize: state.pageSize,
    };
  }

  function sliceRows(items: Row[], pagination: false | PaginationProps | undefined, state: RuntimePaginationState) {
    if (pagination === false) return items;
    const pageSize = Math.max(1, state.pageSize);
    const page = clampPage(state.page, items.length, pageSize);
    const start = (page - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }

  function sortRows(items: Row[], view: CollectionViewSchema<Row> | undefined, state: TableSortState) {
    if (!view || view.type !== 'table' || view.sort?.remote || !state.sort_by || !state.sort_dir) return items;
    const sortableColumn = getRuntimeColumns(view).find((column) => {
      const field = column.sortField || String(column.key);
      return column.sortable && field === state.sort_by;
    });
    if (!sortableColumn) return items;
    const columnKey = String(sortableColumn.key);
    const direction = state.sort_dir === 'asc' ? 1 : -1;
    return [...items].sort((left, right) => compareValues(left[columnKey], right[columnKey]) * direction);
  }

  function compareValues(left: unknown, right: unknown) {
    if (left === right) return 0;
    if (left == null) return -1;
    if (right == null) return 1;
    const leftNumber = typeof left === 'number' ? left : Number(left);
    const rightNumber = typeof right === 'number' ? right : Number(right);
    if (!Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)) {
      return leftNumber - rightNumber;
    }
    return String(left).localeCompare(String(right), 'zh-Hans-CN');
  }

  function getInitialPage(pagination: false | PaginationProps | undefined) {
    return pagination === false ? DEFAULT_PAGE : pagination?.page || pagination?.defaultPage || DEFAULT_PAGE;
  }

  function getInitialPageSize(pagination: false | PaginationProps | undefined) {
    return pagination === false ? DEFAULT_PAGE_SIZE : pagination?.pageSize || pagination?.defaultPageSize || DEFAULT_PAGE_SIZE;
  }

  function clampPage(page: number, itemCount: number, pageSize: number) {
    const pageCount = Math.max(1, Math.ceil(itemCount / Math.max(1, pageSize)));
    return Math.min(Math.max(1, page), pageCount);
  }

  async function handlePaneRefresh(pane: TabbedListPaneSchema<Row>) {
    if (pane.refresh) {
      await pane.refresh({
        pagination: getPanePaginationState(pane),
        sort: getPaneSortState(pane.name),
      });
      return;
    }
    handleRefresh();
  }

  async function handleSplitRefresh(name: 'master' | 'detail') {
    const pane = getSplitPane(name);
    if (pane?.refresh) {
      await pane.refresh({
        pagination: getSplitPaginationState(name),
        sort: getSplitSortState(name),
      });
      return;
    }
    handleRefresh();
  }

  function formatCssSize(value: number | string) {
    return typeof value === 'number' ? `${value}px` : value;
  }

  watch(
    tabbedPanes,
    (panes) => {
      if (!panes.length) return;
      if (!panes.some((pane) => pane.name === activeTab.value)) {
        activeTab.value = panes[0].name;
      }
    },
    { immediate: true }
  );
  watch(
    () => [props.schema.id, props.schema.pagination] as const,
    () => {
      paginationState.value = {
        page: getInitialPage(props.schema.pagination),
        pageSize: getInitialPageSize(props.schema.pagination),
      };
    }
  );
  watch(
    () => props.rows.length,
    (itemCount) => {
      paginationState.value = {
        ...paginationState.value,
        page: clampPage(paginationState.value.page, itemCount, paginationState.value.pageSize),
      };
    }
  );
  watch(
    tabbedPanes,
    (panes) => {
      const nextState: Record<string, RuntimePaginationState> = {};
      panes.forEach((pane) => {
        const current = panePaginationState.value[pane.name] || {
          page: getInitialPage(pane.pagination),
          pageSize: getInitialPageSize(pane.pagination),
        };
        nextState[pane.name] = {
          ...current,
          page: clampPage(current.page, pane.rows?.length || 0, current.pageSize),
        };
      });
      panePaginationState.value = nextState;
    },
    { immediate: true }
  );
</script>

<style lang="less" scoped>
  .app-list-page__collection {
    min-width: 0;
  }

  .app-list-page__tabbed {
    min-width: 0;
  }

  .app-list-page__split {
    display: grid;
    grid-template-columns: minmax(240px, var(--app-list-page-master-width)) minmax(0, 1fr);
    gap: var(--app-page-section-gap);
    align-items: start;
    min-width: 0;
    min-height: var(--app-list-page-split-min-height);
  }

  .app-list-page__split-pane {
    display: grid;
    gap: var(--app-page-section-gap);
    min-width: 0;
  }

  .app-list-page__embedded-header {
    display: flex;
    gap: var(--app-page-toolbar-gap);
    align-items: flex-start;
    justify-content: space-between;
    min-width: 0;
  }

  .app-list-page__embedded-copy {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .app-list-page__embedded-copy h3 {
    margin: 0;
    overflow-wrap: anywhere;
    color: var(--app-text-color);
    font-size: 15px;
    font-weight: 650;
    line-height: 1.35;
    letter-spacing: 0;
  }

  .app-list-page__embedded-copy p {
    margin: 0;
    color: var(--app-icon-color);
    font-size: 12px;
    line-height: 1.45;
  }

  .app-list-page__embedded-actions {
    display: inline-flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
    min-width: 0;
  }

  .app-list-page__tabs :deep(.n-tabs-nav) {
    padding: 0 4px;
  }

  .app-list-page__pane {
    display: grid;
    gap: var(--app-page-section-gap);
  }

  .app-list-page__pane-header {
    display: flex;
    gap: var(--app-page-toolbar-gap);
    align-items: flex-start;
    justify-content: space-between;
    min-width: 0;
    padding-top: 2px;
  }

  .app-list-page__pane-title {
    min-width: 0;
    padding-left: 4px;
  }

  .app-list-page__pane-title h3 {
    margin: 0 0 4px;
    color: var(--app-text-color);
    font-size: 16px;
    line-height: 1.35;
    font-weight: 650;
  }

  .app-list-page__pane-title p {
    margin: 0;
    color: var(--app-text-color-2);
    font-size: 13px;
    line-height: 1.5;
  }

  .app-list-page__pane-actions {
    display: inline-flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
    min-width: 0;
  }

  @media (max-width: 900px) {
    .app-list-page__embedded-header {
      flex-direction: column;
      align-items: stretch;
    }

    .app-list-page__embedded-actions {
      justify-content: flex-start;
    }

    .app-list-page__pane-header {
      width: 100%;
      min-width: 0;
      flex-direction: column;
      align-items: stretch;
    }

    .app-list-page__pane-title {
      padding-left: 0;
    }

    .app-list-page__pane-actions {
      justify-content: flex-start;
    }

    .app-list-page__pane-header :deep(.n-button) {
      align-self: flex-start;
    }
  }
</style>
