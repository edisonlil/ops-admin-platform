<template>
  <div class="token-text-row">
    <div class="token-text-row__meta">
      <span class="token-text-row__label">{{ label }}</span>
      <span class="token-text-row__path">{{ tokenPath }}</span>
    </div>
    <n-input
      size="small"
      :value="modelValue"
      :placeholder="placeholder"
      @update:value="(value) => emit('update:modelValue', value)"
    />
    <div v-if="resolvedValue && resolvedValue !== modelValue" class="token-text-row__resolved">
      解析值 {{ resolvedValue }}
    </div>
  </div>
</template>

<script lang="ts" setup>
  defineProps<{
    label: string;
    tokenPath: string;
    modelValue: string;
    resolvedValue?: string;
    placeholder?: string;
  }>();

  const emit = defineEmits<{
    (event: 'update:modelValue', value: string): void;
  }>();
</script>

<style lang="less" scoped>
  .token-text-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) minmax(160px, 220px);
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

    &__path,
    &__resolved {
      display: block;
      color: var(--app-icon-color);
      font-size: 12px;
      line-height: 18px;
    }

    &__resolved {
      grid-column: 2;
    }
  }
</style>
