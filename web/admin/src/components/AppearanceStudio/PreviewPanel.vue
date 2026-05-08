<template>
  <n-config-provider :theme-overrides="appearanceStore.editorThemeOverrides">
    <div
      class="preview-panel"
      :class="appearanceStore.editorEffectiveSkinClass"
      :style="appearanceStore.editorCssVars"
    >
      <n-card title="控件预览" size="small">
        <n-space vertical>
          <n-space>
            <n-button type="primary">主要操作</n-button>
            <n-button>默认按钮</n-button>
            <n-button tertiary>弱按钮</n-button>
          </n-space>
          <n-input value="复核功能点推荐" />
          <n-select :value="'review'" :options="selectOptions" />
          <n-space>
            <n-tag type="info">草稿</n-tag>
            <n-tag type="success">已匹配</n-tag>
            <n-tag type="warning">待复核</n-tag>
          </n-space>
        </n-space>
      </n-card>

      <n-card title="表格预览" size="small">
        <n-data-table
          class="appearance-table-preview"
          :columns="columns"
          :data="data"
          :pagination="{ pageSize: 3 }"
          :row-key="(row) => row.name"
          :checked-row-keys="['文档上传']"
          size="medium"
        />
      </n-card>
    </div>
  </n-config-provider>
</template>

<script lang="ts" setup>
  import { h } from 'vue';
  import type { DataTableColumns } from 'naive-ui';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';

  const appearanceStore = useAppearanceStore();

  const selectOptions = [
    { label: '待复核', value: 'review' },
    { label: '可复用功能点', value: 'reusable' },
  ];

  const columns: DataTableColumns<Recordable> = [
    { type: 'selection', width: 48 },
    { title: '名称', key: 'name' },
    {
      title: '状态',
      key: 'status',
      render(row) {
        return h(AppStatusTag, { tone: String(row.tone || 'neutral') as any, label: String(row.status || '') });
      },
    },
    { title: '置信度', key: 'confidence', sorter: 'default' },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render() {
        return h(AppTableActions, {
          actions: [
            { label: '查看', type: 'default' },
            { label: '复核', type: 'primary' },
          ],
        });
      },
    },
  ];

  const data = [
    { name: '文档上传', status: '已匹配', tone: 'success', confidence: '92%' },
    { name: '审批流程', status: '待复核', tone: 'warning', confidence: '74%' },
    { name: '档案检索', status: '草稿', tone: 'neutral', confidence: '61%' },
  ];
</script>

<style lang="less" scoped>
  .preview-panel {
    display: grid;
    gap: 12px;
  }

  .appearance-table-preview {
    overflow: hidden;
    border-radius: var(--app-table-radius);
  }
</style>
