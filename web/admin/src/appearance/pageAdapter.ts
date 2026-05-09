import { merge } from 'lodash-es';
import { pageVariantOverrides } from './pageVariants';
import type { AppearanceTokens, PageDensity, PageTokens, PageVariant } from './types';

const densityScale: Record<PageDensity, Partial<PageTokens>> = {
  compact: {
    density: 'compact',
    section: { gap: 8, blockMargin: 8, dividerStrength: 'subtle' },
    filter: { minHeight: 36, padding: 8, fieldGap: 8, rowGap: 8, labelWidth: 76, collapsedRows: 1 },
    toolbar: { minHeight: 36, gap: 8, paddingInline: 10, leftGap: 6, rightGap: 6 },
    collection: { gap: 8, borderStrategy: 'container' },
    table: { rowHeight: 36, headerHeight: 36, cellPaddingInline: 10 },
    card: { padding: 12, gap: 8, minItemWidth: 240 },
    detail: { sectionGap: 12, labelWidth: 108, formItemGap: 10, footerHeight: 48 },
  },
  comfortable: {
    density: 'comfortable',
    section: { gap: 12, blockMargin: 12, dividerStrength: 'subtle' },
    filter: { minHeight: 44, padding: 12, fieldGap: 12, rowGap: 10, labelWidth: 88, collapsedRows: 1 },
    toolbar: { minHeight: 44, gap: 12, paddingInline: 12, leftGap: 8, rightGap: 8 },
    collection: { gap: 12, borderStrategy: 'container' },
    table: { rowHeight: 44, headerHeight: 44, cellPaddingInline: 12 },
    card: { padding: 16, gap: 12, minItemWidth: 260 },
    detail: { sectionGap: 16, labelWidth: 120, formItemGap: 12, footerHeight: 56 },
  },
  spacious: {
    density: 'spacious',
    section: { gap: 18, blockMargin: 18, dividerStrength: 'none' },
    filter: { minHeight: 52, padding: 16, fieldGap: 14, rowGap: 12, labelWidth: 104, collapsedRows: 1 },
    toolbar: { minHeight: 52, gap: 14, paddingInline: 16, leftGap: 10, rightGap: 10 },
    collection: { gap: 18, borderStrategy: 'item' },
    table: { rowHeight: 52, headerHeight: 48, cellPaddingInline: 14 },
    card: { padding: 20, gap: 16, minItemWidth: 280 },
    detail: { sectionGap: 20, labelWidth: 132, formItemGap: 14, footerHeight: 64 },
  },
};

export interface PageRuntimeConfig extends PageTokens {
  cssClass: string;
}

export function createPageRuntimeConfig(
  tokens: AppearanceTokens,
  options: { density?: PageDensity; variant?: PageVariant } = {}
): PageRuntimeConfig {
  const basePage = tokens.page;
  const variant = options.variant || basePage.variant || 'default';
  const density = options.density || basePage.density || 'comfortable';
  const page = merge({}, basePage, pageVariantOverrides[variant], densityScale[density], {
    variant,
    density,
  }) as PageTokens;

  return {
    ...page,
    cssClass: `app-page-runtime--${page.variant} app-page-runtime--${page.density}`,
  };
}
