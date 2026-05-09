<template>
  <div class="visual-token-panel">
    <section v-if="activeTarget === 'radius'" class="visual-token-panel__section">
      <header class="visual-token-panel__header">
        <span>全局样式</span>
        <strong>圆角</strong>
      </header>
      <TokenSizeRow
        v-for="item in radiusRows"
        :key="item.key"
        :label="item.label"
        :token-path="`primitive.${item.key}`"
        :model-value="primitive[item.key]"
        :min="0"
        :max="32"
        :resolved-value="primitive[item.key]"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
      />
    </section>
    <section v-else-if="activeTarget === 'type'" class="visual-token-panel__section">
      <header class="visual-token-panel__header">
        <span>全局样式</span>
        <strong>字体</strong>
      </header>
      <TokenSizeRow
        v-for="item in fontRows"
        :key="item.key"
        :label="item.label"
        :token-path="`primitive.${item.key}`"
        :model-value="primitive[item.key]"
        :min="10"
        :max="32"
        :resolved-value="primitive[item.key]"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
      />
    </section>
    <section v-else class="visual-token-panel__section">
      <header class="visual-token-panel__header">
        <span>全局样式</span>
        <strong>阴影</strong>
      </header>
      <TokenSelectRow
        label="弱阴影"
        token-path="primitive.shadowSm"
        :model-value="primitive.shadowSm"
        :options="shadowOptions"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken('shadowSm', value)"
      />
      <TokenSelectRow
        label="中阴影"
        token-path="primitive.shadowMd"
        :model-value="primitive.shadowMd"
        :options="shadowOptions"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken('shadowMd', value)"
      />
    </section>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import TokenSelectRow from './TokenSelectRow.vue';
  import TokenSizeRow from './TokenSizeRow.vue';

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

  const shadowOptions = [
    { label: '无阴影', value: 'none' },
    { label: '轻微阴影', value: '0 1px 2px rgb(15 23 42 / 6%)' },
    { label: '标准阴影', value: '0 8px 18px rgb(15 23 42 / 8%)' },
    { label: '强调阴影', value: '0 14px 32px rgb(15 23 42 / 12%)' },
  ];
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
