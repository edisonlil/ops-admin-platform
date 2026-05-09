<template>
  <div class="visual-token-panel">
    <section v-if="activeTarget === 'radius'" class="visual-token-panel__section">
      <header class="visual-token-panel__header">
        <span>全局样式</span>
        <strong>圆角</strong>
      </header>
      <TokenTextRow
        v-for="item in radiusRows"
        :key="item.key"
        :label="item.label"
        :token-path="`primitive.${item.key}`"
        :model-value="primitive[item.key]"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
      />
    </section>
    <section v-else-if="activeTarget === 'type'" class="visual-token-panel__section">
      <header class="visual-token-panel__header">
        <span>全局样式</span>
        <strong>字体</strong>
      </header>
      <TokenTextRow
        v-for="item in fontRows"
        :key="item.key"
        :label="item.label"
        :token-path="`primitive.${item.key}`"
        :model-value="primitive[item.key]"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
      />
    </section>
    <section v-else class="visual-token-panel__section">
      <header class="visual-token-panel__header">
        <span>全局样式</span>
        <strong>阴影</strong>
      </header>
      <TokenTextRow
        v-for="item in shadowRows"
        :key="item.key"
        :label="item.label"
        :token-path="`primitive.${item.key}`"
        :model-value="primitive[item.key]"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
      />
    </section>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import TokenTextRow from './TokenTextRow.vue';

  const props = defineProps<{
    target?: string;
  }>();

  const appearanceStore = useAppearanceStore();
  const primitive = computed(() => appearanceStore.editorMergedTokens.primitive);
  const activeTarget = computed(() => props.target || 'radius');

  const radiusRows = [
    { key: 'radiusXs', label: '超小圆角' },
    { key: 'radiusSm', label: '小圆角' },
    { key: 'radiusMd', label: '中圆角' },
    { key: 'radiusLg', label: '大圆角' },
  ] as const;

  const fontRows = [
    { key: 'fontSizeXs', label: '超小字号' },
    { key: 'fontSizeSm', label: '小字号' },
    { key: 'fontSizeMd', label: '基础字号' },
    { key: 'fontSizeLg', label: '大字号' },
  ] as const;

  const shadowRows = [
    { key: 'shadowNone', label: '无阴影' },
    { key: 'shadowSm', label: '弱阴影' },
    { key: 'shadowMd', label: '中阴影' },
  ] as const;
</script>

<style lang="less" scoped>
  .visual-token-panel {
    min-width: 0;
  }

  .visual-token-panel__section {
    display: grid;
    gap: 0;
    min-width: 0;
  }

  .visual-token-panel__header {
    display: grid;
    gap: 2px;
    margin-bottom: 14px;

    span {
      color: var(--app-icon-color);
      font-size: 12px;
      line-height: 18px;
    }

    strong {
      color: var(--app-text-color);
      font-size: 18px;
      font-weight: 700;
      line-height: 26px;
    }
  }
</style>
