<template>
  <div class="page-widget" :class="`page-widget--${component.type}`">
    <div class="page-widget__head">
      <strong>{{ title }}</strong>
      <span>{{ definition.label }}</span>
    </div>
    <div class="page-widget__body">
      <template v-if="component.type === 'metric_card'">
        <div class="page-widget__metric">{{ component.props?.value || '0' }}</div>
        <div class="page-widget__trend">{{ component.props?.trend || '0%' }}</div>
      </template>
      <template v-else-if="component.type === 'text_block'">
        <p>{{ component.props?.content || '输入说明内容' }}</p>
      </template>
      <template v-else-if="component.type === 'quick_link'">
        <n-button size="small" type="primary" ghost>{{ component.props?.text || '打开功能' }}</n-button>
      </template>
      <template v-else-if="component.type === 'data_table'">
        <div class="page-widget__table">
          <span v-for="index in 4" :key="index"></span>
        </div>
      </template>
      <template v-else>
        <div class="page-widget__chart">
          <span v-for="index in 7" :key="index" :style="{ height: `${28 + index * 7}%` }"></span>
        </div>
      </template>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import type { PageComponentConfig } from '@/api/pageDesigner';
  import { componentTitle, widgetDefinition } from './widgets';

  const props = defineProps<{
    component: PageComponentConfig;
  }>();

  const definition = computed(() => widgetDefinition(props.component.type));
  const title = computed(() => componentTitle(props.component));
</script>

<style lang="less" scoped>
  .page-widget {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
    overflow: hidden;
    background: var(--app-color-bg-container, #fff);
    border: 1px solid var(--app-border-color, #e5e7eb);
    border-radius: 6px;
  }

  .page-widget__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 40px;
    padding: 10px 12px 6px;

    strong {
      min-width: 0;
      overflow: hidden;
      font-size: 14px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      flex: 0 0 auto;
      color: #64748b;
      font-size: 12px;
    }
  }

  .page-widget__body {
    flex: 1;
    min-height: 0;
    padding: 8px 12px 12px;
  }

  .page-widget__metric {
    color: #0f172a;
    font-size: 30px;
    font-weight: 700;
    line-height: 1.1;
  }

  .page-widget__trend {
    margin-top: 8px;
    color: #047857;
    font-size: 13px;
  }

  .page-widget__chart {
    display: flex;
    align-items: end;
    gap: 8px;
    height: 100%;

    span {
      flex: 1;
      min-width: 8px;
      background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%);
      border-radius: 3px 3px 0 0;
    }
  }

  .page-widget__table {
    display: grid;
    gap: 8px;

    span {
      height: 14px;
      background: #e2e8f0;
      border-radius: 3px;
    }
  }

  p {
    margin: 0;
    color: #475569;
    line-height: 1.7;
  }
</style>
