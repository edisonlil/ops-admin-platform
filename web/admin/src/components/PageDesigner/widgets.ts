import type { PageComponentConfig } from '@/api/pageDesigner';
import type { DatasetField, DatasetRuntimePayload } from '@/api/datasets';

export interface WidgetDefinition {
  type: string;
  label: string;
  defaultTitle: string;
  defaultProps: Record<string, unknown>;
  defaultSize: {
    w: number;
    h: number;
  };
}

export type WidgetDataSourceType = 'static_json' | 'dataset';

export type WidgetDatasetFilterOperator = 'eq' | 'neq' | 'contains' | 'gt' | 'gte' | 'lt' | 'lte';

export interface WidgetDatasetFilterConfig {
  field?: string;
  operator?: WidgetDatasetFilterOperator;
  value?: unknown;
  enabled?: boolean;
}

export interface WidgetDatasetConfig {
  xAxisField?: string;
  yAxisFields?: string[];
  pieValueMode?: 'count' | 'field';
  pieValueField?: string;
  pieSortBy?: 'name' | 'value';
  pieSortDirection?: 'asc' | 'desc';
  filters?: WidgetDatasetFilterConfig[];
}

export interface WidgetDataSourceConfig {
  type: WidgetDataSourceType;
  staticJson?: string;
  datasetId?: string | number | null;
  datasetConfig?: WidgetDatasetConfig;
}

export const chartWidgetTypes = [
  'metric_card',
  'line_chart',
  'bar_chart',
  'pie_chart',
  'stacked_area_chart',
  'scatter_chart',
  'radar_chart',
  'gauge_chart',
];
export const dataDrivenWidgetTypes = [...chartWidgetTypes, 'data_table'];

export function isDataDrivenWidget(type: string) {
  return dataDrivenWidgetTypes.includes(type);
}

export function sampleDataForWidget(type: string) {
  if (type === 'metric_card') {
    return {
      value: '128.6万',
      trend: '+12.8%',
      unit: '',
    };
  }

  if (type === 'data_table') {
    return {
      columns: [
        { key: 'name', title: '名称' },
        { key: 'status', title: '状态' },
        { key: 'count', title: '数量' },
      ],
      rows: [
        { name: '客户 A', status: '正常', count: 128 },
        { name: '客户 B', status: '跟进中', count: 76 },
      ],
    };
  }

  if (type === 'pie_chart') {
    return {
      categories: ['线上渠道', '线下渠道', '自然搜索', '复购客户'],
      series: [
        {
          name: '占比',
          data: [36, 24, 18, 22],
        },
      ],
    };
  }

  if (type === 'stacked_area_chart') {
    return {
      categories: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      series: [
        {
          name: '新增',
          data: [12, 18, 22, 28, 25, 31, 36],
        },
        {
          name: '活跃',
          data: [18, 22, 27, 32, 30, 35, 40],
        },
        {
          name: '转化',
          data: [8, 10, 14, 18, 16, 20, 24],
        },
      ],
    };
  }

  if (type === 'scatter_chart') {
    return {
      categories: ['样本 A', '样本 B', '样本 C', '样本 D', '样本 E', '样本 F', '样本 G'],
      series: [
        {
          name: '样本分布',
          data: [
            [12, 18],
            [18, 31],
            [24, 24],
            [31, 42],
            [36, 28],
            [42, 49],
            [48, 38],
          ],
        },
      ],
    };
  }

  if (type === 'radar_chart') {
    return {
      categories: ['响应速度', '稳定性', '转化率', '满意度', '覆盖率', '成本控制'],
      series: [
        {
          name: '当前表现',
          data: [86, 92, 74, 88, 79, 68],
        },
      ],
    };
  }

  if (type === 'gauge_chart') {
    return {
      value: 76,
      max: 100,
      unit: '%',
      label: '完成率',
      thresholds: [
        { label: '低', value: 40 },
        { label: '中', value: 70 },
        { label: '高', value: 100 },
      ],
    };
  }

  return {
    categories: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    series: [
      {
        name: '计数',
        data: [12, 18, 24, 31, 28, 36, 42],
      },
    ],
  };
}

export function sampleDataJsonForWidget(type: string) {
  return JSON.stringify(sampleDataForWidget(type), null, 2);
}

export function defaultDataSourceForWidget(type: string): WidgetDataSourceConfig {
  return {
    type: 'static_json',
    staticJson: sampleDataJsonForWidget(type),
  };
}

export function withDefaultDataSource(type: string, props: Record<string, unknown> = {}) {
  if (!isDataDrivenWidget(type)) return { ...props };
  const dataSource = props.dataSource as WidgetDataSourceConfig | undefined;
  return {
    ...props,
    dataSource:
      dataSource && typeof dataSource === 'object'
        ? {
            type: dataSource.type || 'static_json',
            staticJson: dataSource.staticJson || sampleDataJsonForWidget(type),
            datasetId: dataSource.datasetId,
            datasetConfig: normalizeDatasetConfig(dataSource.datasetConfig),
          }
        : defaultDataSourceForWidget(type),
  };
}

export function normalizeDatasetConfig(config?: WidgetDatasetConfig): WidgetDatasetConfig {
  const filters = Array.isArray(config?.filters)
    ? config.filters.map((filter) => ({
        field: String(filter?.field || ''),
        operator: filter?.operator || 'eq',
        value: filter?.value ?? '',
        enabled: filter?.enabled !== false,
      }))
    : [];
  return {
    xAxisField: String(config?.xAxisField || ''),
    yAxisFields: Array.isArray(config?.yAxisFields) ? config.yAxisFields.map((field) => String(field || '')).filter(Boolean) : [],
    pieValueMode: config?.pieValueMode === 'field' ? 'field' : 'count',
    pieValueField: String(config?.pieValueField || ''),
    pieSortBy: config?.pieSortBy === 'value' ? 'value' : 'name',
    pieSortDirection: config?.pieSortDirection === 'desc' ? 'desc' : 'asc',
    filters,
  };
}

export function parseStaticWidgetData(component?: PageComponentConfig) {
  if (!component) return sampleDataForWidget('metric_card');
  const dataSource = component.props?.dataSource as WidgetDataSourceConfig | undefined;
  if (dataSource?.type !== 'static_json' || !dataSource.staticJson) {
    return sampleDataForWidget(component.type);
  }

  try {
    return JSON.parse(dataSource.staticJson);
  } catch {
    return sampleDataForWidget(component.type);
  }
}

export function parseWidgetData(component?: PageComponentConfig, datasetPayload?: DatasetRuntimePayload | null) {
  if (!component) return sampleDataForWidget('metric_card');
  const dataSource = component.props?.dataSource as WidgetDataSourceConfig | undefined;
  if (dataSource?.type === 'dataset' && datasetPayload) {
    return datasetPayloadToWidgetData(component, datasetPayload);
  }
  return parseStaticWidgetData(component);
}

export function datasetIdForComponent(component?: PageComponentConfig) {
  const dataSource = component?.props?.dataSource as WidgetDataSourceConfig | undefined;
  if (dataSource?.type !== 'dataset' || dataSource.datasetId === null || dataSource.datasetId === undefined || dataSource.datasetId === '') {
    return '';
  }
  return String(dataSource.datasetId);
}

export function datasetPayloadKeyForComponent(component?: PageComponentConfig) {
  const datasetId = datasetIdForComponent(component);
  if (!datasetId) return '';
  return datasetPayloadKey(datasetId, datasetVariablesForComponent(component));
}

export function datasetVariablesForComponent(component?: PageComponentConfig) {
  const dataSource = component?.props?.dataSource as WidgetDataSourceConfig | undefined;
  const config = normalizeDatasetConfig(dataSource?.datasetConfig);
  return (config.filters || []).reduce<Record<string, unknown>>((variables, filter) => {
    const field = String(filter.field || '').trim();
    if (!field || filter.enabled === false || filter.value === null || filter.value === undefined || filter.value === '') {
      return variables;
    }
    variables[field] = filter.value;
    return variables;
  }, {});
}

export function datasetPayloadKey(datasetId: string, variables: Record<string, unknown>) {
  const sortedVariables = Object.keys(variables)
    .sort()
    .reduce<Record<string, unknown>>((result, key) => {
      result[key] = variables[key];
      return result;
    }, {});
  return `${datasetId}:${JSON.stringify(sortedVariables)}`;
}

function datasetPayloadToWidgetData(component: PageComponentConfig, payload: DatasetRuntimePayload) {
  const type = component.type;
  const config = normalizeDatasetConfig((component.props?.dataSource as WidgetDataSourceConfig | undefined)?.datasetConfig);
  const fields = (payload.fields || []).filter((field) => field.visible !== false);
  const rows = applyDatasetFilters(payload.items || [], config.filters || []);

  if (type === 'data_table') {
    return {
      columns: fields.map((field) => ({ key: field.field_key, title: field.label || field.field_key })),
      rows,
    };
  }

  if (type === 'metric_card') {
    const row = rows[0] || {};
    const valueField = preferredField(fields, ['value', 'metric', 'amount', 'count', 'total']) || firstNumberField(fields) || fields[0];
    const trendField = preferredField(fields, ['trend', 'rate', 'change', 'growth']);
    return {
      value: valueField ? formatDatasetValue(row[valueField.field_key], valueField) : '0',
      trend: trendField ? formatDatasetValue(row[trendField.field_key], trendField) : '',
      unit: valueField?.unit || '',
    };
  }

  if (type === 'scatter_chart') {
    const numberFields = fields.filter(isNumberField);
    const xField = numberFields[0];
    const yField = numberFields[1] || numberFields[0];
    return {
      categories: rows.map((row, index) => String(row[labelField(fields)?.field_key || ''] ?? `样本 ${index + 1}`)),
      series: [
        {
          name: payload.dataset?.name || '样本分布',
          data: rows.map((row) => [toNumber(row[xField?.field_key || '']), toNumber(row[yField?.field_key || ''])]),
        },
      ],
    };
  }

  if (type === 'gauge_chart') {
    const row = rows[0] || {};
    const valueField = preferredField(fields, ['value', 'progress', 'rate', 'percent']) || firstNumberField(fields);
    const maxField = preferredField(fields, ['max', 'target']);
    return {
      value: toNumber(row[valueField?.field_key || '']),
      max: Math.max(toNumber(row[maxField?.field_key || '']) || 100, 1),
      unit: valueField?.unit || '%',
      label: valueField?.label || payload.dataset?.name || '完成率',
    };
  }

  if (type === 'pie_chart') {
    const categoryField = fieldByKey(fields, config.xAxisField) || labelField(fields);
    const valueField = fieldByKey(fields, config.pieValueField) || fieldByKey(fields, config.yAxisFields?.[0] || '');
    const grouped = new Map<string, number>();
    rows.forEach((row, index) => {
      const category = String(row[categoryField?.field_key || ''] ?? `项目 ${index + 1}`);
      const value = config.pieValueMode === 'field' && valueField ? toNumber(row[valueField.field_key]) : 1;
      grouped.set(category, (grouped.get(category) || 0) + value);
    });
    const entries = Array.from(grouped.entries()).sort((left, right) => {
      const direction = config.pieSortDirection === 'desc' ? -1 : 1;
      if (config.pieSortBy === 'value') return (left[1] - right[1]) * direction;
      return left[0].localeCompare(right[0], 'zh-CN') * direction;
    });
    return {
      categories: entries.map(([category]) => category),
      series: [
        {
          name: valueField?.label || payload.dataset?.name || '占比',
          data: entries.map(([, value]) => value),
        },
      ],
    };
  }

  const categoryField = fieldByKey(fields, config.xAxisField) || labelField(fields);
  const valueFields = fields.filter(isNumberField);
  const configuredValueFields = (config.yAxisFields || []).map((field) => fieldByKey(fields, field)).filter(Boolean) as DatasetField[];
  const values = configuredValueFields.length ? configuredValueFields : valueFields.length ? valueFields : fields.slice(0, 1);
  return {
    categories: rows.map((row, index) => String(row[categoryField?.field_key || ''] ?? `项目 ${index + 1}`)),
    series: values.map((field) => ({
      name: field.label || field.field_key,
      data: rows.map((row) => toNumber(row[field.field_key])),
    })),
  };
}

function applyDatasetFilters(rows: Record<string, unknown>[], filters: WidgetDatasetFilterConfig[]) {
  const activeFilters = filters.filter((filter) => filter.enabled !== false && filter.field && filter.value !== null && filter.value !== undefined && filter.value !== '');
  if (!activeFilters.length) return rows;
  return rows.filter((row) =>
    activeFilters.every((filter) => {
      const actual = row[String(filter.field || '')];
      const expected = filter.value;
      const operator = filter.operator || 'eq';
      if (operator === 'contains') return String(actual ?? '').includes(String(expected ?? ''));
      if (operator === 'neq') return String(actual ?? '') !== String(expected ?? '');
      if (operator === 'gt') return toNumber(actual) > toNumber(expected);
      if (operator === 'gte') return toNumber(actual) >= toNumber(expected);
      if (operator === 'lt') return toNumber(actual) < toNumber(expected);
      if (operator === 'lte') return toNumber(actual) <= toNumber(expected);
      return String(actual ?? '') === String(expected ?? '');
    })
  );
}

function fieldByKey(fields: DatasetField[], key?: string) {
  if (!key) return undefined;
  return fields.find((field) => field.field_key === key);
}

function preferredField(fields: DatasetField[], semanticTypes: string[]) {
  const lowered = semanticTypes.map((item) => item.toLowerCase());
  return fields.find((field) => {
    const semanticType = String(field.semantic_type || '').toLowerCase();
    const key = String(field.field_key || '').toLowerCase();
    return lowered.includes(semanticType) || lowered.some((item) => key.includes(item));
  });
}

function labelField(fields: DatasetField[]) {
  return (
    preferredField(fields, ['category', 'dimension', 'label', 'name', 'date', 'time']) ||
    fields.find((field) => ['text', 'date', 'datetime'].includes(field.data_type)) ||
    fields[0]
  );
}

function firstNumberField(fields: DatasetField[]) {
  return fields.find(isNumberField);
}

function isNumberField(field: DatasetField) {
  return ['number', 'integer'].includes(field.data_type);
}

function formatDatasetValue(value: unknown, field: DatasetField) {
  if (value === null || value === undefined || value === '') return '0';
  if (!isNumberField(field)) return String(value);
  const numberValue = toNumber(value);
  const precision = field.precision;
  const formatted = typeof precision === 'number' && precision >= 0 ? numberValue.toFixed(precision) : String(numberValue);
  return `${formatted}${field.unit || ''}`;
}

function toNumber(value: unknown) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

export const widgetDefinitions: WidgetDefinition[] = [
  {
    type: 'metric_card',
    label: '指标卡片',
    defaultTitle: '核心指标',
    defaultProps: withDefaultDataSource('metric_card', { value: '128.6万', unit: '', trend: '+12.8%' }),
    defaultSize: { w: 6, h: 3 },
  },
  {
    type: 'line_chart',
    label: '折线图',
    defaultTitle: '趋势分析',
    defaultProps: withDefaultDataSource('line_chart', { description: '展示关键指标的时间趋势' }),
    defaultSize: { w: 12, h: 5 },
  },
  {
    type: 'bar_chart',
    label: '柱状图',
    defaultTitle: '分类对比',
    defaultProps: withDefaultDataSource('bar_chart', { description: '展示不同分类的数据对比' }),
    defaultSize: { w: 12, h: 5 },
  },
  {
    type: 'pie_chart',
    label: '饼图',
    defaultTitle: '占比分布',
    defaultProps: withDefaultDataSource('pie_chart', { description: '展示不同分类的占比结构' }),
    defaultSize: { w: 8, h: 5 },
  },
  {
    type: 'stacked_area_chart',
    label: '堆叠面积图',
    defaultTitle: '累计趋势',
    defaultProps: withDefaultDataSource('stacked_area_chart', { description: '展示多组指标的累计趋势' }),
    defaultSize: { w: 12, h: 5 },
  },
  {
    type: 'scatter_chart',
    label: '散点图',
    defaultTitle: '样本分布',
    defaultProps: withDefaultDataSource('scatter_chart', { description: '展示两个指标之间的分布关系' }),
    defaultSize: { w: 12, h: 5 },
  },
  {
    type: 'radar_chart',
    label: '雷达图',
    defaultTitle: '能力评估',
    defaultProps: withDefaultDataSource('radar_chart', { description: '展示多维指标的综合表现' }),
    defaultSize: { w: 8, h: 5 },
  },
  {
    type: 'gauge_chart',
    label: '进度仪表盘',
    defaultTitle: '目标进度',
    defaultProps: withDefaultDataSource('gauge_chart', { description: '展示单个指标的目标完成进度' }),
    defaultSize: { w: 8, h: 5 },
  },
  {
    type: 'data_table',
    label: '数据表格',
    defaultTitle: '明细数据',
    defaultProps: withDefaultDataSource('data_table', { rows: 5 }),
    defaultSize: { w: 12, h: 6 },
  },
  {
    type: 'text_block',
    label: '文本说明',
    defaultTitle: '说明',
    defaultProps: { content: '输入说明内容' },
    defaultSize: { w: 8, h: 3 },
  },
  {
    type: 'quick_link',
    label: '快捷入口',
    defaultTitle: '快捷入口',
    defaultProps: { text: '打开功能', href: '/' },
    defaultSize: { w: 6, h: 3 },
  },
];

export function widgetDefinition(type: string) {
  return widgetDefinitions.find((item) => item.type === type) || widgetDefinitions[0];
}

export function componentTitle(component?: PageComponentConfig) {
  if (!component) return '';
  return component.title || widgetDefinition(component.type).defaultTitle;
}
