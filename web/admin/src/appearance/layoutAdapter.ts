import type { AppearanceTokens, LayoutTokens } from './types';

export function createLayoutConfig(tokens: AppearanceTokens): LayoutTokens {
  return { ...tokens.layout };
}
