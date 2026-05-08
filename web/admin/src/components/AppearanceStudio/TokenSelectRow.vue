<template>
  <div class="token-select-row">
    <div class="token-select-row__meta">
      <span class="token-select-row__label">{{ label }}</span>
      <span class="token-select-row__path">{{ tokenPath }}</span>
    </div>
    <n-select
      size="small"
      :value="modelValue"
      :options="options"
      @update:value="(value) => emit('update:modelValue', value)"
    />
  </div>
</template>

<script lang="ts" setup>
  defineProps<{
    label: string;
    tokenPath: string;
    modelValue: string;
    options: { label: string; value: string }[];
  }>();

  const emit = defineEmits<{
    (event: 'update:modelValue', value: string): void;
  }>();
</script>

<style lang="less" scoped>
  .token-select-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) 180px;
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
