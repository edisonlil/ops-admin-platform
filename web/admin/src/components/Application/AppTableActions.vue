<template>
  <div class="app-table-actions">
    <n-button
      v-for="action in visibleActions"
      :key="action.key || action.label"
      class="app-table-actions__button"
      :type="action.type"
      :disabled="action.disabled"
      :secondary="action.secondary ?? action.type !== 'primary'"
      :ghost="action.ghost"
      size="small"
      @click="action.onClick"
    >
      {{ action.label }}
    </n-button>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import type { ButtonProps } from 'naive-ui';

  export interface AppTableAction {
    key?: string;
    label: string;
    type?: ButtonProps['type'];
    disabled?: boolean;
    secondary?: boolean;
    ghost?: boolean;
    show?: boolean;
    onClick?: () => void;
  }

  const props = defineProps<{
    actions: AppTableAction[];
  }>();

  const visibleActions = computed(() => props.actions.filter((action) => action.show !== false));
</script>

<style lang="less" scoped>
  .app-table-actions {
    display: inline-flex;
    align-items: center;
    justify-content: flex-start;
    gap: var(--app-table-action-gap);
    min-width: 0;

    &__button {
      height: var(--app-table-action-button-height);
      padding-right: var(--app-table-action-button-padding-x);
      padding-left: var(--app-table-action-button-padding-x);
      border-radius: var(--app-table-action-button-radius);
    }
  }
</style>
