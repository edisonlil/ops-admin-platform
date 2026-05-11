<template>
  <n-popover
    v-if="confirm"
    v-model:show="confirmVisible"
    :disabled="disabled"
    trigger="click"
    to=".appearance-root"
    placement="top-end"
    :width="confirmPopoverWidth"
    :content-style="{ padding: '0' }"
    content-class="app-confirm-action-popover"
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
    <div class="app-confirm-action__panel" @click.stop>
      <div class="app-confirm-action__content">
        <strong v-if="confirmTitle">{{ confirmTitle }}</strong>
        <span>{{ confirmContent || '确认执行该操作吗？' }}</span>
      </div>
      <div class="app-confirm-action__footer">
        <button class="app-confirm-action__cancel" type="button" :disabled="loading" @click="handleCancel">
          {{ negativeText }}
        </button>
        <button
          class="app-confirm-action__confirm"
          :class="{ 'is-danger': resolvedTone === 'danger' }"
          type="button"
          :disabled="loading"
          @click="handleConfirm"
        >
          {{ positiveText }}
        </button>
      </div>
    </div>
  </n-popover>
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
  import { computed, ref } from 'vue';

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
  const confirmVisible = ref(false);
  const confirmPopoverWidth = 236;

  function handleCancel() {
    confirmVisible.value = false;
    emit('cancel');
  }

  async function handleConfirm() {
    await props.confirmHandler?.();
    confirmVisible.value = false;
  }
</script>

<style lang="less" scoped>
  .app-confirm-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    height: var(--app-table-action-button-height, 30px);
    padding: 0 var(--app-table-action-button-padding-x, 12px);
    font-size: 13px;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    border: 1px solid;
    border-radius: var(--app-table-action-button-radius, 6px);
    transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease, opacity 0.16s ease;

    &--default {
      color: var(--app-table-action-default-text, #2563eb);
      background: var(--app-table-action-default-bg, #ffffff);
      border-color: var(--app-table-action-default-border, #d9e1ec);
    }

    &--primary {
      color: var(--app-table-action-primary-text, #ffffff);
      background: var(--app-table-action-primary-bg, #2563eb);
      border-color: var(--app-table-action-primary-border, #2563eb);
    }

    &--danger {
      color: var(--app-table-action-danger-text, #dc2626);
      background: var(--app-table-action-danger-bg, #ffffff);
      border-color: var(--app-table-action-danger-border, #dc2626);
    }

    &.is-disabled,
    &:disabled {
      color: var(--app-table-action-disabled-text, #94a3b8);
      cursor: not-allowed;
      background: var(--app-table-action-disabled-bg, #f8fafc);
      border-color: var(--app-table-action-disabled-border, #d9e1ec);
      opacity: 0.78;
    }
  }

  .app-confirm-action__content {
    display: grid;
    gap: 5px;
    min-width: 0;

    strong {
      color: var(--app-text-color, #1f2937);
      font-size: 13px;
      font-weight: 700;
      line-height: 18px;
    }

    span {
      color: var(--app-icon-color, #64748b);
      font-size: 13px;
      line-height: 18px;
    }
  }

  .app-confirm-action__panel {
    display: grid;
    gap: 10px;
    box-sizing: border-box;
    width: min(calc(100vw - 40px), 236px);
    padding: 12px;
    background: var(--app-table-action-confirm-bg, #ffffff);
    border: 1px solid var(--app-table-action-confirm-border, #d9e1ec);
    border-radius: var(--app-table-action-confirm-radius, 6px);
    box-shadow: var(--app-table-action-confirm-shadow, 0 8px 24px rgb(15 23 42 / 12%));
  }

  .app-confirm-action__footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .app-confirm-action__cancel,
  .app-confirm-action__confirm {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 52px;
    height: 28px;
    padding: 0 11px;
    font-size: 13px;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    border: 1px solid;
    border-radius: var(--app-table-action-button-radius, 6px);
    transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease, opacity 0.16s ease;

    &:disabled {
      cursor: not-allowed;
      opacity: 0.68;
    }
  }

  .app-confirm-action__cancel {
    color: var(--app-table-action-default-text, #2563eb);
    background: var(--app-table-action-default-bg, #ffffff);
    border-color: var(--app-table-action-default-border, #d9e1ec);
  }

  .app-confirm-action__confirm {
    color: var(--app-table-action-primary-text, #ffffff);
    background: var(--app-table-action-primary-bg, #2563eb);
    border-color: var(--app-table-action-primary-border, #2563eb);

    &.is-danger {
      color: var(--app-table-action-danger-text, #dc2626);
      background: color-mix(in srgb, var(--app-table-action-danger-text, #dc2626) 10%, var(--app-table-action-danger-bg, #ffffff));
      border-color: var(--app-table-action-danger-border, #dc2626);
    }
  }
</style>

<style lang="less">
  .n-popover.app-confirm-action-popover,
  .n-popover:has(.app-confirm-action-popover) {
    padding: 0;
    overflow: visible;
    background: transparent;
    border: 0;
    box-shadow: none;
  }

  .app-confirm-action-popover {
    max-width: min(calc(100vw - 40px), 236px);
  }
</style>
