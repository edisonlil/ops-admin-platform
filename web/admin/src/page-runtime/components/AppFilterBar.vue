<template>
  <section
    v-if="$slots.default"
    class="app-filter-bar"
    :class="[fieldSizeClass, layoutClass]"
  >
    <div class="app-filter-bar__fields">
      <slot></slot>
    </div>
    <div v-if="showActions" class="app-filter-bar__actions">
      <n-button
        v-if="showSubmit"
        :disabled="submitDisabled"
        :loading="loading"
        @click="$emit('submit')"
      >
        {{ submitLabel }}
      </n-button>
      <n-button
        v-if="showReset"
        secondary
        :disabled="resetDisabled"
        @click="$emit('reset')"
      >
        {{ resetLabel }}
      </n-button>
    </div>
  </section>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import type { FilterBarFieldSize } from '../types';

  const props = withDefaults(
    defineProps<{
      fieldSize?: FilterBarFieldSize;
      layout?: 'default' | 'compact-grid';
      showSubmit?: boolean;
      showReset?: boolean;
      submitLabel?: string;
      resetLabel?: string;
      submitDisabled?: boolean;
      resetDisabled?: boolean;
      loading?: boolean;
    }>(),
    {
      fieldSize: 'default',
      layout: 'default',
      showSubmit: false,
      showReset: false,
      submitLabel: '查询',
      resetLabel: '重置',
      submitDisabled: false,
      resetDisabled: false,
      loading: false,
    }
  );

  defineEmits<{
    submit: [];
    reset: [];
  }>();

  const showActions = computed(() => props.showSubmit || props.showReset);
  const fieldSizeClass = computed(() => `app-filter-bar--${props.fieldSize}`);
  const layoutClass = computed(() => `app-filter-bar--layout-${props.layout}`);
</script>

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

    &--small {
      --app-filter-bar-field-width: var(--app-table-search-input-width-small, 160px);
    }

    &--default {
      --app-filter-bar-field-width: var(--app-table-search-input-width, 220px);
    }

    &--large {
      --app-filter-bar-field-width: var(--app-table-search-input-width-large, 300px);
    }
  }

  .app-filter-bar__fields,
  .app-filter-bar__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    min-width: 0;
    gap: var(--app-page-filter-row-gap) var(--app-page-filter-field-gap);
  }

  .app-filter-bar__fields {
    flex: 0 1 auto;

    :deep(.n-form-item) {
      min-width: min(100%, var(--app-filter-bar-field-width));
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
      flex: 0 1 var(--app-filter-bar-field-width);
      width: var(--app-filter-bar-field-width);
      min-width: min(100%, 180px);
      max-width: 100%;
    }
  }

  .app-filter-bar__actions {
    flex: 0 0 auto;
  }

  .app-filter-bar--layout-compact-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;

    .app-filter-bar__fields {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 180px), 1fr));
      align-items: center;
      width: 100%;

      :deep(> .n-input),
      :deep(> .n-input-number),
      :deep(> .n-select),
      :deep(> .n-date-picker),
      :deep(> .n-time-picker) {
        width: 100%;
        min-width: 0;
      }
    }

    .app-filter-bar__actions {
      flex-wrap: nowrap;
      justify-content: flex-end;
      padding-left: 4px;
    }
  }

  @media (max-width: 640px) {
    .app-filter-bar__fields,
    .app-filter-bar__actions {
      flex: 1 1 100%;
    }

    .app-filter-bar__fields {
      :deep(> .n-input),
      :deep(> .n-input-number),
      :deep(> .n-select),
      :deep(> .n-date-picker),
      :deep(> .n-time-picker) {
        flex-basis: 100%;
        width: 100%;
      }
    }

    .app-filter-bar__actions {
      justify-content: flex-start;
    }

    .app-filter-bar--layout-compact-grid {
      grid-template-columns: minmax(0, 1fr);

      .app-filter-bar__actions {
        padding-left: 0;
      }
    }
  }
</style>
