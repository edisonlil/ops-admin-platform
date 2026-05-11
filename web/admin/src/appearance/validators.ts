import type { AppearanceTokens, TokenValidationError } from './types';

const HEX_PATTERN = /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i;
const CSS_SIZE_PATTERN = /^-?\d+(\.\d+)?(px|rem|em|%)$/;
const CSS_NUMBER_PATTERN = /^-?\d+(\.\d+)?$/;
const COLOR_KEYS = /(color|bg|border|text)$/i;
const SIZE_KEYS = /(height|radius|padding|margin|width|size)$/i;

function isColorPath(path: string) {
  return COLOR_KEYS.test(path) || /(Color|Bg|Text)$/.test(path);
}

function isSizePath(path: string) {
  return SIZE_KEYS.test(path) && !/color/i.test(path);
}

function isCssSizeShorthand(value: string) {
  const parts = value.trim().split(/\s+/);
  return parts.length >= 1 && parts.length <= 4 && parts.every((part) => CSS_SIZE_PATTERN.test(part));
}

function visit(value: unknown, path: string, errors: TokenValidationError[]) {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    Object.entries(value as Record<string, unknown>).forEach(([key, item]) => {
      visit(item, path ? `${path}.${key}` : key, errors);
    });
    return;
  }

  if (typeof value === 'string' && value.trim() === '') {
    errors.push({
      path,
      code: 'TOKEN_EMPTY',
      message: `${path} 不能为空。`,
    });
    return;
  }

  if (typeof value === 'string' && isColorPath(path) && !HEX_PATTERN.test(value)) {
    errors.push({
      path,
      code: 'TOKEN_INVALID_COLOR',
      message: `${path} 必须是十六进制颜色值。`,
    });
  }

  if (
    typeof value === 'string' &&
    isSizePath(path) &&
    value !== 'none' &&
    value !== 'auto' &&
    !CSS_NUMBER_PATTERN.test(value) &&
    !isCssSizeShorthand(value)
  ) {
    errors.push({
      path,
      code: 'TOKEN_INVALID_SIZE',
      message: `${path} 必须是 px、rem、em 或百分比单位。`,
    });
  }
}

export function validateAppearanceTokens(tokens: AppearanceTokens): TokenValidationError[] {
  const errors: TokenValidationError[] = [];
  visit(tokens, '', errors);

  const { layout } = tokens;
  if (!['compact', 'default', 'comfortable'].includes(layout.density)) {
    errors.push({
      path: 'layout.density',
      code: 'TOKEN_INVALID_ENUM',
      message: 'layout.density 必须是 compact、default 或 comfortable。',
    });
  }

  if (!['bordered', 'shadow', 'flat'].includes(layout.cardStyle)) {
    errors.push({
      path: 'layout.cardStyle',
      code: 'TOKEN_INVALID_ENUM',
      message: 'layout.cardStyle 必须是 bordered、shadow 或 flat。',
    });
  }

  const { page } = tokens;
  if (!['compact', 'comfortable', 'spacious'].includes(page.density)) {
    errors.push({
      path: 'page.density',
      code: 'TOKEN_INVALID_ENUM',
      message: 'page.density must be compact, comfortable, or spacious.',
    });
  }

  if (!['default', 'enterprise', 'saas', 'dense-data', 'minimal'].includes(page.variant)) {
    errors.push({
      path: 'page.variant',
      code: 'TOKEN_INVALID_ENUM',
      message: 'page.variant must be default, enterprise, saas, dense-data, or minimal.',
    });
  }

  [
    ['layout.headerHeight', layout.headerHeight],
    ['layout.tabsHeight', layout.tabsHeight],
    ['layout.menuWidth', layout.menuWidth],
    ['layout.collapsedMenuWidth', layout.collapsedMenuWidth],
    ['layout.contentPadding', layout.contentPadding],
    ['page.header.minHeight', page.header.minHeight],
    ['page.header.paddingBlock', page.header.paddingBlock],
    ['page.header.paddingInline', page.header.paddingInline],
    ['page.section.gap', page.section.gap],
    ['page.filter.padding', page.filter.padding],
    ['page.toolbar.minHeight', page.toolbar.minHeight],
    ['page.table.rowHeight', page.table.rowHeight],
    ['page.card.padding', page.card.padding],
  ].forEach(([path, value]) => {
    if (typeof value !== 'number' || value < 0) {
      errors.push({
        path: path as string,
        code: 'TOKEN_INVALID_NUMBER',
        message: `${path} 必须是非负数。`,
      });
    }
  });

  return errors;
}
