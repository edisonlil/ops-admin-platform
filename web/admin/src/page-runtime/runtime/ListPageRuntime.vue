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
            <AppCollectionView :schema="resolveTableViewSchema(pane.view)" :rows="pane.rows || []" :loading="pane.loading || false">
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
            <AppPagination :pagination="pane.pagination" />
          </section>
        </n-tab-pane>
      </n-tabs>
    </section>
    <AppCollectionView v-else :schema="resolvedViewSchema" :rows="rows" :loading="loading">
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

    <AppPagination v-if="!isTabbedListView" :pagination="schema.pagination" />
  </AppPage>
</template>

<script lang="ts" setup generic="Row extends Record<string, unknown>, Query extends Record<string, unknown>">
  import { computed, ref, watch, useSlots } from 'vue';
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
  const slots = useSlots();
  const runtimeTableFillHeight = ref(props.schema.view.tableLayout?.heightMode === 'fill');
  const runtimeTableRowDensity = ref<TableRowDensity>(props.schema.view.tableLayout?.rowDensity || 'default');
  const activeTab = ref(props.schema.view.tabs?.[0]?.name || '');

  const reservedSlots = ['filters', 'toolbar-left', 'toolbar-right', 'header-actions', 'collection'];
  const hasDeclaredFilters = computed(() => !!props.schema.filters?.length);
  const rightTools = computed(() => props.schema.toolbar?.rightTools || []);
  const hasRefreshTool = computed(() => rightTools.value.includes('refresh'));
  const isTabbedListView = computed(() => props.schema.view.type === 'tabbed-list');
  const tabbedPanes = computed(() => props.schema.view.tabs || []);
  const hasRuntimeTableTools = computed(() => props.schema.view.type === 'table' || isTabbedListView.value);
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

  function handleAction(action: PageAction) {
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

  async function handlePaneRefresh(pane: TabbedListPaneSchema<Row>) {
    if (pane.refresh) {
      await pane.refresh();
      return;
    }
    emit('refresh');
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
</script>

<style lang="less" scoped>
  .app-list-page__collection {
    min-width: 0;
  }

  .app-list-page__tabbed {
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

    .app-list-page__pane-header :deep(.n-button) {
      align-self: flex-start;
    }
  }
</style>
