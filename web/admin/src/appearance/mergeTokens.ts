import { cloneDeep, merge } from 'lodash-es';
import type { AppearancePreset, AppearanceTokens, LayoutTokens, TokenOverrides } from './types';
import { defaultPageTokens } from './tokens/page';

export function mergeAppearanceTokens(
  preset: AppearancePreset,
  tokenOverrides: TokenOverrides = {},
  layoutOverrides: Partial<LayoutTokens> = {},
  isDark = false
): AppearanceTokens {
  const tokens = merge(cloneDeep(preset.tokens), {
    primitive: cloneDeep(tokenOverrides.primitive || {}),
    semantic: cloneDeep(tokenOverrides.semantic || {}),
    component: cloneDeep(tokenOverrides.component || {}),
    layout: cloneDeep(layoutOverrides),
    page: merge(cloneDeep(defaultPageTokens), cloneDeep(preset.tokens.page || {}), cloneDeep(tokenOverrides.page || {})),
  }) as AppearanceTokens;

  if (isDark) {
    tokens.semantic = merge(
      cloneDeep(tokens.semantic),
      cloneDeep(preset.darkSemantic || {}),
      cloneDeep(tokenOverrides.darkSemantic || {})
    );
  }

  return tokens;
}
