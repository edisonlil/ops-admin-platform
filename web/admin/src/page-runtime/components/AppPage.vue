<template>
  <section class="app-page" :class="pageRuntime.cssClass">
    <slot></slot>
  </section>
</template>

<script lang="ts" setup>
  import { usePageRuntime } from '../usePageRuntime';
  import type { PageDensity, PageVariant } from '@/appearance/types';

  const props = defineProps<{
    density?: PageDensity;
    variant?: PageVariant;
  }>();

  const { pageRuntime } = usePageRuntime({
    density: props.density,
    variant: props.variant,
  });
</script>

<style lang="less" scoped>
  .app-page {
    display: grid;
    gap: var(--app-page-section-gap);
    box-sizing: border-box;
    width: 100%;
    max-width: var(--app-page-content-max-width);
    min-width: 0;
    padding-block: var(--app-page-content-padding-block);
    margin-inline: auto;
  }
</style>
