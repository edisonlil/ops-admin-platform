import type { PageComponentConfig } from '@/api/pageDesigner';

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

export interface WidgetDataSourceConfig {
  type: WidgetDataSourceType;
  staticJson?: string;
  datasetId?: string;
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
          }
        : defaultDataSourceForWidget(type),
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
    label: '折叠面积图',
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
