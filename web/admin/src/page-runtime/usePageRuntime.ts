import { computed } from 'vue';
import { createPageRuntimeConfig } from '@/appearance/pageAdapter';
import { useAppearanceStore } from '@/store/modules/appearance';
import type { PageDensity, PageVariant } from '@/appearance/types';

export function usePageRuntime(options: { density?: PageDensity; variant?: PageVariant } = {}) {
  const appearanceStore = useAppearanceStore();
  const pageRuntime = computed(() =>
    createPageRuntimeConfig(appearanceStore.resolvedTokens, {
      density: options.density,
      variant: options.variant,
    })
  );

  return {
    pageRuntime,
  };
}
