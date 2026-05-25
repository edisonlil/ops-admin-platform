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

export const widgetDefinitions: WidgetDefinition[] = [
  {
    type: 'metric_card',
    label: '指标卡片',
    defaultTitle: '核心指标',
    defaultProps: { value: '128.6万', unit: '', trend: '+12.8%' },
    defaultSize: { w: 6, h: 3 },
  },
  {
    type: 'line_chart',
    label: '折线图',
    defaultTitle: '趋势分析',
    defaultProps: { description: '展示关键指标的时间趋势' },
    defaultSize: { w: 12, h: 5 },
  },
  {
    type: 'bar_chart',
    label: '柱状图',
    defaultTitle: '分类对比',
    defaultProps: { description: '展示不同分类的数据对比' },
    defaultSize: { w: 12, h: 5 },
  },
  {
    type: 'data_table',
    label: '数据表格',
    defaultTitle: '明细数据',
    defaultProps: { rows: 5 },
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
