<template>
  <div class="page-widget" :class="`page-widget--${component.type}`">
    <div class="page-widget__head">
      <strong>{{ title }}</strong>
      <span>{{ definition.label }}</span>
    </div>
    <div class="page-widget__body">
      <template v-if="component.type === 'metric_card'">
        <div class="page-widget__metric">{{ metricData.value || component.props?.value || '0' }}</div>
        <div class="page-widget__trend">{{ metricData.trend || component.props?.trend || '0%' }}</div>
      </template>
      <template v-else-if="component.type === 'text_block'">
        <p>{{ component.props?.content || '输入说明内容' }}</p>
      </template>
      <template v-else-if="component.type === 'quick_link'">
        <n-button size="small" type="primary" ghost>{{ component.props?.text || '打开功能' }}</n-button>
      </template>
      <template v-else-if="component.type === 'data_table'">
        <div class="page-widget__table">
          <span v-for="row in tableRows" :key="row"></span>
        </div>
      </template>
      <template v-else-if="component.type === 'bar_chart'">
        <div class="page-widget__chart page-widget__chart--bar">
          <div v-for="(value, index) in chartValues" :key="index" class="page-widget__chart-item">
            <div class="page-widget__chart-plot" :style="{ '--bar-height': `${chartHeight(value)}%` }">
              <span class="page-widget__chart-value">{{ value }}</span>
              <span class="page-widget__chart-bar"></span>
            </div>
            <span class="page-widget__chart-label">{{ chartCategories[index] || `项${index + 1}` }}</span>
          </div>
        </div>
      </template>
      <template v-else-if="component.type === 'pie_chart'">
        <div class="page-widget__pie">
          <div class="page-widget__pie-graph" :style="{ '--pie-gradient': pieGradient }">
            <span>{{ chartTotal }}</span>
          </div>
          <div class="page-widget__pie-legend">
            <span v-for="segment in pieSegments" :key="segment.label">
              <i :style="{ background: segment.color }"></i>
              {{ segment.label }}
            </span>
          </div>
        </div>
      </template>
      <template v-else-if="component.type === 'line_chart'">
        <div class="page-widget__svg-chart">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="折线图">
            <polyline class="page-widget__line-fill" :points="lineFillPoints" />
            <polyline class="page-widget__line-path" :points="linePoints" />
            <circle
              v-for="point in linePointItems"
              :key="point.key"
              class="page-widget__line-dot"
              :cx="point.x"
              :cy="point.y"
              r="1.8"
            />
          </svg>
          <div class="page-widget__axis-labels">
            <span v-for="(label, index) in compactCategories" :key="`${label}-${index}`">{{ label }}</span>
          </div>
        </div>
      </template>
      <template v-else-if="component.type === 'stacked_area_chart'">
        <div class="page-widget__svg-chart">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="折叠面积图">
            <path
              v-for="area in stackedAreas"
              :key="area.name"
              class="page-widget__area-path"
              :d="area.path"
              :style="{ fill: area.color, stroke: area.color }"
            />
          </svg>
          <div class="page-widget__series-legend">
            <span v-for="area in stackedAreas" :key="area.name">
              <i :style="{ background: area.color }"></i>
              {{ area.name }}
            </span>
          </div>
        </div>
      </template>
      <template v-else-if="component.type === 'scatter_chart'">
        <div class="page-widget__scatter">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="散点图">
            <line v-for="line in gridLines" :key="`x-${line}`" class="page-widget__grid-line" :x1="line" y1="6" :x2="line" y2="92" />
            <line v-for="line in gridLines" :key="`y-${line}`" class="page-widget__grid-line" x1="6" :y1="line" x2="96" :y2="line" />
            <circle
              v-for="point in scatterPoints"
              :key="point.key"
              class="page-widget__scatter-dot"
              :cx="point.x"
              :cy="point.y"
              r="2.2"
            />
          </svg>
        </div>
      </template>
      <template v-else-if="component.type === 'radar_chart'">
        <div class="page-widget__radar">
          <svg viewBox="0 0 100 100" role="img" aria-label="雷达图">
            <polygon
              v-for="ring in radarRings"
              :key="ring.key"
              class="page-widget__radar-ring"
              :points="ring.points"
            />
            <line
              v-for="axis in radarAxes"
              :key="axis.key"
              class="page-widget__radar-axis"
              x1="50"
              y1="50"
              :x2="axis.x"
              :y2="axis.y"
            />
            <polygon class="page-widget__radar-area" :points="radarDataPoints" />
            <circle
              v-for="point in radarDataPointItems"
              :key="point.key"
              class="page-widget__radar-dot"
              :cx="point.x"
              :cy="point.y"
              r="2"
            />
            <text
              v-for="label in radarLabels"
              :key="label.key"
              class="page-widget__radar-label"
              :x="label.x"
              :y="label.y"
              :text-anchor="label.anchor"
              dominant-baseline="middle"
            >
              {{ label.text }}
            </text>
          </svg>
        </div>
      </template>
      <template v-else-if="component.type === 'gauge_chart'">
        <div class="page-widget__gauge">
          <svg viewBox="0 0 120 78" role="img" aria-label="进度仪表盘">
            <path class="page-widget__gauge-track" :d="gaugeArcPath" />
            <path class="page-widget__gauge-progress" :d="gaugeProgressPath" />
            <circle class="page-widget__gauge-center" cx="60" cy="60" r="3.5" />
            <line
              class="page-widget__gauge-pointer"
              x1="60"
              y1="60"
              :x2="gaugePointer.x"
              :y2="gaugePointer.y"
            />
          </svg>
          <div class="page-widget__gauge-value">
            <strong>{{ gaugeDisplayValue }}</strong>
            <span>{{ gaugeData.label }}</span>
          </div>
          <div class="page-widget__gauge-scale">
            <span>0{{ gaugeData.unit }}</span>
            <span>{{ gaugeData.max }}{{ gaugeData.unit }}</span>
          </div>
        </div>
      </template>
      <template v-else>
        <p>{{ component.props?.description || '组件预览' }}</p>
      </template>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import type { PageComponentConfig } from '@/api/pageDesigner';
  import { componentTitle, parseStaticWidgetData, widgetDefinition } from './widgets';

  const props = defineProps<{
    component: PageComponentConfig;
  }>();

  const definition = computed(() => widgetDefinition(props.component.type));
  const title = computed(() => componentTitle(props.component));
  const staticData = computed(() => parseStaticWidgetData(props.component));
  const metricData = computed(() => staticData.value || {});
  const chartSeries = computed(() => {
    const data = staticData.value as { series?: Array<{ name?: string; data?: unknown[] }> };
    return Array.isArray(data.series) ? data.series : [];
  });
  const chartValues = computed(() => {
    const values = chartSeries.value[0]?.data?.map((item) => (Array.isArray(item) ? Number(item[1] || 0) : Number(item || 0))) || [];
    return values.length ? values : [12, 18, 24, 31, 28, 36, 42];
  });
  const chartCategories = computed(() => {
    const data = staticData.value as { categories?: string[] };
    return Array.isArray(data.categories) ? data.categories.map((item) => String(item)) : [];
  });
  const compactCategories = computed(() => {
    const categories = chartCategories.value.length ? chartCategories.value : chartValues.value.map((_, index) => `项${index + 1}`);
    if (categories.length <= 5) return categories;
    return categories.filter((_, index) => index === 0 || index === categories.length - 1 || index % Math.ceil(categories.length / 4) === 0);
  });
  const tableRows = computed(() => {
    const data = staticData.value as { rows?: unknown[] };
    return Array.from({ length: Math.max(1, Math.min(data.rows?.length || Number(props.component.props?.rows) || 4, 8)) }, (_, index) => index);
  });
  const chartTotal = computed(() => chartValues.value.reduce((total, value) => total + Number(value || 0), 0));
  const chartColors = ['#2563eb', '#14b8a6', '#f97316', '#8b5cf6', '#0ea5e9', '#84cc16'];
  const pieSegments = computed(() =>
    chartValues.value.map((value, index) => ({
      label: chartCategories.value[index] || `项${index + 1}`,
      value,
      color: chartColors[index % chartColors.length],
    }))
  );
  const pieGradient = computed(() => {
    const total = Math.max(chartTotal.value, 1);
    let cursor = 0;
    return pieSegments.value
      .map((segment) => {
        const start = cursor;
        cursor += (Number(segment.value || 0) / total) * 100;
        return `${segment.color} ${start}% ${cursor}%`;
      })
      .join(', ');
  });
  const linePointItems = computed(() => normalizedLinePoints(chartValues.value));
  const linePoints = computed(() => linePointItems.value.map((point) => `${point.x},${point.y}`).join(' '));
  const lineFillPoints = computed(() => (linePoints.value ? `4,94 ${linePoints.value} 96,94` : ''));
  const stackedAreas = computed(() => {
    const series = chartSeries.value.length
      ? chartSeries.value
      : [{ name: '计数', data: chartValues.value }];
    const length = Math.max(...series.map((item) => item.data?.length || 0), 1);
    const totals = Array.from({ length }, (_, index) =>
      series.reduce((total, item) => total + Number(item.data?.[index] || 0), 0)
    );
    const max = Math.max(...totals, 1);
    const previous = Array.from({ length }, () => 0);

    return series.map((item, seriesIndex) => {
      const top = Array.from({ length }, (_, index) => {
        previous[index] += Number(item.data?.[index] || 0);
        return pointForValue(index, length, previous[index], max);
      });
      const base = Array.from({ length }, (_, index) => pointForValue(index, length, previous[index] - Number(item.data?.[index] || 0), max)).reverse();
      return {
        name: item.name || `系列 ${seriesIndex + 1}`,
        color: chartColors[seriesIndex % chartColors.length],
        path: `${toPath(top)} L ${base.map((point) => `${point.x} ${point.y}`).join(' L ')} Z`,
      };
    });
  });
  const scatterPoints = computed(() => {
    const data = chartSeries.value[0]?.data || [];
    const pairs = data
      .map((item) => (Array.isArray(item) ? [Number(item[0] || 0), Number(item[1] || 0)] : [0, Number(item || 0)]))
      .filter((pair) => pair.every((value) => Number.isFinite(value)));
    const safePairs = pairs.length ? pairs : [[12, 18], [18, 31], [24, 24], [31, 42], [36, 28], [42, 49]];
    const xs = safePairs.map((item) => item[0]);
    const ys = safePairs.map((item) => item[1]);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    return safePairs.map(([x, y], index) => ({
      key: `${x}-${y}-${index}`,
      x: scaleValue(x, minX, maxX, 8, 94),
      y: scaleValue(y, minY, maxY, 90, 8),
    }));
  });
  const radarMetrics = computed(() => {
    const labels = chartCategories.value.length
      ? chartCategories.value
      : ['响应速度', '稳定性', '转化率', '满意度', '覆盖率', '成本控制'];
    const values = chartValues.value.slice(0, labels.length);
    return labels.map((label, index) => ({
      label,
      value: Number(values[index] || 0),
    }));
  });
  const radarMax = computed(() => Math.max(...radarMetrics.value.map((item) => item.value), 100, 1));
  const radarAxes = computed(() =>
    radarMetrics.value.map((_, index) => ({
      key: `axis-${index}`,
      ...radarPoint(index, radarMetrics.value.length, 38),
    }))
  );
  const radarRings = computed(() =>
    [0.25, 0.5, 0.75, 1].map((ratio) => ({
      key: `ring-${ratio}`,
      points: radarMetrics.value.map((_, index) => toPointString(radarPoint(index, radarMetrics.value.length, 38 * ratio))).join(' '),
    }))
  );
  const radarDataPointItems = computed(() =>
    radarMetrics.value.map((item, index) => ({
      key: `${item.label}-${index}`,
      ...radarPoint(index, radarMetrics.value.length, (item.value / radarMax.value) * 38),
    }))
  );
  const radarDataPoints = computed(() => radarDataPointItems.value.map(toPointString).join(' '));
  const radarLabels = computed(() =>
    radarMetrics.value.map((item, index) => {
      const point = radarPoint(index, radarMetrics.value.length, 45);
      return {
        key: `${item.label}-${index}`,
        text: item.label,
        x: point.x,
        y: point.y,
        anchor: point.x < 44 ? 'end' : point.x > 56 ? 'start' : 'middle',
      };
    })
  );
  const gaugeData = computed(() => {
    const data = staticData.value as { value?: number; max?: number; unit?: string; label?: string; series?: Array<{ data?: number[] }> };
    const value = Number(data.value ?? data.series?.[0]?.data?.[0] ?? chartValues.value[0] ?? 0);
    const max = Math.max(Number(data.max || 100), 1);
    return {
      value: Math.max(0, Math.min(value, max)),
      max,
      unit: data.unit || '%',
      label: data.label || '完成率',
    };
  });
  const gaugeRatio = computed(() => gaugeData.value.value / gaugeData.value.max);
  const gaugeArcPath = computed(() => describeArc(60, 60, 44, 180, 360));
  const gaugeProgressPath = computed(() => describeArc(60, 60, 44, 180, 180 + gaugeRatio.value * 180));
  const gaugePointer = computed(() => polarToCartesian(60, 60, 34, 180 + gaugeRatio.value * 180));
  const gaugeDisplayValue = computed(() => `${Math.round(gaugeData.value.value)}${gaugeData.value.unit}`);
  const gridLines = [24, 42, 60, 78];

  function chartHeight(value: number) {
    const max = Math.max(...chartValues.value, 1);
    return Math.max(18, Math.round((Number(value || 0) / max) * 92));
  }

  function normalizedLinePoints(values: number[]) {
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    return values.map((value, index) => {
      const x = scaleValue(index, 0, Math.max(values.length - 1, 1), 4, 96);
      const y = scaleValue(value, min, max, 88, 8);
      return { key: `${index}-${value}`, x, y };
    });
  }

  function pointForValue(index: number, length: number, value: number, max: number) {
    return {
      x: scaleValue(index, 0, Math.max(length - 1, 1), 4, 96),
      y: scaleValue(value, 0, max, 92, 8),
    };
  }

  function scaleValue(value: number, min: number, max: number, start: number, end: number) {
    if (max === min) return (start + end) / 2;
    return start + ((value - min) / (max - min)) * (end - start);
  }

  function toPath(points: Array<{ x: number; y: number }>) {
    return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
  }

  function radarPoint(index: number, total: number, radius: number) {
    const angle = -Math.PI / 2 + (index / Math.max(total, 1)) * Math.PI * 2;
    return {
      x: 50 + Math.cos(angle) * radius,
      y: 50 + Math.sin(angle) * radius,
    };
  }

  function toPointString(point: { x: number; y: number }) {
    return `${point.x},${point.y}`;
  }

  function polarToCartesian(centerX: number, centerY: number, radius: number, angleInDegrees: number) {
    const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180;
    return {
      x: centerX + radius * Math.cos(angleInRadians),
      y: centerY + radius * Math.sin(angleInRadians),
    };
  }

  function describeArc(x: number, y: number, radius: number, startAngle: number, endAngle: number) {
    const start = polarToCartesian(x, y, radius, endAngle);
    const end = polarToCartesian(x, y, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';
    return ['M', start.x, start.y, 'A', radius, radius, 0, largeArcFlag, 0, end.x, end.y].join(' ');
  }
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
    align-items: stretch;
    gap: 8px;
    height: 100%;
    min-height: 0;
  }

  .page-widget__chart-item {
    display: grid;
    grid-template-rows: minmax(0, 1fr) 20px;
    flex: 1;
    min-width: 0;
    height: 100%;
    align-items: end;
  }

  .page-widget__chart-plot {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .page-widget__chart-value {
    position: absolute;
    bottom: calc(var(--bar-height) + 4px);
    left: 50%;
    transform: translateX(-50%);
    color: #1e3a8a;
    font-size: 12px;
    line-height: 18px;
    text-align: center;
    white-space: nowrap;
  }

  .page-widget__chart-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    height: var(--bar-height);
    width: 100%;
    min-width: 8px;
    background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%);
    border-radius: 3px 3px 0 0;
  }

  .page-widget__chart-label {
    display: block;
    align-self: end;
    min-width: 0;
    overflow: hidden;
    color: #64748b;
    font-size: 12px;
    line-height: 20px;
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .page-widget__svg-chart,
  .page-widget__scatter {
    display: grid;
    grid-template-rows: minmax(0, 1fr) auto;
    gap: 6px;
    height: 100%;
    min-height: 0;

    svg {
      width: 100%;
      height: 100%;
      min-height: 0;
      overflow: visible;
    }
  }

  .page-widget__line-path {
    fill: none;
    stroke: #2563eb;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 2.4;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__line-fill {
    fill: rgba(37, 99, 235, 0.1);
    stroke: none;
  }

  .page-widget__line-dot {
    fill: #fff;
    stroke: #2563eb;
    stroke-width: 1.8;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__axis-labels,
  .page-widget__series-legend,
  .page-widget__pie-legend {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-width: 0;
    color: #64748b;
    font-size: 12px;
    line-height: 18px;

    span {
      display: inline-flex;
      align-items: center;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .page-widget__series-legend,
  .page-widget__pie-legend {
    justify-content: center;
    flex-wrap: wrap;

    i {
      flex: 0 0 auto;
      width: 8px;
      height: 8px;
      margin-right: 4px;
      border-radius: 2px;
    }
  }

  .page-widget__area-path {
    fill-opacity: 0.28;
    stroke-opacity: 0.78;
    stroke-width: 1.4;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__grid-line {
    stroke: #dbe3ee;
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__scatter-dot {
    fill: #2563eb;
    stroke: #fff;
    stroke-width: 1.4;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__radar {
    height: 100%;
    min-height: 0;

    svg {
      width: 100%;
      height: 100%;
      min-height: 0;
    }
  }

  .page-widget__radar-ring {
    fill: none;
    stroke: #dbe3ee;
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__radar-axis {
    stroke: #e2e8f0;
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__radar-area {
    fill: rgba(37, 99, 235, 0.16);
    stroke: #2563eb;
    stroke-linejoin: round;
    stroke-width: 1.8;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__radar-dot {
    fill: #fff;
    stroke: #2563eb;
    stroke-width: 1.6;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__radar-label {
    fill: #64748b;
    font-size: 5px;
    font-weight: 600;
  }

  .page-widget__gauge {
    display: grid;
    grid-template-rows: minmax(0, 1fr) auto auto;
    gap: 4px;
    height: 100%;
    min-height: 0;
    place-items: center;

    svg {
      width: min(100%, 220px);
      height: 100%;
      min-height: 0;
      overflow: visible;
    }
  }

  .page-widget__gauge-track,
  .page-widget__gauge-progress {
    fill: none;
    stroke-linecap: round;
    stroke-width: 10;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__gauge-track {
    stroke: #e2e8f0;
  }

  .page-widget__gauge-progress {
    stroke: #2563eb;
  }

  .page-widget__gauge-pointer {
    stroke: #0f172a;
    stroke-linecap: round;
    stroke-width: 2;
    vector-effect: non-scaling-stroke;
  }

  .page-widget__gauge-center {
    fill: #0f172a;
  }

  .page-widget__gauge-value {
    display: grid;
    gap: 2px;
    margin-top: -8px;
    text-align: center;

    strong {
      color: #0f172a;
      font-size: 24px;
      font-weight: 750;
      line-height: 1;
    }

    span {
      color: #64748b;
      font-size: 12px;
      line-height: 16px;
    }
  }

  .page-widget__gauge-scale {
    display: flex;
    justify-content: space-between;
    width: min(100%, 196px);
    color: #94a3b8;
    font-size: 11px;
    line-height: 16px;
  }

  .page-widget__pie {
    display: grid;
    grid-template-columns: minmax(112px, 0.76fr) minmax(0, 1fr);
    align-items: center;
    gap: 14px;
    height: 100%;
    min-height: 0;
  }

  .page-widget__pie-graph {
    display: grid;
    place-items: center;
    width: min(100%, 178px);
    aspect-ratio: 1;
    justify-self: center;
    background: conic-gradient(var(--pie-gradient, #2563eb 0% 100%));
    border-radius: 50%;
    box-shadow: inset 0 0 0 16px #fff;

    span {
      color: #0f172a;
      font-size: 18px;
      font-weight: 700;
      line-height: 1;
    }
  }

  .page-widget__pie-legend {
    display: grid;
    justify-content: stretch;
    gap: 6px;
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
