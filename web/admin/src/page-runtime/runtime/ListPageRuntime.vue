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
        <n-button v-if="hasHeaderRefresh" size="small" quaternary @click="emit('refresh')">刷新</n-button>
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
        <n-button v-if="hasHeaderRefresh" size="small" quaternary @click="emit('refresh')">刷新</n-button>
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
        <n-button v-if="hasToolbarRefresh && !hasRuntimeTableTools" size="small" quaternary @click="emit('refresh')">刷新</n-button>
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
        >
          <template v-if="splitView.detail.view.type === 'table'" #table-tools>
            <n-button v-if="hasToolbarRefresh" size="tiny" quaternary :loading="splitView.detail.loading" @click="handleSplitRefresh('detail')">
              刷新
            </n-button>
            <AppTableRuntimeControls
              v-model:fill-height="runtimeTableFillHeight"
              v-model:row-density="runtimeTableRowDensity"
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
            >
              <template v-if="pane.view.type === 'table'" #table-tools>
                <n-button v-if="hasToolbarRefresh" size="tiny" quaternary :loading="pane.loading" @click="handlePaneRefresh(pane)">
                  刷新
                </n-button>
                <AppTableRuntimeControls
                  v-model:fill-height="runtimeTableFillHeight"
                  v-model:row-density="runtimeTableRowDensity"
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
    <AppCollectionView v-else :schema="resolvedViewSchema" :rows="pagedRows" :loading="loading">
      <template v-if="hasRuntimeTableTools" #table-tools>
        <n-button v-if="hasToolbarRefresh" size="tiny" quaternary @click="emit('refresh')">刷新</n-button>
        <AppTableRuntimeControls
          v-model:fill-height="runtimeTableFillHeight"
          v-model:row-density="runtimeTableRowDensity"
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
  import type { PaginationProps } from 'naive-ui';
  import AppCollectionView from '../components/AppCollectionView.vue';
  import AppFilterBar from '../components/AppFilterBar.vue';
  import AppPage from '../components/AppPage.vue';
  import AppPageHeader from '../components/AppPageHeader.vue';
  import AppPageToolbar from '../components/AppPageToolbar.vue';
  import AppPagination from '../components/AppPagination.vue';
  import AppTableRuntimeControls from '../components/AppTableRuntimeControls.vue';
  import type { CollectionViewSchema, ListPageSchema, PageAction, PageRuntimeContext, TabbedListPaneSchema, TableRowDensity } from '../types';

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
    refresh: [];
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
    return sliceRows(props.rows, props.schema.pagination, paginationState.value);
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
    const rowHeight = ROW_HEIGHT_BY_DENSITY[runtimeTableRowDensity.value];
    return {
      ...view,
      selectable: view.selectable ?? true,
      columnRuntime: {
        defaultResizable: true,
        ...view.columnRuntime,
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
    return sliceRows(pane.rows || [], pane.pagination, getPanePaginationState(pane));
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
    return sliceRows(pane?.rows || [], pane?.pagination, getSplitPaginationState(name));
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
  }

  function updateSplitPageSize(name: 'master' | 'detail', pageSize: number) {
    splitPaginationState.value = {
      ...splitPaginationState.value,
      [name]: {
        page: DEFAULT_PAGE,
        pageSize,
      },
    };
  }

  function updatePage(page: number) {
    paginationState.value = {
      ...paginationState.value,
      page: clampPage(page, props.rows.length, paginationState.value.pageSize),
    };
  }

  function updatePageSize(pageSize: number) {
    paginationState.value = {
      page: DEFAULT_PAGE,
      pageSize,
    };
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
      await pane.refresh();
      return;
    }
    emit('refresh');
  }

  async function handleSplitRefresh(name: 'master' | 'detail') {
    const pane = getSplitPane(name);
    if (pane?.refresh) {
      await pane.refresh();
      return;
    }
    emit('refresh');
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
