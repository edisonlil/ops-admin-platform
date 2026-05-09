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
      <TokenSelectRow
        label="字体"
        token-path="semantic.fontFamilyBase"
        :model-value="fontFamilyValue"
        :options="fontOptions"
        @update:model-value="(value) => appearanceStore.updateSemanticToken('fontFamilyBase', value)"
      />
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
  import { computed, onMounted, ref } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import TokenSelectRow from './TokenSelectRow.vue';
  import TokenSizeRow from './TokenSizeRow.vue';

  const props = defineProps<{
    target?: string;
  }>();

  const appearanceStore = useAppearanceStore();
  const primitive = computed(() => appearanceStore.editorMergedTokens.primitive);
  const semantic = computed(() => appearanceStore.editorMergedTokens.semantic);
  const resolvedSemantic = computed(() => appearanceStore.editorResolvedTokens.semantic);
  const activeTarget = computed(() => props.target || 'radius');

  type FontOption = {
    label: string;
    value: string;
    family?: string;
  };

  const systemFontOptions: FontOption[] = [
    { label: '跟随系统默认', value: '{fontFamilySans}' },
    { label: 'Microsoft YaHei', value: '"Microsoft YaHei", sans-serif', family: 'Microsoft YaHei' },
    { label: 'PingFang SC', value: '"PingFang SC", sans-serif', family: 'PingFang SC' },
    { label: 'Segoe UI', value: '"Segoe UI", sans-serif', family: 'Segoe UI' },
    { label: 'Noto Sans CJK SC', value: '"Noto Sans CJK SC", sans-serif', family: 'Noto Sans CJK SC' },
    { label: 'Source Han Sans SC', value: '"Source Han Sans SC", sans-serif', family: 'Source Han Sans SC' },
    { label: 'Hiragino Sans GB', value: '"Hiragino Sans GB", sans-serif', family: 'Hiragino Sans GB' },
    { label: 'SimSun', value: 'SimSun, serif', family: 'SimSun' },
    { label: 'SimHei', value: 'SimHei, sans-serif', family: 'SimHei' },
    { label: 'Arial', value: 'Arial, sans-serif', family: 'Arial' },
    { label: 'Helvetica Neue', value: '"Helvetica Neue", sans-serif', family: 'Helvetica Neue' },
  ];

  const availableFontOptions = ref<FontOption[]>(systemFontOptions);
  const fontFamilyValue = computed(
    () => semantic.value.fontFamilyBase || resolvedSemantic.value.fontFamilyBase || '{fontFamilySans}'
  );
  const fontOptions = computed(() => {
    const exists = availableFontOptions.value.some((option) => option.value === fontFamilyValue.value);
    if (exists) return availableFontOptions.value;
    return [{ label: '当前字体', value: fontFamilyValue.value }, ...availableFontOptions.value];
  });

  function isFontAvailable(fontName: string) {
    if (typeof document === 'undefined') return true;
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) return true;

    const sample = 'mmmmmmmmmmllllll速搭Aa123';
    const bases = ['monospace', 'sans-serif', 'serif'];
    return bases.some((base) => {
      context.font = `72px ${base}`;
      const baseWidth = context.measureText(sample).width;
      context.font = `72px "${fontName}", ${base}`;
      return context.measureText(sample).width !== baseWidth;
    });
  }

  onMounted(() => {
    availableFontOptions.value = systemFontOptions.filter(
      (option) => !option.family || isFontAvailable(option.family)
    );
  });

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
      font-size: var(--app-font-size-sm, 13px);
      line-height: 18px;
    }

    strong {
      color: var(--app-text-color);
      font-size: calc(var(--app-font-size-base, 14px) + 4px);
      font-weight: 700;
      line-height: 24px;
    }
  }
</style>
