<template>
  <div class="dashboard-grid-canvas" :class="{ 'is-readonly': readonly }">
    <GridLayout
      v-model:layout="innerLayout"
      :col-num="layout.cols || 24"
      :row-height="layout.rowHeight || 64"
      :is-draggable="!readonly"
      :is-resizable="!readonly"
      :vertical-compact="true"
      :use-css-transforms="true"
      @layout-updated="emitLayoutChange"
    >
      <GridItem
        v-for="item in innerLayout"
        :key="item.i"
        :x="item.x"
        :y="item.y"
        :w="item.w"
        :h="item.h"
        :i="item.i"
        @click="selectItem(item.i)"
      >
        <div class="dashboard-grid-canvas__item" :class="{ 'is-selected': item.i === selectedId && !readonly }">
          <div v-if="item.i === selectedId && !readonly" class="dashboard-grid-canvas__item-tools" @click.stop>
            <n-dropdown
              trigger="click"
              :options="componentActionOptions"
              :style="{ minWidth: '148px' }"
              @select="(key) => handleComponentAction(key, item.i)"
            >
              <button class="dashboard-grid-canvas__item-menu" type="button" aria-label="组件操作">
                <n-icon size="18">
                  <MoreOutlined />
                </n-icon>
              </button>
            </n-dropdown>
          </div>
          <WidgetRenderer :component="componentById(item.i)" />
        </div>
      </GridItem>
    </GridLayout>
  </div>
</template>

<script lang="ts" setup>
  import { ref, watch } from 'vue';
  import { GridItem, GridLayout } from 'grid-layout-plus';
  import { MoreOutlined } from '@vicons/antd';
  import type { DashboardLayout, PageComponentConfig } from '@/api/pageDesigner';
  import WidgetRenderer from './WidgetRenderer.vue';

  interface GridCanvasItem {
    x: number;
    y: number;
    w: number;
    h: number;
    i: string;
  }

  const props = withDefaults(
    defineProps<{
      layout: DashboardLayout;
      components: PageComponentConfig[];
      selectedId?: string;
      readonly?: boolean;
    }>(),
    {
      selectedId: '',
      readonly: false,
    }
  );

  const emit = defineEmits<{
    (event: 'update:layout', value: DashboardLayout): void;
    (event: 'select', value: string): void;
    (event: 'configure', value: string): void;
    (event: 'duplicate', value: string): void;
    (event: 'remove', value: string): void;
  }>();

  const innerLayout = ref<GridCanvasItem[]>(toGridItems(props.layout));
  const componentActionOptions = [
    { label: '配置', key: 'configure' },
    { label: '复制', key: 'duplicate' },
    { type: 'divider', key: 'divider' },
    { label: '删除', key: 'remove' },
  ];

  watch(
    () => props.layout.items,
    () => {
      const nextItems = toGridItems(props.layout);
      if (layoutSignature(innerLayout.value) !== layoutSignature(nextItems)) {
        innerLayout.value = nextItems;
      }
    },
    { deep: true }
  );

  function componentById(id: string) {
    return props.components.find((component) => component.id === id) || { id, type: 'text_block', title: '未知组件', props: {} };
  }

  function emitLayoutChange(nextLayout: GridCanvasItem[]) {
    const normalizedLayout = {
      ...props.layout,
      items: nextLayout.map((item) => {
        const existing = props.layout.items.find((layoutItem) => layoutItem.id === item.i);
        return {
          id: String(item.i),
          type: existing?.type,
          x: Number(item.x || 0),
          y: Number(item.y || 0),
          w: Number(item.w || 1),
          h: Number(item.h || 1),
          props: existing?.props || {},
        };
      }),
    };

    if (layoutSignature(toGridItems(normalizedLayout)) !== layoutSignature(toGridItems(props.layout))) {
      emit('update:layout', normalizedLayout);
    }
  }

  function selectItem(id: string) {
    if (!props.readonly) {
      emit('select', id);
    }
  }

  function handleComponentAction(key: string | number, id: string) {
    if (key === 'configure') emit('configure', id);
    if (key === 'duplicate') emit('duplicate', id);
    if (key === 'remove') emit('remove', id);
  }

  function toGridItems(layout: DashboardLayout): GridCanvasItem[] {
    return (layout.items || []).map((item) => ({
      x: Number(item.x || 0),
      y: Number(item.y || 0),
      w: Number(item.w || 1),
      h: Number(item.h || 1),
      i: item.id,
    }));
  }

  function layoutSignature(items: GridCanvasItem[]) {
    return items.map((item) => `${item.i}:${item.x}:${item.y}:${item.w}:${item.h}`).join('|');
  }
</script>

<style lang="less" scoped>
  .dashboard-grid-canvas {
    min-height: 520px;
    padding: 12px;
    background:
      linear-gradient(#eef2f7 1px, transparent 1px),
      linear-gradient(90deg, #eef2f7 1px, transparent 1px),
      #f8fafc;
    background-size: 24px 24px;
    border: 1px solid #dbe3ee;
    border-radius: 6px;
  }

  .dashboard-grid-canvas__item {
    position: relative;
    height: 100%;
    cursor: pointer;

    &.is-selected {
      outline: 2px solid #14b8a6;
      outline-offset: 2px;
    }
  }

  .dashboard-grid-canvas__item-tools {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 3;
  }

  .dashboard-grid-canvas__item-menu {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    color: #334155;
    cursor: pointer;
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #dbe3ee;
    border-radius: 6px;
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);

    &:hover,
    &:focus-visible {
      color: #0f766e;
      border-color: #14b8a6;
      outline: none;
    }
  }

  .is-readonly {
    min-height: 0;
    background: transparent;
    border: 0;

    .dashboard-grid-canvas__item {
      cursor: default;
    }
  }
</style>
