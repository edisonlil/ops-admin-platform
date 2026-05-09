<template>
  <div class="preset-panel">
    <div class="preset-panel__header">
      <div>
        <h3>选择一个起点</h3>
        <p>预设会重置当前草稿中的覆盖项，适合先定整体气质，再进入变量微调。</p>
      </div>
      <n-button secondary size="small" @click="appearanceStore.resetToPreset">重置当前预设</n-button>
    </div>

    <div class="preset-panel__grid">
      <button
        v-for="preset in appearancePresets"
        :key="preset.id"
        class="preset-panel__item"
        :class="{ 'preset-panel__item--active': appearanceStore.editingPresetId === preset.id }"
        type="button"
        @click="appearanceStore.applyPreset(preset.id)"
      >
        <span class="preset-panel__swatches" aria-hidden="true">
          <i :style="{ background: preset.tokens.semantic.primaryColor }"></i>
          <i :style="{ background: preset.tokens.semantic.surfaceColor }"></i>
          <i :style="{ background: preset.tokens.semantic.borderColorBase }"></i>
        </span>
        <span class="preset-panel__content">
          <strong>{{ preset.name }}</strong>
          <small>{{ preset.description }}</small>
          <em>{{ preset.id }}</em>
        </span>
      </button>
    </div>
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
    gap: 14px;

    &__header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      min-width: 0;

      h3 {
        margin: 0;
        color: var(--app-text-color);
        font-size: calc(var(--app-font-size-base, 14px) + 4px);
        font-weight: 700;
        line-height: 24px;
      }

      p {
        max-width: 560px;
        margin: 2px 0 0;
        color: var(--app-icon-color);
        line-height: 22px;
      }
    }

    &__grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }

    &__item {
      display: grid;
      grid-template-columns: 48px minmax(0, 1fr);
      gap: 12px;
      width: 100%;
      min-height: 116px;
      padding: 14px;
      font: inherit;
      text-align: left;
      cursor: pointer;
      background: var(--app-surface-bg);
      border: 1px solid var(--app-border-color);
      border-radius: var(--app-card-radius);
      transition:
        border-color 0.18s ease,
        background 0.18s ease;

      &:hover {
        background: var(--app-hover-color);
      }

      &--active {
        background: var(--app-surface-muted-bg);
        border-color: var(--app-primary-color);
      }
    }

    &__swatches {
      display: grid;
      align-content: start;
      gap: 6px;

      i {
        display: block;
        width: 40px;
        height: 22px;
        border: 1px solid var(--app-border-color);
        border-radius: 6px;
      }
    }

    &__content {
      display: grid;
      gap: 5px;
      min-width: 0;

      strong {
        color: var(--app-text-color);
        font-weight: 700;
        line-height: 22px;
      }

      small {
        color: var(--app-icon-color);
        font-size: var(--app-font-size-sm, 13px);
        line-height: 20px;
      }

      em {
        color: var(--app-icon-color);
        font-size: var(--app-font-size-xs, 12px);
        font-style: normal;
        line-height: 18px;
      }
    }

    @media (max-width: 720px) {
      &__header {
        flex-direction: column;
      }
    }
  }
</style>
