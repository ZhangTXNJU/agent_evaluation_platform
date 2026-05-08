/**
 * 柱状图对比组件 (T047)
 * 使用ECharts分组柱状图展示多任务在各指标上的得分对比。
 */

import React from 'react';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { Empty } from 'antd';

echarts.use([
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer,
]);

interface BarCompareProps {
  metricNames: string[];
  scores: Array<{
    task_id: string;
    task_name: string;
    metric_scores: Record<string, number>;
    overall_score: number;
  }>;
}

const BarCompare: React.FC<BarCompareProps> = ({ metricNames, scores }) => {
  if (metricNames.length === 0 || scores.length === 0) {
    return <Empty description="无对比数据" />;
  }

  // 指标中文名映射
  const metricLabels: Record<string, string> = {
    success_rate: '任务成功率',
    tool_accuracy: '工具准确性',
    llm_judge: 'LLM推理评分',
    response_time: '响应时间',
  };

  const option: echarts.EChartsCoreOption = {
    title: {
      text: '多任务指标柱状图对比',
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: unknown) =>
        `${((value as number) * 100).toFixed(1)}%`,
    },
    legend: {
      data: scores.map((s) => s.task_name),
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: metricNames.map((n) => metricLabels[n] || n),
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: {
        formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
      },
    },
    series: scores.map((s) => ({
      name: s.task_name,
      type: 'bar',
      data: metricNames.map((n) => s.metric_scores[n] || 0),
      label: {
        show: true,
        position: 'top',
        formatter: (params: unknown) => {
          const val = (params as { value: number }).value;
          return `${(val * 100).toFixed(0)}%`;
        },
      },
    })),
  };

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      style={{ height: 400 }}
      notMerge
    />
  );
};

export default BarCompare;
