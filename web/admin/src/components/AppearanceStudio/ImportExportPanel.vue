<template>
  <div class="io-panel">
    <n-alert type="info" :bordered="false">
      当前作用范围：{{ appearanceStore.currentTenantKey }} / {{ appearanceStore.currentUsername }}
    </n-alert>
    <n-space>
      <n-button size="small" @click="output = appearanceStore.exportThemeOverridesJSON()">
        导出主题覆盖
      </n-button>
      <n-button size="small" @click="output = appearanceStore.exportAppearanceJSON()">
        导出完整外观
      </n-button>
      <n-button size="small" secondary @click="importCurrent">导入配置</n-button>
      <n-button size="small" tertiary type="error" @click="appearanceStore.resetAll">
        全部重置
      </n-button>
    </n-space>
    <n-input
      v-model:value="output"
      type="textarea"
      :autosize="{ minRows: 12, maxRows: 18 }"
      placeholder="导出的 JSON 会显示在这里；也可以粘贴完整外观 JSON 后点击导入配置。"
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
      message.success('已为当前租户和用户导入外观配置。');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '导入失败。');
    }
  }
</script>

<style lang="less" scoped>
  .io-panel {
    display: grid;
    gap: 12px;
  }
</style>
