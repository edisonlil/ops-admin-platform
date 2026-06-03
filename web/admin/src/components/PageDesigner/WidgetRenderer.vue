<template>
  <div class="page-widget" :class="`page-widget--${component.type}`">
    <div class="page-widget__head">
      <strong>{{ title }}</strong>
      <span>{{ definition.label }}</span>
    </div>
    <div class="page-widget__body">
      <template v-if="component.type === 'metric_card'">
        <div class="page-widget__metric">{{ metricData.value || component.props?.value || '0' }}</div>
        <div class="page-widget__trend">{{ metricData.trend || component.props?.trend || '0%' }}</div>
      </template>
      <template v-else-if="component.type === 'text_block'">
        <p>{{ component.props?.content || '输入说明内容' }}</p>
      </template>
      <template v-else-if="component.type === 'quick_link'">
        <n-button size="small" type="primary" ghost>{{ component.props?.text || '打开功能' }}</n-button>
      </template>
      <template v-else-if="component.type === 'data_table'">
        <div class="page-widget__table">
          <template v-if="tablePreview.columns.length">
            <div class="page-widget__table-head">
              <span v-for="column in tablePreview.columns" :key="column.key">{{ column.title }}</span>
            </div>
            <div v-for="(row, rowIndex) in tablePreview.rows" :key="rowIndex" class="page-widget__table-row">
              <span v-for="column in tablePreview.columns" :key="column.key">{{ row[column.key] ?? '' }}</span>
            </div>
          </template>
          <span v-for="row in tableRows" v-else :key="row"></span>
        </div>
      </template>
      <template v-else-if="isEChartWidget">
        <WidgetEChart :component="component" :data="staticData" />
      </template>
      <template v-else>
        <p>{{ component.props?.description || '组件预览' }}</p>
      </template>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import type { DatasetRuntimePayload } from '@/api/datasets';
  import type { PageComponentConfig } from '@/api/pageDesigner';
  import WidgetEChart from './WidgetEChart.vue';
  import { chartWidgetTypes, componentTitle, datasetIdForComponent, parseWidgetData, widgetDefinition } from './widgets';

  const props = defineProps<{
    component: PageComponentConfig;
    datasetPayloads?: Record<string, DatasetRuntimePayload | null | undefined>;
  }>();

  const echartWidgetTypes = chartWidgetTypes.filter((type) => type !== 'metric_card');
  const definition = computed(() => widgetDefinition(props.component.type));
  const title = computed(() => componentTitle(props.component));
  const datasetId = computed(() => datasetIdForComponent(props.component));
  const datasetPayload = computed(() => (datasetId.value ? props.datasetPayloads?.[datasetId.value] || null : null));
  const staticData = computed(() => parseWidgetData(props.component, datasetPayload.value) as Record<string, unknown>);
  const metricData = computed(() => staticData.value || {});
  const isEChartWidget = computed(() => echartWidgetTypes.includes(props.component.type));
  const tableRows = computed(() => {
    const data = staticData.value as { rows?: unknown[] };
    return Array.from({ length: Math.max(1, Math.min(data.rows?.length || Number(props.component.props?.rows) || 4, 8)) }, (_, index) => index);
  });
  const tablePreview = computed(() => {
    const data = staticData.value as {
      columns?: Array<{ key?: string; title?: string }>;
      rows?: Array<Record<string, unknown>>;
    };
    const columns = Array.isArray(data.columns)
      ? data.columns
          .map((column) => ({ key: String(column.key || ''), title: String(column.title || column.key || '') }))
          .filter((column) => column.key)
      : [];
    const rows = Array.isArray(data.rows) ? data.rows.slice(0, Math.max(1, Math.min(Number(props.component.props?.rows) || 5, 12))) : [];
    return { columns, rows };
  });
</script>

<style lang="less" scoped>
  .page-widget {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
    overflow: hidden;
    color: var(--app-text-color, #111827);
    font-family: var(
      --app-font-family-base,
      system-ui,
      -apple-system,
      BlinkMacSystemFont,
      'Segoe UI',
      'Microsoft YaHei',
      'PingFang SC',
      sans-serif
    );
    background: var(--app-card-bg, var(--app-surface-bg, #fff));
    border: 1px solid var(--app-card-border-color, var(--app-border-color, #e5e7eb));
    border-radius: var(--app-card-radius, 6px);
    box-shadow: var(--app-card-shadow, none);
  }

  .page-widget__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-height: 34px;
    padding: 8px 14px 4px;

    strong {
      min-width: 0;
      overflow: hidden;
      color: var(--app-text-color, #111827);
      font-size: var(--app-font-size-md, 14px);
      font-weight: 650;
      line-height: 20px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      flex: 0 0 auto;
      color: var(--app-icon-color, var(--app-text-color-2, #64748b));
      font-size: var(--app-font-size-xs, 12px);
      line-height: 18px;
    }
  }

  .page-widget__body {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    padding: 4px 14px 12px;
  }

  .page-widget--metric_card .page-widget__body {
    justify-content: center;
    padding-block: 4px 14px;
  }

  .page-widget__metric {
    color: var(--app-text-color, #111827);
    font-size: 30px;
    font-weight: 700;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
  }

  .page-widget__trend {
    margin-top: 8px;
    color: var(--app-success-color, #18a058);
    font-size: var(--app-font-size-sm, 13px);
    line-height: 18px;
    font-variant-numeric: tabular-nums;
  }

  .page-widget__table {
    display: grid;
    gap: 8px;
    overflow: hidden;

    span {
      height: 14px;
      background: var(--app-surface-muted-bg, #e2e8f0);
      border-radius: 3px;
    }
  }

  .page-widget__table-head,
  .page-widget__table-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(72px, 1fr));
    gap: 8px;

    span {
      min-width: 0;
      height: auto;
      overflow: hidden;
      color: var(--app-text-color-2, #475569);
      font-size: var(--app-font-size-xs, 12px);
      line-height: 20px;
      text-overflow: ellipsis;
      white-space: nowrap;
      background: transparent;
      border-radius: 0;
    }
  }

  .page-widget__table-head span {
    color: var(--app-text-color, #111827);
    font-weight: 650;
  }

  .page-widget__table-row {
    padding-top: 6px;
    border-top: 1px solid var(--app-border-color, #e2e8f0);
  }

  p {
    margin: 0;
    color: var(--app-text-color-2, #475569);
    font-size: var(--app-font-size-sm, 13px);
    line-height: 1.7;
  }
</style>
