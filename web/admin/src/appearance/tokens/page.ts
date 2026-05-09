import type { PageTokens } from '../types';

export const defaultPageTokens: PageTokens = {
  density: 'comfortable',
  variant: 'default',
  header: {
    minHeight: 72,
    paddingBlock: 14,
    paddingInline: 0,
    titleSize: 20,
    descriptionSize: 13,
    actionGap: 8,
  },
  section: {
    gap: 12,
    blockMargin: 12,
    dividerStrength: 'subtle',
  },
  content: {
    maxWidth: 'none',
    paddingBlock: 0,
  },
  filter: {
    minHeight: 44,
    padding: 12,
    fieldGap: 12,
    rowGap: 10,
    labelWidth: 88,
    collapsedRows: 1,
  },
  toolbar: {
    minHeight: 44,
    gap: 12,
    paddingInline: 12,
    leftGap: 8,
    rightGap: 8,
  },
  collection: {
    gap: 12,
    borderStrategy: 'container',
  },
  table: {
    rowHeight: 44,
    headerHeight: 44,
    cellPaddingInline: 12,
  },
  card: {
    padding: 16,
    gap: 12,
    minItemWidth: 260,
  },
  detail: {
    sectionGap: 16,
    labelWidth: 120,
    formItemGap: 12,
    footerHeight: 56,
  },
};
