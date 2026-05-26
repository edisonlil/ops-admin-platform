<template>
  <div class="app-table-actions">
    <AppConfirmAction
      v-for="action in inlineActions"
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
    <n-popover
      v-if="overflowActions.length"
      v-model:show="moreVisible"
      trigger="click"
      to=".appearance-root"
      placement="bottom-end"
      :show-arrow="false"
      :content-style="{ padding: '0' }"
      content-class="app-table-actions-more-popover"
    >
      <template #trigger>
        <button class="app-table-actions__more" type="button" @click.stop>
          {{ moreLabel }}
        </button>
      </template>
      <div class="app-table-actions__menu" @click.stop>
        <AppConfirmAction
          v-for="action in overflowActions"
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
          variant="menu-item"
          :confirm-handler="() => handleOverflowConfirm(action)"
          @click="handleOverflowClick(action)"
          @cancel="action.onCancel"
        />
      </div>
    </n-popover>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref } from 'vue';
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

  const props = withDefaults(
    defineProps<{
      actions: AppTableAction[];
      inlineLimit?: number;
      moreLabel?: string;
    }>(),
    {
      inlineLimit: 0,
      moreLabel: '更多',
    }
  );

  const visibleActions = computed(() => props.actions.filter((action) => action.show !== false));
  const moreVisible = ref(false);

  const inlineActions = computed(() => {
    if (!props.inlineLimit || visibleActions.value.length <= props.inlineLimit) {
      return visibleActions.value;
    }
    return visibleActions.value.slice(0, Math.max(0, props.inlineLimit));
  });

  const overflowActions = computed(() => {
    if (!props.inlineLimit || visibleActions.value.length <= props.inlineLimit) {
      return [];
    }
    return visibleActions.value.slice(Math.max(0, props.inlineLimit));
  });

  function handleOverflowClick(action: AppTableAction) {
    action.onClick?.();
    if (!action.confirm) {
      moreVisible.value = false;
    }
  }

  async function handleOverflowConfirm(action: AppTableAction) {
    await action.onConfirm?.();
    moreVisible.value = false;
  }
</script>

<style lang="less" scoped>
  .app-table-actions {
    display: inline-flex;
    align-items: center;
    justify-content: flex-start;
    gap: var(--app-table-action-gap, 8px);
    min-width: 0;
  }

  .app-table-actions__more {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    height: var(--app-table-action-button-height, 30px);
    padding: 0 var(--app-table-action-button-padding-x, 12px);
    color: var(--app-table-action-default-text, #2563eb);
    font-size: 13px;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    background: var(--app-table-action-default-bg, #ffffff);
    border: 1px solid var(--app-table-action-default-border, #d9e1ec);
    border-radius: var(--app-table-action-button-radius, 6px);
    transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease;
  }

  .app-table-actions__menu {
    display: grid;
    grid-template-columns: 1fr;
    gap: 2px;
    min-width: 108px;
    padding: 6px;
    background: var(--app-table-action-confirm-bg, #ffffff);
    border: 1px solid var(--app-table-action-confirm-border, #d9e1ec);
    border-radius: var(--app-table-action-confirm-radius, 6px);
    box-shadow: var(--app-table-action-confirm-shadow, 0 8px 24px rgb(15 23 42 / 12%));
  }

  .app-table-actions__menu :deep(.app-confirm-action) {
    width: 100%;
  }
</style>

<style lang="less">
  .n-popover.app-table-actions-more-popover,
  .n-popover:has(.app-table-actions-more-popover) {
    padding: 0;
    overflow: visible;
    background: transparent;
    border: 0;
    box-shadow: none;
  }
</style>
