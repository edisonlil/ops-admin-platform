<template>
  <section v-if="$slots.default" class="app-filter-bar">
    <slot></slot>
  </section>
</template>

<style lang="less" scoped>
  .app-filter-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--app-page-filter-row-gap) var(--app-page-filter-field-gap);
    min-height: var(--app-page-filter-min-height);
    min-width: 0;
    padding: var(--app-page-filter-padding);
    background: var(--app-table-search-bg, var(--app-surface-bg));
    border: 1px solid var(--app-table-search-border-color, var(--app-border-color));
    border-radius: var(--app-table-search-radius, var(--app-card-radius));

    :deep(.n-form-item) {
      min-width: min(100%, var(--app-table-search-input-width, 220px));
      margin-bottom: 0;
    }

    :deep(.n-form-item-label) {
      width: var(--app-page-filter-label-width);
    }

    :deep(> .n-input),
    :deep(> .n-input-number),
    :deep(> .n-select),
    :deep(> .n-date-picker),
    :deep(> .n-time-picker) {
      flex: 0 1 var(--app-table-search-input-width, 220px);
      width: var(--app-table-search-input-width, 220px);
      min-width: min(100%, 180px);
      max-width: 100%;
    }

    :deep(> .n-button) {
      flex: 0 0 auto;
    }
  }
</style>
