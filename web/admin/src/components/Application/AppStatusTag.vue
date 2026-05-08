<template>
  <span class="app-status-tag" :class="`app-status-tag--${resolvedTone}`">
    {{ label }}
  </span>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';

  type StatusTone = 'success' | 'warning' | 'error' | 'info' | 'neutral';

  const props = withDefaults(
    defineProps<{
      label: string;
      tone?: StatusTone | string;
    }>(),
    {
      tone: 'neutral',
    }
  );

  const resolvedTone = computed<StatusTone>(() => {
    if (['success', 'warning', 'error', 'info', 'neutral'].includes(props.tone)) {
      return props.tone as StatusTone;
    }
    return 'neutral';
  });
</script>

<style lang="less" scoped>
  .app-status-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    height: var(--app-status-tag-height);
    padding: 0 var(--app-status-tag-padding-x);
    font-size: 12px;
    font-weight: var(--app-status-tag-font-weight);
    line-height: 1;
    white-space: nowrap;
    border: 1px solid;
    border-radius: var(--app-status-tag-radius);

    &--success {
      color: var(--app-status-success-text);
      background: var(--app-status-success-bg);
      border-color: var(--app-status-success-border);
    }

    &--warning {
      color: var(--app-status-warning-text);
      background: var(--app-status-warning-bg);
      border-color: var(--app-status-warning-border);
    }

    &--error {
      color: var(--app-status-error-text);
      background: var(--app-status-error-bg);
      border-color: var(--app-status-error-border);
    }

    &--info {
      color: var(--app-status-info-text);
      background: var(--app-status-info-bg);
      border-color: var(--app-status-info-border);
    }

    &--neutral {
      color: var(--app-status-neutral-text);
      background: var(--app-status-neutral-bg);
      border-color: var(--app-status-neutral-border);
    }
  }
</style>
