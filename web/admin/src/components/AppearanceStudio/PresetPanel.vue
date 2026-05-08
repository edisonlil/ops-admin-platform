<template>
  <div class="preset-panel">
    <button
      v-for="preset in appearancePresets"
      :key="preset.id"
      class="preset-panel__item"
      :class="{ 'preset-panel__item--active': appearanceStore.editingPresetId === preset.id }"
      type="button"
      @click="appearanceStore.applyPreset(preset.id)"
    >
      <span>{{ preset.name }}</span>
      <small>{{ preset.description }}</small>
    </button>
    <n-button secondary size="small" @click="appearanceStore.resetToPreset">重置当前预设</n-button>
  </div>
</template>

<script lang="ts" setup>
  import { appearancePresets } from '@/appearance/presets';
  import { useAppearanceStore } from '@/store/modules/appearance';

  const appearanceStore = useAppearanceStore();
</script>

<style lang="less" scoped>
  .preset-panel {
    display: grid;
    gap: 10px;

    &__item {
      display: grid;
      gap: 4px;
      width: 100%;
      padding: 12px;
      text-align: left;
      border: 1px solid var(--app-border-color);
      border-radius: var(--app-card-radius);
      background: var(--app-surface-bg);
      cursor: pointer;

      span {
        color: var(--app-text-color);
        font-weight: 600;
      }

      small {
        color: var(--app-icon-color);
        line-height: 18px;
      }

      &--active {
        border-color: var(--app-primary-color);
        background: var(--app-surface-muted-bg);
      }
    }
  }
</style>
