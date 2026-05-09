<template>
  <AppPage :density="schema.density" :variant="schema.variant">
    <AppPageHeader :title="schema.title" :description="schema.description">
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

    <AppPagination :pagination="schema.pagination" />
  </AppPage>
</template>

<script lang="ts" setup generic="Row extends Record<string, unknown>, Query extends Record<string, unknown>">
  import { computed, ref, useSlots } from 'vue';
  import AppCollectionView from '../components/AppCollectionView.vue';
  import AppFilterBar from '../components/AppFilterBar.vue';
  import AppPage from '../components/AppPage.vue';
  import AppPageHeader from '../components/AppPageHeader.vue';
  import AppPageToolbar from '../components/AppPageToolbar.vue';
  import AppPagination from '../components/AppPagination.vue';
  import AppTableRuntimeControls from '../components/AppTableRuntimeControls.vue';
  import type { ListPageSchema, PageAction, PageRuntimeContext, TableRowDensity } from '../types';

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

  const reservedSlots = ['filters', 'toolbar-left', 'toolbar-right', 'header-actions', 'collection'];
  const hasDeclaredFilters = computed(() => !!props.schema.filters?.length);
  const rightTools = computed(() => props.schema.toolbar?.rightTools || []);
  const hasRefreshTool = computed(() => rightTools.value.includes('refresh'));
  const hasRuntimeTableTools = computed(() => props.schema.view.type === 'table');
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
    const rowHeight = ROW_HEIGHT_BY_DENSITY[runtimeTableRowDensity.value];
    return {
      ...props.schema.view,
      selectable: props.schema.view.selectable ?? true,
      columnRuntime: {
        defaultResizable: true,
        ...props.schema.view.columnRuntime,
      },
      tableLayout: {
        tableLayout: 'fixed',
        ...props.schema.view.tableLayout,
        rowHeight,
        minRowHeight: rowHeight,
        heightMode: runtimeTableFillHeight.value ? 'fill' : 'natural',
        rowDensity: runtimeTableRowDensity.value,
      },
    };
  });
  const context = computed<PageRuntimeContext>(() => ({
    pageId: props.schema.id,
    density: props.schema.density || 'comfortable',
    variant: props.schema.variant || 'enterprise',
  }));

  function handleAction(action: PageAction) {
    return action.onClick?.(context.value);
  }
</script>

<style lang="less" scoped>
  .app-list-page__collection {
    min-width: 0;
  }
</style>
