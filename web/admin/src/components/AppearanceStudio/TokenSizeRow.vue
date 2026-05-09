<template>
  <div class="token-size-row">
    <div class="token-size-row__meta">
      <span class="token-size-row__label">{{ label }}</span>
      <span class="token-size-row__path">{{ tokenPath }}</span>
    </div>
    <n-input-number
      size="small"
      :value="numericValue"
      :min="min"
      :max="max"
      :step="step"
      :show-button="false"
      :placeholder="placeholder"
      @update:value="updateValue"
    >
      <template #suffix>{{ unit }}</template>
    </n-input-number>
    <div v-if="hintText" class="token-size-row__hint">
      {{ hintText }}
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';

  const props = withDefaults(
    defineProps<{
      label: string;
      tokenPath: string;
      modelValue: string;
      resolvedValue?: string;
      min?: number;
      max?: number;
      step?: number;
      unit?: 'px';
      placeholder?: string;
    }>(),
    {
      unit: 'px',
      min: 0,
      step: 1,
      placeholder: '自动',
    },
  );

  const emit = defineEmits<{
    (event: 'update:modelValue', value: string): void;
  }>();

  const numericValue = computed(() => parseSize(props.modelValue) ?? parseSize(props.resolvedValue) ?? null);
  const hintText = computed(() => {
    if (!props.modelValue?.startsWith('{')) return '';
    if (!props.resolvedValue) return `当前引用 ${props.modelValue}`;
    return `当前引用 ${props.modelValue}，解析为 ${props.resolvedValue}`;
  });

  function parseSize(value?: string) {
    if (!value) return null;
    const match = value.trim().match(/^(-?\d+(?:\.\d+)?)px$/);
    return match ? Number(match[1]) : null;
  }

  function updateValue(value: number | null) {
    if (value === null) return;
    emit('update:modelValue', `${value}${props.unit}`);
  }
</script>

<style lang="less" scoped>
  .token-size-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) 140px;
    gap: 10px;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid var(--app-border-color);

    &__label {
      display: block;
      color: var(--app-text-color);
      font-size: var(--app-font-size-md, 14px);
      font-weight: 500;
      line-height: 20px;
    }

    &__path,
    &__hint {
      display: block;
      color: var(--app-icon-color);
      font-size: var(--app-font-size-xs, 12px);
      line-height: 18px;
    }

    &__hint {
      grid-column: 2;
    }
  }
</style>
