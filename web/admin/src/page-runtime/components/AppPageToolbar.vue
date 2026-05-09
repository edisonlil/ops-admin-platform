<template>
  <section class="app-page-toolbar">
    <div class="app-page-toolbar__left">
      <span v-if="selectedCount > 0" class="app-page-toolbar__selection">已选择 {{ selectedCount }} 项</span>
      <slot name="left"></slot>
    </div>
    <div class="app-page-toolbar__right">
      <slot name="right"></slot>
    </div>
  </section>
</template>

<script lang="ts" setup>
  withDefaults(
    defineProps<{
      selectedCount?: number;
    }>(),
    {
      selectedCount: 0,
    }
  );
</script>

<style lang="less" scoped>
  .app-page-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--app-page-toolbar-gap);
    min-height: var(--app-page-toolbar-min-height);
    min-width: 0;
    padding: 6px var(--app-page-toolbar-padding-inline);
    background: var(--app-table-toolbar-bg, var(--app-surface-bg));
    border: 1px solid var(--app-table-toolbar-border-color, var(--app-border-color));
    border-radius: var(--app-table-toolbar-radius, var(--app-card-radius));
  }

  .app-page-toolbar__left,
  .app-page-toolbar__right {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    min-width: 0;
  }

  .app-page-toolbar__left {
    gap: var(--app-page-toolbar-left-gap);
  }

  .app-page-toolbar__right {
    justify-content: flex-end;
    gap: var(--app-page-toolbar-right-gap);
  }

  .app-page-toolbar__selection {
    color: var(--app-text-color);
    font-size: var(--app-font-size-sm);
    font-weight: 650;
    line-height: 1;
  }

  @media (max-width: 720px) {
    .app-page-toolbar {
      align-items: stretch;
      flex-direction: column;
    }

    .app-page-toolbar__right {
      justify-content: flex-start;
    }
  }
</style>
