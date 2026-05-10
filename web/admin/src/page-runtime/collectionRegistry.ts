import type { CollectionViewDefinition, CollectionViewType } from './types';

const collectionViewDefinitions: CollectionViewDefinition[] = [
  { type: 'table', label: '表格列表', description: '高密度数据扫描、排序、固定列和批量操作。' },
  { type: 'tabbed-list', label: '多标签列表', description: '在同一页面内管理多个同级列表集合。' },
  { type: 'basic-list', label: '基础列表', description: '按行展示对象摘要和行内操作。' },
  { type: 'card-list', label: '卡片列表', description: '以卡片网格展示同构对象。' },
  { type: 'product-list', label: '商品列表', description: '展示商品图、价格、库存、状态和商品操作。' },
  { type: 'split-list', label: '左侧双栏列表', description: '左侧对象列表，右侧详情预览或辅助集合。' },
  { type: 'kanban', label: '看板视图', description: '按状态或分组列组织任务、审批或流程对象。' },
  { type: 'calendar', label: '日历视图', description: '按月、周、日组织排期、任务和事件。' },
  { type: 'tree', label: '树列表', description: '层级数据的浏览、选择和管理。' },
  { type: 'timeline', label: '时间线', description: '按时间顺序呈现事件、日志和活动。' },
  { type: 'gallery', label: '图库视图', description: '以媒体缩略图或附件网格浏览资源。' },
  { type: 'map', label: '地图视图', description: '以空间位置呈现资源、工单或设备。' },
];

export function getCollectionViewDefinition(type: CollectionViewType): CollectionViewDefinition {
  return (
    collectionViewDefinitions.find((definition) => definition.type === type) || {
      type,
      label: type,
      description: '已注册的集合视图。',
    }
  );
}

export function getCollectionViewDefinitions() {
  return collectionViewDefinitions;
}
