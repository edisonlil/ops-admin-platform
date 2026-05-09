<template>
  <div class="io-panel">
    <n-alert type="info" :bordered="false">
      当前导入只会更新这个主题草稿，并在保存后作用于当前主题；运行时本地配置作用域为
      {{ appearanceStore.currentTenantKey }} / {{ appearanceStore.currentUsername }}。
    </n-alert>

    <div class="io-panel__actions">
      <n-button size="small" @click="output = appearanceStore.exportThemeOverridesJSON()">
        导出 Naive 覆盖
      </n-button>
      <n-button size="small" @click="output = appearanceStore.exportAppearanceJSON()">
        导出完整外观
      </n-button>
      <n-button size="small" secondary @click="importCurrent">导入完整外观</n-button>
      <n-button size="small" tertiary type="error" @click="appearanceStore.resetAll">
        全部重置
      </n-button>
    </div>

    <n-input
      v-model:value="output"
      type="textarea"
      :autosize="{ minRows: 14, maxRows: 22 }"
      placeholder="导出的 JSON 会显示在这里；也可以粘贴完整 Appearance JSON 后点击导入完整外观。"
    />
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import { useAppearanceStore } from '@/store/modules/appearance';

  const appearanceStore = useAppearanceStore();
  const message = useMessage();
  const output = ref('');

  function importCurrent() {
    try {
      appearanceStore.importAppearanceJSON(output.value);
      message.success('已导入到当前主题草稿。保存草稿后才会写入主题资产。');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '导入失败。');
    }
  }
</script>

<style lang="less" scoped>
  .io-panel {
    display: grid;
    gap: 12px;

    &__actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
  }
</style>
