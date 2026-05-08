<template>
  <n-button class="appearance-studio-trigger" circle type="primary" @click="show = true">
    <template #icon>
      <n-icon>
        <BgColorsOutlined />
      </n-icon>
    </template>
  </n-button>

  <n-drawer v-model:show="show" :width="480" placement="right">
    <n-drawer-content title="外观工作台" closable>
      <div class="appearance-studio">
        <n-alert
          v-if="appearanceStore.editorValidationErrors.length"
          type="warning"
          :bordered="false"
          class="appearance-studio__errors"
        >
          <div v-for="error in appearanceStore.editorValidationErrors.slice(0, 4)" :key="error.path">
            {{ error.path }}: {{ error.message }}
          </div>
        </n-alert>

        <n-tabs type="line" animated>
          <n-tab-pane name="presets" tab="风格预设">
            <PresetPanel />
          </n-tab-pane>
          <n-tab-pane name="primitive" tab="基础变量">
            <PrimitivePanel />
          </n-tab-pane>
          <n-tab-pane name="semantic" tab="语义变量">
            <SemanticPanel />
          </n-tab-pane>
          <n-tab-pane name="visual" tab="圆角 / 字体">
            <VisualTokenPanel />
          </n-tab-pane>
          <n-tab-pane name="components" tab="组件样式">
            <ComponentPanel />
          </n-tab-pane>
          <n-tab-pane name="layout" tab="布局外观">
            <LayoutPanel />
          </n-tab-pane>
          <n-tab-pane name="behavior" tab="界面行为">
            <BehaviorPanel />
          </n-tab-pane>
          <n-tab-pane name="preview" tab="效果预览">
            <PreviewPanel />
          </n-tab-pane>
          <n-tab-pane name="io" tab="导入 / 导出">
            <ImportExportPanel />
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script lang="ts" setup>
  import { ref } from 'vue';
  import { BgColorsOutlined } from '@vicons/antd';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import BehaviorPanel from './BehaviorPanel.vue';
  import ImportExportPanel from './ImportExportPanel.vue';
  import ComponentPanel from './ComponentPanel.vue';
  import LayoutPanel from './LayoutPanel.vue';
  import PreviewPanel from './PreviewPanel.vue';
  import PresetPanel from './PresetPanel.vue';
  import PrimitivePanel from './PrimitivePanel.vue';
  import SemanticPanel from './SemanticPanel.vue';
  import VisualTokenPanel from './VisualTokenPanel.vue';

  const show = ref(false);
  const appearanceStore = useAppearanceStore();
</script>

<style lang="less" scoped>
  .appearance-studio-trigger {
    position: fixed;
    right: 22px;
    bottom: 88px;
    z-index: 30;
    box-shadow: var(--app-shadow-sm);
  }

  .appearance-studio {
    display: grid;
    gap: 12px;

    &__errors {
      margin-bottom: 4px;
    }
  }
</style>
