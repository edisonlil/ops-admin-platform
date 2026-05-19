<template>
  <div class="app-table-runtime-controls">
    <n-popover
      v-if="orderedColumns.length"
      trigger="click"
      placement="bottom-end"
      :width="286"
    >
      <template #trigger>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button size="tiny" quaternary circle>
              <template #icon>
                <n-icon>
                  <SettingOutlined />
                </n-icon>
              </template>
            </n-button>
          </template>
          列设置
        </n-tooltip>
      </template>
      <div class="app-table-runtime-controls__columns">
        <div class="app-table-runtime-controls__columns-header">
          <span>列设置</span>
          <n-button size="tiny" text @click="emit('resetColumns')">恢复默认</n-button>
        </div>
        <div class="app-table-runtime-controls__columns-hint">拖动调整显示顺序</div>
        <div class="app-table-runtime-controls__column-list">
          <div
            v-for="column in orderedColumns"
            :key="String(column.key)"
            class="app-table-runtime-controls__column-item"
            :class="{ 'is-dragging': draggingKey === String(column.key) }"
            draggable="true"
            @dragstart="handleDragStart(column)"
            @dragover.prevent
            @drop="handleDrop(column)"
            @dragend="handleDragEnd"
          >
            <button
              type="button"
              class="app-table-runtime-controls__drag-handle"
              aria-label="拖动排序"
            >
              <n-icon>
                <HolderOutlined />
              </n-icon>
            </button>
            <n-checkbox
              :checked="visibleColumnSet.has(String(column.key))"
              :disabled="column.required"
              @update:checked="(checked) => handleColumnChecked(column, checked)"
            >
              {{ column.label || column.key }}
            </n-checkbox>
          </div>
        </div>
      </div>
    </n-popover>

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
      {{ fillHeight ? '取消填满高度' : '填满高度' }}
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
        行密度
      </n-tooltip>
    </n-popselect>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref } from 'vue';
  import { NButton, NCheckbox, NIcon, NPopover, NPopselect, NTooltip } from 'naive-ui';
  import { ColumnHeightOutlined, FullscreenExitOutlined, FullscreenOutlined, HolderOutlined, SettingOutlined } from '@vicons/antd';
  import type { TableColumnPreferenceSchema, TableRowDensity } from '../types';

  const props = withDefaults(
    defineProps<{
      fillHeight: boolean;
      rowDensity: TableRowDensity;
      columns?: TableColumnPreferenceSchema[];
      visibleColumnKeys?: string[];
      columnOrderKeys?: string[];
    }>(),
    {
      columns: () => [],
      visibleColumnKeys: () => [],
      columnOrderKeys: () => [],
    }
  );

  const emit = defineEmits<{
    'update:fillHeight': [value: boolean];
    'update:rowDensity': [value: TableRowDensity];
    'update:visibleColumnKeys': [value: string[]];
    'update:columnOrderKeys': [value: string[]];
    resetColumns: [];
  }>();

  const draggingKey = ref<string | null>(null);

  const rowDensityOptions: Array<{ label: string; value: TableRowDensity }> = [
    { label: '默认', value: 'default' },
    { label: '适中', value: 'medium' },
    { label: '紧凑', value: 'compact' },
  ];

  const visibleColumnSet = computed(() => new Set(props.visibleColumnKeys.map(String)));

  const orderedColumns = computed(() => {
    if (!props.columnOrderKeys.length) return props.columns;
    const columnMap = new Map(props.columns.map((column) => [String(column.key), column]));
    const ordered = props.columnOrderKeys
      .map((key) => columnMap.get(String(key)))
      .filter((column): column is TableColumnPreferenceSchema => !!column);
    const orderedKeySet = new Set(ordered.map((column) => String(column.key)));
    const remaining = props.columns.filter((column) => !orderedKeySet.has(String(column.key)));
    return [...ordered, ...remaining];
  });

  function handleRowDensityUpdate(value: string | number) {
    emit('update:rowDensity', value as TableRowDensity);
  }

  function handleColumnChecked(column: TableColumnPreferenceSchema, checked: boolean) {
    const key = String(column.key);
    const nextKeys = checked
      ? [...props.visibleColumnKeys.map(String), key]
      : props.visibleColumnKeys.map(String).filter((item) => item !== key);
    emit('update:visibleColumnKeys', Array.from(new Set(nextKeys)));
  }

  function handleDragStart(column: TableColumnPreferenceSchema) {
    draggingKey.value = String(column.key);
  }

  function handleDrop(targetColumn: TableColumnPreferenceSchema) {
    if (!draggingKey.value) return;
    const targetKey = String(targetColumn.key);
    const sourceKey = draggingKey.value;
    if (sourceKey === targetKey) return;

    const keys = orderedColumns.value.map((column) => String(column.key));
    const sourceIndex = keys.indexOf(sourceKey);
    const targetIndex = keys.indexOf(targetKey);
    if (sourceIndex < 0 || targetIndex < 0) return;

    keys.splice(sourceIndex, 1);
    keys.splice(targetIndex, 0, sourceKey);
    emit('update:columnOrderKeys', keys);
  }

  function handleDragEnd() {
    draggingKey.value = null;
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

  .app-table-runtime-controls__columns {
    display: grid;
    gap: 10px;
    min-width: 0;
  }

  .app-table-runtime-controls__columns-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: var(--app-text-color);
    font-size: 13px;
    font-weight: 650;
  }

  .app-table-runtime-controls__columns-hint {
    color: var(--app-text-color-2);
    font-size: 12px;
    line-height: 1.4;
  }

  .app-table-runtime-controls__column-list {
    display: grid;
    gap: 4px;
    max-height: 320px;
    overflow: auto;
  }

  .app-table-runtime-controls__column-item {
    display: grid;
    grid-template-columns: 24px minmax(0, 1fr);
    gap: 6px;
    align-items: center;
    min-width: 0;
    padding: 4px 6px;
    cursor: grab;
    border-radius: 6px;
    transition:
      background-color 0.16s ease,
      opacity 0.16s ease;
  }

  .app-table-runtime-controls__column-item:hover {
    background: var(--app-surface-muted-bg);
  }

  .app-table-runtime-controls__column-item.is-dragging {
    opacity: 0.55;
  }

  .app-table-runtime-controls__drag-handle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    color: var(--app-icon-color);
    cursor: grab;
    background: transparent;
    border: 0;
    border-radius: 6px;
  }

  .app-table-runtime-controls__drag-handle:hover {
    color: var(--app-primary-color);
    background: var(--app-primary-soft-bg);
  }
</style>
