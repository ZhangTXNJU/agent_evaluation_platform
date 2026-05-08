/**
 * 雷达图对比组件 (T046)
 * 使用ECharts雷达图展示多任务在各项指标上的得分对比。
 */

import React from 'react';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { RadarChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { Empty } from 'antd';

// 按需注册ECharts组件
echarts.use([
  RadarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
]);

interface RadarCompareProps {
  metricNames: string[];
  scores: Array<{
    task_id: string;
    task_name: string;
    metric_scores: Record<string, number>;
    overall_score: number;
  }>;
}

const RadarCompare: React.FC<RadarCompareProps> = ({ metricNames, scores }) => {
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
      text: '多任务指标雷达图',
      left: 'center',
    },
    tooltip: {
      trigger: 'item',
    },
    legend: {
      data: scores.map((s) => s.task_name),
      bottom: 0,
    },
    radar: {
      indicator: metricNames.map((name) => ({
        name: metricLabels[name] || name,
        max: 1.0,
      })),
      center: ['50%', '50%'],
      radius: '60%',
    },
    series: [
      {
        type: 'radar',
        data: scores.map((s) => ({
          name: s.task_name,
          value: metricNames.map((n) => s.metric_scores[n] || 0),
        })),
      },
    ],
  };

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      style={{ height: 450 }}
      notMerge
    />
  );
};

export default RadarCompare;
