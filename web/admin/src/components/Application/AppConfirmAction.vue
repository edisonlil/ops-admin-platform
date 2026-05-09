<template>
  <n-popconfirm
    v-if="confirm"
    :show-icon="false"
    :positive-text="positiveText"
    :negative-text="negativeText"
    :disabled="disabled"
    trigger="click"
    to=".appearance-root"
    placement="top-end"
    :width="confirmPopoverWidth"
    content-class="app-confirm-action-popover"
    @positive-click="handleConfirm"
    @negative-click="emit('cancel')"
  >
    <template #trigger>
      <button
        class="app-confirm-action"
        :class="[`app-confirm-action--${resolvedTone}`, { 'is-disabled': disabled }]"
        type="button"
        :disabled="disabled"
        @click.stop
      >
        {{ label }}
      </button>
    </template>
    <div class="app-confirm-action__content">
      <strong v-if="confirmTitle">{{ confirmTitle }}</strong>
      <span>{{ confirmContent || '确认执行该操作吗？' }}</span>
    </div>
  </n-popconfirm>
  <button
    v-else
    class="app-confirm-action"
    :class="[`app-confirm-action--${resolvedTone}`, { 'is-disabled': disabled }]"
    type="button"
    :disabled="disabled || loading"
    @click="emit('click')"
  >
    {{ label }}
  </button>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';

  type ActionTone = 'default' | 'primary' | 'danger';

  const props = withDefaults(
    defineProps<{
      label: string;
      tone?: ActionTone | string;
      disabled?: boolean;
      confirm?: boolean;
      confirmTitle?: string;
      confirmContent?: string;
      positiveText?: string;
      negativeText?: string;
      loading?: boolean;
      confirmHandler?: () => void | Promise<void>;
    }>(),
    {
      tone: 'default',
      positiveText: '确认',
      negativeText: '取消',
    }
  );

  const emit = defineEmits<{
    click: [];
    cancel: [];
  }>();

  const resolvedTone = computed<ActionTone>(() => {
    if (['default', 'primary', 'danger'].includes(props.tone)) {
      return props.tone as ActionTone;
    }
    return 'default';
  });
  const confirmPopoverWidth = 260;

  function handleConfirm() {
    return props.confirmHandler?.();
  }
</script>

<style lang="less" scoped>
  .app-confirm-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    height: var(--app-table-action-button-height);
    padding: 0 var(--app-table-action-button-padding-x);
    font-size: 13px;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    border: 1px solid;
    border-radius: var(--app-table-action-button-radius);
    transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease, opacity 0.16s ease;

    &--default {
      color: var(--app-table-action-default-text);
      background: var(--app-table-action-default-bg);
      border-color: var(--app-table-action-default-border);
    }

    &--primary {
      color: var(--app-table-action-primary-text);
      background: var(--app-table-action-primary-bg);
      border-color: var(--app-table-action-primary-border);
    }

    &--danger {
      color: var(--app-table-action-danger-text);
      background: var(--app-table-action-danger-bg);
      border-color: var(--app-table-action-danger-border);
    }

    &.is-disabled,
    &:disabled {
      color: var(--app-table-action-disabled-text);
      cursor: not-allowed;
      background: var(--app-table-action-disabled-bg);
      border-color: var(--app-table-action-disabled-border);
      opacity: 0.78;
    }
  }

  .app-confirm-action__content {
    display: grid;
    gap: 4px;
    width: min(100vw - 48px, var(--app-table-action-confirm-width));
    min-width: 0;

    strong {
      color: var(--app-text-color);
      font-size: var(--app-font-size-sm, 13px);
      line-height: 20px;
    }

    span {
      color: var(--app-icon-color);
      font-size: var(--app-font-size-sm, 13px);
      line-height: 20px;
    }
  }

  :deep(.n-popover) {
    background: var(--app-table-action-confirm-bg);
    border: 1px solid var(--app-table-action-confirm-border);
    border-radius: var(--app-table-action-confirm-radius);
    box-shadow: var(--app-table-action-confirm-shadow);
  }
</style>

<style lang="less">
  .app-confirm-action-popover {
    max-width: min(calc(100vw - 48px), 260px);
    background: var(--app-table-action-confirm-bg);
    border: 1px solid var(--app-table-action-confirm-border);
    border-radius: var(--app-table-action-confirm-radius);
    box-shadow: var(--app-table-action-confirm-shadow);
  }
</style>
