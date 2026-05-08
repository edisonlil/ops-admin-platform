<template>
  <div class="setting-switch-row">
    <div class="setting-switch-row__meta">
      <span class="setting-switch-row__label">{{ label }}</span>
      <span class="setting-switch-row__path">{{ settingPath }}</span>
    </div>
    <n-switch
      size="small"
      :value="modelValue"
      :disabled="disabled"
      @update:value="(value) => emit('update:modelValue', value)"
    />
  </div>
</template>

<script lang="ts" setup>
  defineProps<{
    label: string;
    settingPath: string;
    modelValue: boolean;
    disabled?: boolean;
  }>();

  const emit = defineEmits<{
    (event: 'update:modelValue', value: boolean): void;
  }>();
</script>

<style lang="less" scoped>
  .setting-switch-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) auto;
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
