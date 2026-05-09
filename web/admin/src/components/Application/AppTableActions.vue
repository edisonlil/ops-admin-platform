<template>
  <div class="app-table-actions">
    <AppConfirmAction
      v-for="action in visibleActions"
      :key="action.key || action.label"
      :label="action.label"
      :tone="action.tone"
      :disabled="action.disabled"
      :confirm="action.confirm"
      :confirm-title="action.confirmTitle"
      :confirm-content="action.confirmContent"
      :positive-text="action.positiveText"
      :negative-text="action.negativeText"
      :loading="action.loading"
      :confirm-handler="action.onConfirm"
      @click="action.onClick"
      @cancel="action.onCancel"
    />
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import AppConfirmAction from './AppConfirmAction.vue';

  export interface AppTableAction {
    key?: string;
    label: string;
    tone?: 'default' | 'primary' | 'danger';
    disabled?: boolean;
    show?: boolean;
    confirm?: boolean;
    confirmTitle?: string;
    confirmContent?: string;
    positiveText?: string;
    negativeText?: string;
    loading?: boolean;
    onClick?: () => void;
    onConfirm?: () => void | Promise<void>;
    onCancel?: () => void;
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
  }
</style>
