<template>
  <div>
    <TokenColorRow
      v-for="item in colorRows"
      :key="item.key"
      :label="item.label"
      :token-path="`primitive.${item.key}`"
      :model-value="sourceTokens[item.key]"
      :resolved-value="resolvedTokens[item.key]"
      @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
    />
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import TokenColorRow from './TokenColorRow.vue';

  const appearanceStore = useAppearanceStore();
  const sourceTokens = computed(() => appearanceStore.editorMergedTokens.primitive);
  const resolvedTokens = computed(() => appearanceStore.editorResolvedTokens.primitive);

  const colorRows = [
    { key: 'blue500', label: '品牌主色阶' },
    { key: 'blue600', label: '品牌深色阶' },
    { key: 'gray50', label: '页面背景' },
    { key: 'gray200', label: '弱边框色' },
    { key: 'gray900', label: '正文颜色' },
    { key: 'green500', label: '成功色' },
    { key: 'amber500', label: '警告色' },
    { key: 'red500', label: '错误色' },
  ] as const;
</script>
