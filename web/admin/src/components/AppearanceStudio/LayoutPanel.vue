<template>
  <div>
    <TokenSelectRow
      label="界面密度"
      token-path="layout.density"
      :model-value="layout.density"
      :options="densityOptions"
      @update:model-value="(value) => appearanceStore.updateLayoutToken('density', value as any)"
    />
    <TokenNumberRow
      label="顶栏高度"
      token-path="layout.headerHeight"
      :model-value="layout.headerHeight"
      :min="48"
      :max="88"
      @update:model-value="(value) => appearanceStore.updateLayoutToken('headerHeight', value)"
    />
    <TokenNumberRow
      label="菜单宽度"
      token-path="layout.menuWidth"
      :model-value="layout.menuWidth"
      :min="160"
      :max="280"
      @update:model-value="(value) => appearanceStore.updateLayoutToken('menuWidth', value)"
    />
    <TokenNumberRow
      label="折叠菜单宽度"
      token-path="layout.collapsedMenuWidth"
      :model-value="layout.collapsedMenuWidth"
      :min="48"
      :max="88"
      @update:model-value="(value) => appearanceStore.updateLayoutToken('collapsedMenuWidth', value)"
    />
    <TokenNumberRow
      label="内容区间距"
      token-path="layout.contentPadding"
      :model-value="layout.contentPadding"
      :min="0"
      :max="32"
      @update:model-value="(value) => appearanceStore.updateLayoutToken('contentPadding', value)"
    />
    <TokenSelectRow
      label="卡片样式"
      token-path="layout.cardStyle"
      :model-value="layout.cardStyle"
      :options="cardStyleOptions"
      @update:model-value="(value) => appearanceStore.updateLayoutToken('cardStyle', value as any)"
    />
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import TokenNumberRow from './TokenNumberRow.vue';
  import TokenSelectRow from './TokenSelectRow.vue';

  const appearanceStore = useAppearanceStore();
  const layout = computed(() => appearanceStore.editorLayoutConfig);

  const densityOptions = [
    { label: '紧凑', value: 'compact' },
    { label: '默认', value: 'default' },
    { label: '宽松', value: 'comfortable' },
  ];

  const cardStyleOptions = [
    { label: '边框', value: 'bordered' },
    { label: '阴影', value: 'shadow' },
    { label: '扁平', value: 'flat' },
  ];
</script>
