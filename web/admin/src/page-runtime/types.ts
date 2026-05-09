import type { Component } from 'vue';
import type { DataTableColumns, PaginationProps, SelectOption } from 'naive-ui';
import type { PageDensity, PageVariant } from '@/appearance/types';

export type CollectionViewType =
  | 'table'
  | 'basic-list'
  | 'card-list'
  | 'product-list'
  | 'split-list'
  | 'kanban'
  | 'calendar'
  | 'tree'
  | 'timeline'
  | 'gallery'
  | 'map';

export type DetailPageKind =
  | 'basic-detail'
  | 'profile-detail'
  | 'form-detail'
  | 'product-detail'
  | 'approval-detail'
  | 'workspace-detail'
  | 'master-detail';

export interface PageRuntimeContext {
  pageId: string;
  density: PageDensity;
  variant: PageVariant;
}

export interface PageAction {
  key: string;
  label: string;
  icon?: string | Component;
  type?: 'primary' | 'default' | 'error' | 'warning' | 'info';
  disabled?: boolean;
  loading?: boolean;
  onClick?: (ctx: PageRuntimeContext) => void | Promise<void>;
}

export interface FilterField<T = Record<string, unknown>> {
  key: keyof T | string;
  type: 'keyword' | 'input' | 'select' | 'dateRange' | 'treeSelect' | 'custom';
  label?: string;
  placeholder?: string;
  options?: SelectOption[] | (() => SelectOption[]);
}

export interface CollectionViewSchema<Row = Record<string, unknown>> {
  type: CollectionViewType;
  columns?: DataTableColumns<Row>;
  rowKey?: string | ((row: Row) => string | number);
  scrollX?: number;
  itemKey?: string | ((row: Row) => string | number);
  cardMinWidth?: string;
  groupBy?: string | ((row: Row) => string);
  modes?: string[];
  mode?: string;
  dateField?: string;
  endDateField?: string;
  tableProps?: Record<string, unknown>;
}

export interface ListToolbarSchema {
  primaryAction?: PageAction;
  batchActions?: PageAction[];
  rightTools?: Array<'density' | 'columns' | 'refresh' | 'viewSwitch' | 'today' | 'calendarMode' | 'prevNext'>;
}

export interface ListPageSchema<Row = Record<string, unknown>, Query = Record<string, unknown>> {
  id: string;
  title: string;
  description?: string;
  variant?: PageVariant;
  density?: PageDensity;
  filters?: FilterField<Query>[];
  toolbar?: ListToolbarSchema;
  view: CollectionViewSchema<Row>;
  pagination?: false | PaginationProps;
}

export interface DetailPageSchema<T = Record<string, unknown>> {
  id: string;
  title: string;
  description?: string;
  kind: DetailPageKind;
  variant?: PageVariant;
  density?: PageDensity;
  actions?: PageAction[];
  data?: T;
}

export interface CollectionViewDefinition {
  type: CollectionViewType;
  label: string;
  description: string;
}
