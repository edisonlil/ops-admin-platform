import { cloneDeep, merge } from 'lodash-es';
import type { AppearancePreset, AppearanceTokens, LayoutTokens, TokenOverrides } from './types';

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
