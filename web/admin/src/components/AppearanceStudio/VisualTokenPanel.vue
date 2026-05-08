<template>
  <n-collapse default-expanded-names="radius">
    <n-collapse-item title="圆角" name="radius">
      <TokenTextRow
        v-for="item in radiusRows"
        :key="item.key"
        :label="item.label"
        :token-path="`primitive.${item.key}`"
        :model-value="primitive[item.key]"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
      />
    </n-collapse-item>
    <n-collapse-item title="字体" name="type">
      <TokenTextRow
        v-for="item in fontRows"
        :key="item.key"
        :label="item.label"
        :token-path="`primitive.${item.key}`"
        :model-value="primitive[item.key]"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
      />
    </n-collapse-item>
    <n-collapse-item title="阴影" name="shadow">
      <TokenTextRow
        v-for="item in shadowRows"
        :key="item.key"
        :label="item.label"
        :token-path="`primitive.${item.key}`"
        :model-value="primitive[item.key]"
        @update:model-value="(value) => appearanceStore.updatePrimitiveToken(item.key, value)"
      />
    </n-collapse-item>
  </n-collapse>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import TokenTextRow from './TokenTextRow.vue';

  const appearanceStore = useAppearanceStore();
  const primitive = computed(() => appearanceStore.editorMergedTokens.primitive);

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
