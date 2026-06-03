<template>
  <div ref="chartRef" class="page-widget-echart"></div>
</template>

<script lang="ts" setup>
  import type { EChartsOption } from 'echarts';
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useElementSize } from '@vueuse/core';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { PageComponentConfig } from '@/api/pageDesigner';

  interface ChartSeriesItem {
    name?: string;
    data?: unknown[];
  }

  const props = defineProps<{
    component: PageComponentConfig;
    data: Record<string, unknown>;
  }>();

  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);
  const { width, height } = useElementSize(chartRef);

  const chartColors = computed(() => [
    cssVar('--app-primary-color', '#2d8cf0'),
    cssVar('--app-success-color', '#18a058'),
    cssVar('--app-warning-color', '#f0a020'),
    '#8b5cf6',
    cssVar('--app-info-color', '#2080f0'),
    '#84cc16',
  ]);
  const chartSeries = computed<ChartSeriesItem[]>(() => (Array.isArray(props.data.series) ? (props.data.series as ChartSeriesItem[]) : []));
  const chartCategories = computed(() =>
    Array.isArray(props.data.categories) ? (props.data.categories as unknown[]).map((item) => String(item)) : []
  );
  const chartValues = computed(() => {
    const values = chartSeries.value[0]?.data?.map((item) => (Array.isArray(item) ? Number(item[1] || 0) : Number(item || 0))) || [];
    return values.length ? values : [12, 18, 24, 31, 28, 36, 42];
  });
  const categories = computed(() =>
    chartCategories.value.length ? chartCategories.value : chartValues.value.map((_, index) => `项目 ${index + 1}`)
  );
  const option = computed(() => createChartOption(props.component.type));

  onMounted(() => {
    renderChart();
  });

  watch(
    option,
    () => {
      renderChart();
    },
    { deep: true }
  );

  watch([width, height], () => {
    nextTick(resize);
  });

  function renderChart() {
    setOptions(option.value);
  }

  function createChartOption(type: string): EChartsOption {
    if (type === 'bar_chart') return createBarOption();
    if (type === 'pie_chart') return createPieOption();
    if (type === 'stacked_area_chart') return createStackedAreaOption();
    if (type === 'scatter_chart') return createScatterOption();
    if (type === 'radar_chart') return createRadarOption();
    if (type === 'gauge_chart') return createGaugeOption();
    return createLineOption();
  }

  function cssVar(name: string, fallback: string) {
    const target = chartRef.value || document.documentElement;
    const value = getComputedStyle(target).getPropertyValue(name).trim();
    return value || fallback;
  }

  function textColor() {
    return cssVar('--app-text-color', '#111827');
  }

  function secondaryTextColor() {
    return cssVar('--app-icon-color', '#64748b');
  }

  function borderColor() {
    return cssVar('--app-border-color', '#dbe3ee');
  }

  function mutedSurfaceColor() {
    return cssVar('--app-surface-muted-bg', '#eef1f5');
  }

  function tooltipOption(trigger: 'axis' | 'item') {
    return {
      trigger,
      confine: true,
      backgroundColor: 'rgba(17, 24, 39, 0.92)',
      borderWidth: 0,
      padding: [8, 10],
      textStyle: {
        color: '#fff',
        fontSize: 12,
        lineHeight: 18,
      },
      extraCssText: 'border-radius: 4px; box-shadow: 0 8px 20px rgb(15 23 42 / 16%);',
    };
  }

  function axisLabelOption() {
    return {
      color: secondaryTextColor(),
      fontSize: 11,
      lineHeight: 16,
      margin: 7,
      hideOverlap: true,
    };
  }

  function baseGridOption(): EChartsOption {
    return {
      color: chartColors.value,
      animationDuration: 420,
      animationEasing: 'cubicOut',
      tooltip: tooltipOption('axis'),
      grid: {
        left: 2,
        right: 4,
        top: 8,
        bottom: 0,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: categories.value,
        boundaryGap: true,
        axisLine: { lineStyle: { color: borderColor() } },
        axisTick: { show: false },
        axisLabel: axisLabelOption(),
      },
      yAxis: {
        type: 'value',
        axisLabel: axisLabelOption(),
        splitLine: {
          lineStyle: {
            color: borderColor(),
            opacity: 0.58,
          },
        },
      },
    };
  }

  function createLineOption(): EChartsOption {
    return {
      ...baseGridOption(),
      xAxis: {
        ...(baseGridOption().xAxis as Record<string, unknown>),
        boundaryGap: false,
      },
      series: normalizedSeries().map((series, index) => ({
        name: series.name || `系列 ${index + 1}`,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        lineStyle: {
          width: 2.4,
        },
        areaStyle: {
          opacity: 0.1,
        },
        emphasis: {
          focus: 'series',
          scale: true,
        },
        data: series.data,
      })),
    };
  }

  function createBarOption(): EChartsOption {
    return {
      ...baseGridOption(),
      grid: {
        ...(baseGridOption().grid as Record<string, unknown>),
        top: 6,
      },
      series: normalizedSeries().map((series, index) => ({
        name: series.name || `系列 ${index + 1}`,
        type: 'bar',
        barMaxWidth: 42,
        barCategoryGap: '36%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
        },
        emphasis: {
          focus: 'series',
        },
        data: series.data,
      })),
    };
  }

  function createPieOption(): EChartsOption {
    const data = chartValues.value.map((value, index) => ({
      name: categories.value[index] || `项目 ${index + 1}`,
      value,
    }));
    return {
      color: chartColors.value,
      animationDuration: 420,
      tooltip: {
        ...tooltipOption('item'),
        formatter: '{b}<br/>{c} ({d}%)',
      },
      legend: {
        type: 'scroll',
        orient: 'vertical',
        right: 0,
        top: 'center',
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 10,
        textStyle: {
          color: secondaryTextColor(),
          fontSize: 12,
          lineHeight: 16,
        },
      },
      series: [
        {
          name: props.component.title || '占比',
          type: 'pie',
          radius: ['48%', '76%'],
          center: ['39%', '50%'],
          avoidLabelOverlap: true,
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 600,
              color: textColor(),
            },
          },
          itemStyle: {
            borderColor: cssVar('--app-surface-bg', '#fff'),
            borderWidth: 2,
          },
          data,
        },
      ],
    };
  }

  function createStackedAreaOption(): EChartsOption {
    return {
      ...baseGridOption(),
      xAxis: {
        ...(baseGridOption().xAxis as Record<string, unknown>),
        boundaryGap: false,
      },
      series: normalizedSeries().map((series, index) => ({
        name: series.name || `系列 ${index + 1}`,
        type: 'line',
        stack: 'total',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        lineStyle: {
          width: 2.2,
        },
        areaStyle: {
          opacity: 0.16,
        },
        emphasis: {
          focus: 'series',
        },
        data: series.data,
      })),
    };
  }

  function createScatterOption(): EChartsOption {
    const pairs = normalizedScatterData();
    return {
      color: chartColors.value,
      animationDuration: 420,
      tooltip: {
        ...tooltipOption('item'),
        formatter: (params) => {
          const value = Array.isArray(params.value) ? params.value : [];
          return `${params.seriesName}<br/>X：${value[0] ?? 0}<br/>Y：${value[1] ?? 0}`;
        },
      },
      grid: {
        left: 2,
        right: 6,
        top: 8,
        bottom: 0,
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: borderColor() } },
        axisTick: { show: false },
        axisLabel: axisLabelOption(),
        splitLine: {
          lineStyle: {
            color: borderColor(),
            opacity: 0.58,
          },
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: axisLabelOption(),
        splitLine: {
          lineStyle: {
            color: borderColor(),
            opacity: 0.58,
          },
        },
      },
      series: [
        {
          name: chartSeries.value[0]?.name || '样本分布',
          type: 'scatter',
          symbolSize: 10,
          data: pairs,
        },
      ],
    };
  }

  function createRadarOption(): EChartsOption {
    const metrics = radarMetrics();
    const max = Math.max(...metrics.map((item) => item.value), 100, 1);
    return {
      color: chartColors.value,
      animationDuration: 420,
      tooltip: tooltipOption('item'),
      radar: {
        center: ['50%', '50%'],
        radius: '72%',
        splitNumber: 4,
        indicator: metrics.map((item) => ({ name: item.label, max })),
        axisName: {
          color: secondaryTextColor(),
          fontSize: 11,
          fontWeight: 600,
        },
        axisLine: {
          lineStyle: {
            color: borderColor(),
          },
        },
        splitLine: {
          lineStyle: {
            color: borderColor(),
          },
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(45, 140, 240, 0.025)', 'rgba(45, 140, 240, 0.07)'],
          },
        },
      },
      series: [
        {
          name: chartSeries.value[0]?.name || '当前表现',
          type: 'radar',
          symbol: 'circle',
          symbolSize: 5,
          areaStyle: {
            opacity: 0.18,
          },
          lineStyle: {
            width: 2.2,
          },
          data: [
            {
              value: metrics.map((item) => item.value),
              name: chartSeries.value[0]?.name || '当前表现',
            },
          ],
        },
      ],
    };
  }

  function createGaugeOption(): EChartsOption {
    const value = gaugeValue();
    return {
      color: chartColors.value,
      animationDuration: 420,
      series: [
        {
          type: 'gauge',
          min: 0,
          max: value.max,
          radius: '104%',
          center: ['50%', '62%'],
          progress: {
            show: true,
            width: 12,
            roundCap: true,
            itemStyle: {
              color: chartColors.value[0],
            },
          },
          axisLine: {
            roundCap: true,
            lineStyle: {
              width: 12,
              color: [[1, mutedSurfaceColor()]],
            },
          },
          pointer: {
            width: 4,
            length: '54%',
            itemStyle: {
              color: textColor(),
            },
          },
          anchor: {
            show: true,
            size: 8,
            itemStyle: {
              color: textColor(),
            },
          },
          splitLine: {
            distance: -16,
            length: 8,
            lineStyle: {
              color: borderColor(),
              width: 1,
            },
          },
          axisTick: {
            show: false,
          },
          axisLabel: {
            color: secondaryTextColor(),
            fontSize: 10,
            distance: 13,
          },
          detail: {
            valueAnimation: true,
            formatter: `{value}${value.unit}`,
            color: textColor(),
            fontSize: 26,
            fontWeight: 700,
            offsetCenter: [0, '58%'],
          },
          title: {
            color: secondaryTextColor(),
            fontSize: 12,
            offsetCenter: [0, '78%'],
          },
          data: [
            {
              value: value.value,
              name: value.label,
            },
          ],
        },
      ],
    };
  }

  function normalizedSeries() {
    const series = chartSeries.value.length ? chartSeries.value : [{ name: '计数', data: chartValues.value }];
    return series.map((item) => ({
      name: item.name,
      data: Array.isArray(item.data)
        ? item.data.map((value) => (Array.isArray(value) ? Number(value[1] || 0) : Number(value || 0)))
        : chartValues.value,
    }));
  }

  function normalizedScatterData() {
    const data = chartSeries.value[0]?.data || [];
    const pairs = data
      .map((item) => (Array.isArray(item) ? [Number(item[0] || 0), Number(item[1] || 0)] : [0, Number(item || 0)]))
      .filter((pair) => pair.every((value) => Number.isFinite(value)));
    return pairs.length ? pairs : [[12, 18], [18, 31], [24, 24], [31, 42], [36, 28], [42, 49]];
  }

  function radarMetrics() {
    const labels = chartCategories.value.length ? chartCategories.value : ['响应速度', '稳定性', '转化率', '满意度', '覆盖率', '成本控制'];
    const values = chartValues.value.slice(0, labels.length);
    return labels.map((label, index) => ({
      label,
      value: Number(values[index] || 0),
    }));
  }

  function gaugeValue() {
    const data = props.data as { value?: number; max?: number; unit?: string; label?: string; series?: Array<{ data?: number[] }> };
    const rawValue = Number(data.value ?? data.series?.[0]?.data?.[0] ?? chartValues.value[0] ?? 0);
    const max = Math.max(Number(data.max || 100), 1);
    return {
      value: Math.max(0, Math.min(rawValue, max)),
      max,
      unit: data.unit || '%',
      label: data.label || '完成率',
    };
  }
</script>

<style lang="less" scoped>
  .page-widget-echart {
    width: 100%;
    height: 100%;
    min-height: 0;
  }
</style>
