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

  const chartColors = ['#2563eb', '#14b8a6', '#f97316', '#8b5cf6', '#0ea5e9', '#84cc16'];
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

  function baseGridOption(): EChartsOption {
    return {
      color: chartColors,
      animationDuration: 420,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderWidth: 0,
        textStyle: {
          color: '#fff',
          fontSize: 12,
        },
      },
      grid: {
        left: 10,
        right: 12,
        top: 18,
        bottom: 6,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: categories.value,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#dbe3ee' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#64748b',
          fontSize: 11,
          hideOverlap: true,
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: '#64748b',
          fontSize: 11,
        },
        splitLine: {
          lineStyle: {
            color: '#e8eef6',
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
        symbolSize: 7,
        showSymbol: true,
        lineStyle: {
          width: 2.5,
        },
        areaStyle: {
          opacity: 0.14,
        },
        emphasis: {
          focus: 'series',
        },
        data: series.data,
      })),
    };
  }

  function createBarOption(): EChartsOption {
    return {
      ...baseGridOption(),
      series: normalizedSeries().map((series, index) => ({
        name: series.name || `系列 ${index + 1}`,
        type: 'bar',
        barMaxWidth: 34,
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
      color: chartColors,
      animationDuration: 420,
      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: '{b}<br/>{c} ({d}%)',
      },
      legend: {
        type: 'scroll',
        orient: 'vertical',
        right: 4,
        top: 'center',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: {
          color: '#64748b',
          fontSize: 11,
        },
      },
      series: [
        {
          name: props.component.title || '占比',
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['38%', '52%'],
          avoidLabelOverlap: true,
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 600,
            },
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
        lineStyle: {
          width: 2,
        },
        areaStyle: {
          opacity: 0.2,
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
      color: chartColors,
      animationDuration: 420,
      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: (params) => {
          const value = Array.isArray(params.value) ? params.value : [];
          return `${params.seriesName}<br/>X：${value[0] ?? 0}<br/>Y：${value[1] ?? 0}`;
        },
      },
      grid: {
        left: 12,
        right: 16,
        top: 18,
        bottom: 8,
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#dbe3ee' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#64748b',
          fontSize: 11,
        },
        splitLine: {
          lineStyle: {
            color: '#e8eef6',
          },
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: '#64748b',
          fontSize: 11,
        },
        splitLine: {
          lineStyle: {
            color: '#e8eef6',
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
      color: chartColors,
      animationDuration: 420,
      tooltip: {
        trigger: 'item',
        confine: true,
      },
      radar: {
        center: ['50%', '52%'],
        radius: '66%',
        splitNumber: 4,
        indicator: metrics.map((item) => ({ name: item.label, max })),
        axisName: {
          color: '#64748b',
          fontSize: 11,
          fontWeight: 600,
        },
        axisLine: {
          lineStyle: {
            color: '#dbe3ee',
          },
        },
        splitLine: {
          lineStyle: {
            color: '#dbe3ee',
          },
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(37, 99, 235, 0.03)', 'rgba(37, 99, 235, 0.07)'],
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
      color: chartColors,
      animationDuration: 420,
      series: [
        {
          type: 'gauge',
          min: 0,
          max: value.max,
          radius: '86%',
          center: ['50%', '58%'],
          progress: {
            show: true,
            width: 10,
            roundCap: true,
          },
          axisLine: {
            roundCap: true,
            lineStyle: {
              width: 10,
              color: [[1, '#e2e8f0']],
            },
          },
          pointer: {
            width: 4,
            length: '56%',
            itemStyle: {
              color: '#0f172a',
            },
          },
          anchor: {
            show: true,
            size: 8,
            itemStyle: {
              color: '#0f172a',
            },
          },
          splitLine: {
            distance: -14,
            length: 8,
            lineStyle: {
              color: '#cbd5e1',
              width: 1,
            },
          },
          axisTick: {
            show: false,
          },
          axisLabel: {
            color: '#64748b',
            fontSize: 10,
            distance: 14,
          },
          detail: {
            valueAnimation: true,
            formatter: `{value}${value.unit}`,
            color: '#0f172a',
            fontSize: 22,
            fontWeight: 700,
            offsetCenter: [0, '70%'],
          },
          title: {
            color: '#64748b',
            fontSize: 12,
            offsetCenter: [0, '92%'],
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
