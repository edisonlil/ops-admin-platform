<template>
  <div class="token-color-row">
    <div class="token-color-row__meta">
      <span class="token-color-row__label">{{ label }}</span>
      <span class="token-color-row__path">{{ tokenPath }}</span>
    </div>
    <div class="token-color-row__control">
      <input class="token-color-row__swatch" type="color" :value="colorValue" @input="onColorInput" />
      <n-input size="small" :value="modelValue" @update:value="onTextInput" />
    </div>
    <div v-if="resolvedValue && resolvedValue !== modelValue" class="token-color-row__resolved">
      解析值 {{ resolvedValue }}
    </div>
  </div>
</template>

<script lang="ts" setup>
  const props = defineProps<{
    label: string;
    tokenPath: string;
    modelValue: string;
    resolvedValue?: string;
  }>();

  const emit = defineEmits<{
    (event: 'update:modelValue', value: string): void;
  }>();

  const colorValue = props.modelValue.startsWith('#')
    ? props.modelValue
    : props.resolvedValue?.startsWith('#')
    ? props.resolvedValue
    : '#000000';

  function onColorInput(event: Event) {
    emit('update:modelValue', (event.target as HTMLInputElement).value);
  }

  function onTextInput(value: string) {
    emit('update:modelValue', value);
  }
</script>

<style lang="less" scoped>
  .token-color-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) minmax(190px, 220px);
    gap: 10px;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid var(--app-border-color);

    &__meta {
      min-width: 0;
    }

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

    &__control {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    &__swatch {
      flex: 0 0 32px;
      width: 32px;
      height: 28px;
      padding: 0;
      border: 1px solid var(--app-border-color);
      border-radius: var(--app-card-radius);
      background: var(--app-surface-bg);
    }

    &__resolved {
      grid-column: 2;
    }
  }
</style>
