<template>
  <div class="token-number-row">
    <div class="token-number-row__meta">
      <span class="token-number-row__label">{{ label }}</span>
      <span class="token-number-row__path">{{ tokenPath }}</span>
    </div>
    <n-input-number
      size="small"
      :value="modelValue"
      :min="min"
      :max="max"
      :step="step"
      @update:value="(value) => emit('update:modelValue', value ?? min ?? 0)"
    />
  </div>
</template>

<script lang="ts" setup>
  defineProps<{
    label: string;
    tokenPath: string;
    modelValue: number;
    min?: number;
    max?: number;
    step?: number;
  }>();

  const emit = defineEmits<{
    (event: 'update:modelValue', value: number): void;
  }>();
</script>

<style lang="less" scoped>
  .token-number-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) 140px;
    gap: 10px;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid var(--app-border-color);

    &__label {
      display: block;
      color: var(--app-text-color);
      font-weight: 500;
      line-height: 20px;
    }

    &__path {
      display: block;
      color: var(--app-icon-color);
      font-size: 12px;
      line-height: 18px;
    }
  }
</style>
