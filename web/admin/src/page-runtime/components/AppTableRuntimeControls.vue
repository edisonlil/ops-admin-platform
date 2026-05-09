<template>
  <div class="app-table-runtime-controls">
    <n-tooltip trigger="hover">
      <template #trigger>
        <n-button size="tiny" quaternary circle :class="{ 'is-active': fillHeight }" @click="emit('update:fillHeight', !fillHeight)">
          <template #icon>
            <n-icon>
              <FullscreenOutlined v-if="fillHeight" />
              <FullscreenExitOutlined v-else />
            </n-icon>
          </template>
        </n-button>
      </template>
      {{ fillHeight ? '取消高度铺满' : '高度铺满' }}
    </n-tooltip>

    <n-popselect :value="rowDensity" :options="rowDensityOptions" trigger="click" @update:value="handleRowDensityUpdate">
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary circle>
            <template #icon>
              <n-icon>
                <ColumnHeightOutlined />
              </n-icon>
            </template>
          </n-button>
        </template>
        行高密度
      </n-tooltip>
    </n-popselect>
  </div>
</template>

<script lang="ts" setup>
  import { NButton, NIcon, NPopselect, NTooltip } from 'naive-ui';
  import { ColumnHeightOutlined, FullscreenExitOutlined, FullscreenOutlined } from '@vicons/antd';
  import type { TableRowDensity } from '../types';

  defineProps<{
    fillHeight: boolean;
    rowDensity: TableRowDensity;
  }>();

  const emit = defineEmits<{
    'update:fillHeight': [value: boolean];
    'update:rowDensity': [value: TableRowDensity];
  }>();

  const rowDensityOptions: Array<{ label: string; value: TableRowDensity }> = [
    { label: '默认', value: 'default' },
    { label: '中等', value: 'medium' },
    { label: '紧凑', value: 'compact' },
  ];

  function handleRowDensityUpdate(value: string | number) {
    emit('update:rowDensity', value as TableRowDensity);
  }
</script>

<style lang="less" scoped>
  .app-table-runtime-controls {
    display: inline-flex;
    align-items: center;
    gap: 2px;

    :deep(.n-button.is-active) {
      color: var(--app-primary-color);
      background: var(--app-primary-soft-bg);
    }
  }
</style>
