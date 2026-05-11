<template>
  <span class="app-status-tag" :class="`app-status-tag--${resolvedStatus.tone}`">
    {{ resolvedStatus.label }}
  </span>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { resolveAppStatusSemantic } from './statusSemantic';
  import type { AppStatusTone } from './statusSemantic';

  const props = withDefaults(
    defineProps<{
      label?: string;
      tone?: AppStatusTone | string;
      statusKey?: string;
    }>(),
    {
      tone: 'neutral',
    }
  );

  const resolvedTone = computed<AppStatusTone>(() => {
    if (['success', 'warning', 'error', 'info', 'neutral'].includes(props.tone)) {
      return props.tone as AppStatusTone;
    }
    return 'neutral';
  });

  const resolvedStatus = computed(() => {
    if (props.statusKey) {
      return resolveAppStatusSemantic(props.statusKey, {
        label: props.label || props.statusKey,
        tone: resolvedTone.value,
      });
    }
    return {
      label: props.label || '-',
      tone: resolvedTone.value,
    };
  });
</script>

<style lang="less" scoped>
  .app-status-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    height: var(--app-status-tag-height, 24px);
    padding: 0 var(--app-status-tag-padding-x, 8px);
    font-size: 12px;
    font-weight: var(--app-status-tag-font-weight, 500);
    line-height: 1;
    white-space: nowrap;
    border: 1px solid;
    border-radius: var(--app-status-tag-radius, 4px);

    &--success {
      color: var(--app-status-success-text, #047857);
      background: var(--app-status-success-bg, #ecfdf5);
      border-color: var(--app-status-success-border, #a7f3d0);
    }

    &--warning {
      color: var(--app-status-warning-text, #b45309);
      background: var(--app-status-warning-bg, #fffbeb);
      border-color: var(--app-status-warning-border, #fde68a);
    }

    &--error {
      color: var(--app-status-error-text, #be123c);
      background: var(--app-status-error-bg, #fff1f2);
      border-color: var(--app-status-error-border, #fecdd3);
    }

    &--info {
      color: var(--app-status-info-text, #2563eb);
      background: var(--app-status-info-bg, #eff6ff);
      border-color: var(--app-status-info-border, #bfdbfe);
    }

    &--neutral {
      color: var(--app-status-neutral-text, #64748b);
      background: var(--app-status-neutral-bg, #f8fafc);
      border-color: var(--app-status-neutral-border, #d9e1ec);
    }
  }
</style>
