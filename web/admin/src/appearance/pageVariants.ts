import type { PageTokens, PageVariant } from './types';

export const pageVariantOverrides: Record<PageVariant, Partial<PageTokens>> = {
  default: {},
  enterprise: {
    variant: 'enterprise',
    header: {
      minHeight: 76,
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
    collection: {
      gap: 12,
      borderStrategy: 'container',
    },
  },
  saas: {
    variant: 'saas',
    header: {
      minHeight: 80,
      paddingBlock: 16,
      paddingInline: 0,
      titleSize: 21,
      descriptionSize: 13,
      actionGap: 10,
    },
    section: {
      gap: 14,
      blockMargin: 14,
      dividerStrength: 'none',
    },
    collection: {
      gap: 14,
      borderStrategy: 'item',
    },
  },
  'dense-data': {
    variant: 'dense-data',
    density: 'compact',
    header: {
      minHeight: 60,
      paddingBlock: 10,
      paddingInline: 0,
      titleSize: 18,
      descriptionSize: 12,
      actionGap: 6,
    },
    section: {
      gap: 8,
      blockMargin: 8,
      dividerStrength: 'subtle',
    },
    collection: {
      gap: 8,
      borderStrategy: 'container',
    },
  },
  minimal: {
    variant: 'minimal',
    header: {
      minHeight: 60,
      paddingBlock: 10,
      paddingInline: 0,
      titleSize: 18,
      descriptionSize: 12,
      actionGap: 8,
    },
    section: {
      gap: 10,
      blockMargin: 10,
      dividerStrength: 'none',
    },
    collection: {
      gap: 10,
      borderStrategy: 'none',
    },
  },
};
