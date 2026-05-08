<template>
  <div>
    <n-alert type="info" :bordered="false" class="semantic-panel__hint">
      当前编辑{{ designStore.darkTheme ? '暗色' : '亮色' }}语义变量。
    </n-alert>
    <TokenColorRow
      v-for="item in colorRows"
      :key="item.key"
      :label="item.label"
      :token-path="`semantic.${item.key}`"
      :model-value="sourceTokens[item.key]"
      :resolved-value="resolvedTokens[item.key]"
      @update:model-value="(value) => appearanceStore.updateSemanticToken(item.key, value)"
    />
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import { useDesignSettingStore } from '@/store/modules/designSetting';
  import TokenColorRow from './TokenColorRow.vue';

  const appearanceStore = useAppearanceStore();
  const designStore = useDesignSettingStore();
  const sourceTokens = computed(() => appearanceStore.editorMergedTokens.semantic);
  const resolvedTokens = computed(() => appearanceStore.editorResolvedTokens.semantic);

  const colorRows = [
    { key: 'primaryColor', label: '主色' },
    { key: 'primaryColorHover', label: '主色悬停态' },
    { key: 'primaryColorPressed', label: '主色按下态' },
    { key: 'primaryColorSoft', label: '主色弱背景' },
    { key: 'pageBgColor', label: '页面背景' },
    { key: 'surfaceColor', label: '内容面背景' },
    { key: 'surfaceMutedColor', label: '弱内容面背景' },
    { key: 'textColorBase', label: '正文颜色' },
    { key: 'textColorSecondary', label: '次级文字' },
    { key: 'borderColorBase', label: '基础边框' },
  ] as const;
</script>

<style lang="less" scoped>
  .semantic-panel__hint {
    margin-bottom: 8px;
  }
</style>
