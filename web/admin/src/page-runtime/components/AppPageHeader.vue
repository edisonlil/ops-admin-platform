<template>
  <header class="app-page-header">
    <div class="app-page-header__main">
      <div v-if="$slots.breadcrumb" class="app-page-header__breadcrumb">
        <slot name="breadcrumb"></slot>
      </div>
      <div class="app-page-header__title-row">
        <div class="app-page-header__copy">
          <h1>{{ title }}</h1>
          <p v-if="description">{{ description }}</p>
        </div>
        <div v-if="$slots.actions" class="app-page-header__actions">
          <slot name="actions"></slot>
        </div>
      </div>
    </div>
  </header>
</template>

<script lang="ts" setup>
  defineProps<{
    title: string;
    description?: string;
  }>();
</script>

<style lang="less" scoped>
  .app-page-header {
    display: flex;
    align-items: center;
    min-height: var(--app-page-header-min-height);
    padding: var(--app-page-header-padding-block) var(--app-page-header-padding-inline);
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color) 72%, transparent);
  }

  .app-page-header__main {
    display: grid;
    gap: 8px;
    width: 100%;
    min-width: 0;
  }

  .app-page-header__breadcrumb {
    min-width: 0;
  }

  .app-page-header__title-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--app-page-header-action-gap);
    min-width: 0;
  }

  .app-page-header__copy {
    display: grid;
    gap: 4px;
    min-width: 0;

    h1 {
      margin: 0;
      overflow-wrap: anywhere;
      color: var(--app-text-color);
      font-size: var(--app-page-header-title-size);
      font-weight: 650;
      line-height: 1.25;
      letter-spacing: 0;
    }

    p {
      max-width: 760px;
      margin: 0;
      color: var(--app-icon-color);
      font-size: var(--app-page-header-description-size);
      line-height: 1.45;
    }
  }

  .app-page-header__actions {
    display: inline-flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: var(--app-page-header-action-gap);
    min-width: 0;
  }

  @media (max-width: 720px) {
    .app-page-header__title-row {
      display: grid;
    }

    .app-page-header__actions {
      justify-content: flex-start;
    }
  }
</style>
