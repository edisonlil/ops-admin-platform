<template>
  <section class="app-table-toolbar" :class="{ 'app-table-toolbar--compact-search': compactSearch }">
    <div v-if="$slots.search" class="app-table-toolbar__search">
      <slot name="search"></slot>
    </div>

    <div class="app-table-toolbar__main">
      <div class="app-table-toolbar__title">
        <strong v-if="title">{{ title }}</strong>
        <span v-if="description">{{ description }}</span>
        <slot v-if="!title && !description" name="title"></slot>
      </div>
      <div class="app-table-toolbar__actions">
        <slot name="actions"></slot>
      </div>
    </div>

    <div v-if="selectedCount > 0 || $slots.batch" class="app-table-toolbar__batch">
      <span v-if="selectedCount > 0">已选择 {{ selectedCount }} 项</span>
      <slot name="batch"></slot>
    </div>
  </section>
</template>

<script lang="ts" setup>
  withDefaults(
    defineProps<{
      title?: string;
      description?: string;
      selectedCount?: number;
      compactSearch?: boolean;
    }>(),
    {
      title: '',
      description: '',
      selectedCount: 0,
      compactSearch: false,
    }
  );
</script>

<style lang="less" scoped>
  .app-table-toolbar {
    display: grid;
    gap: var(--app-table-search-row-gap, 10px);
    min-width: 0;
  }

  .app-table-toolbar__search {
    display: flex;
    flex-wrap: wrap;
    gap: var(--app-table-search-row-gap, 10px) var(--app-table-search-field-gap, 12px);
    align-items: center;
    min-width: 0;
    padding: var(--app-table-search-padding-y, 12px) var(--app-table-search-padding-x, 12px);
    background: var(--app-table-search-bg, var(--app-surface-bg));
    border: 1px solid var(--app-table-search-border-color, var(--app-border-color));
    border-radius: var(--app-table-search-radius, var(--app-card-radius));

    :deep(.n-form-item) {
      min-width: min(100%, var(--app-table-search-input-width, 220px));
      margin-bottom: 0;
    }

    :deep(.n-form-item-label) {
      width: var(--app-table-search-label-width, 88px);
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

  .app-table-toolbar--compact-search {
    .app-table-toolbar__search {
      justify-self: start;
      width: auto;
      max-width: 100%;
    }
  }

  .app-table-toolbar__main,
  .app-table-toolbar__batch {
    display: flex;
    align-items: center;
    min-width: 0;
    border: 1px solid;
  }

  .app-table-toolbar__main {
    justify-content: space-between;
    gap: var(--app-table-toolbar-gap, 12px);
    min-height: var(--app-table-toolbar-min-height, 44px);
    padding: var(--app-table-toolbar-padding-y, 10px) var(--app-table-toolbar-padding-x, 12px);
    background: var(--app-table-toolbar-bg, var(--app-surface-bg));
    border-color: var(--app-table-toolbar-border-color, var(--app-border-color));
    border-radius: var(--app-table-toolbar-radius, var(--app-card-radius));
  }

  .app-table-toolbar__title {
    display: grid;
    gap: 2px;
    min-width: 0;

    strong {
      overflow: hidden;
      color: var(--app-table-toolbar-title-color, var(--app-text-color));
      font-size: calc(var(--app-font-size-base, 14px) + 2px);
      font-weight: 650;
      line-height: 22px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      overflow: hidden;
      color: var(--app-icon-color);
      font-size: var(--app-font-size-sm, 13px);
      line-height: 18px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .app-table-toolbar__actions {
    display: inline-flex;
    flex-wrap: wrap;
    gap: var(--app-table-search-action-gap, 8px);
    justify-content: flex-end;
    min-width: 0;
  }

  .app-table-toolbar__batch {
    justify-content: flex-start;
    gap: var(--app-table-batch-action-gap, 8px);
    min-height: var(--app-table-batch-action-min-height, 40px);
    padding: 0 var(--app-table-batch-action-padding-x, 12px);
    color: var(--app-table-batch-action-text-color, var(--app-text-color));
    background: var(--app-table-batch-action-bg, var(--app-primary-soft-bg));
    border-color: var(--app-table-batch-action-border-color, var(--app-border-color));
    border-radius: var(--app-table-batch-action-radius, var(--app-card-radius));

    span {
      font-weight: 650;
    }
  }
</style>
