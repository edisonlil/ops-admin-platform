import type { AppearancePreset } from '../types';
import { compactEnterprisePreset } from './compact';
import { defaultPreset } from './default';
import { primevueLikePreset } from './primevueLike';

export const appearancePresets: AppearancePreset[] = [
  defaultPreset,
  primevueLikePreset,
  compactEnterprisePreset,
];

export function getAppearancePreset(id?: string): AppearancePreset {
  return appearancePresets.find((preset) => preset.id === id) || defaultPreset;
}
