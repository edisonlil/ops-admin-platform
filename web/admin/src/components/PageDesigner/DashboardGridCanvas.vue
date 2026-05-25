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
      @layout-updated="emitChange"
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
          <WidgetRenderer :component="componentById(item.i)" />
        </div>
      </GridItem>
    </GridLayout>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { GridItem, GridLayout } from 'grid-layout-plus';
  import type { DashboardLayout, PageComponentConfig } from '@/api/pageDesigner';
  import WidgetRenderer from './WidgetRenderer.vue';

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
  }>();

  const innerLayout = computed({
    get() {
      return (props.layout.items || []).map((item) => ({
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
        i: item.id,
      }));
    },
    set(value) {
      emit('update:layout', {
        ...props.layout,
        items: value.map((item) => {
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
      });
    },
  });

  function componentById(id: string) {
    return props.components.find((component) => component.id === id) || { id, type: 'text_block', title: '未知组件', props: {} };
  }

  function emitChange(nextLayout: Array<{ i: string; x: number; y: number; w: number; h: number }>) {
    innerLayout.value = nextLayout;
  }

  function selectItem(id: string) {
    if (!props.readonly) {
      emit('select', id);
    }
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
    height: 100%;
    cursor: pointer;

    &.is-selected {
      outline: 2px solid #2563eb;
      outline-offset: 2px;
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
