/**
 * 指标选择器组件 (T037)
 * 提供多选Checkbox组供用户选择评估指标，带中文描述。
 */

import React from 'react';
import { Checkbox, Space, Typography, Card } from 'antd';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';

const { Text } = Typography;

// 可用的评估指标列表
const AVAILABLE_METRICS = [
  {
    key: 'success_rate',
    label: '任务成功率',
    description: '检查Agent输出是否满足目的地、天数、预算、关键词等约束条件',
  },
  {
    key: 'tool_accuracy',
    label: '工具调用准确性',
    description: '对比Agent实际调用的工具序列与预期序列的匹配程度',
  },
  {
    key: 'llm_judge',
    label: 'LLM推理评分',
    description: '使用LLM评估Agent思考链的计划合理性、工具选择和自我修正能力',
  },
  {
    key: 'response_time',
    label: '响应时间',
    description: '衡量Agent处理单个测试用例的执行效率（≤30秒满分）',
  },
  {
    key: 'dialogue_quality',
    label: '对话质量',
    description: '使用LLM评估多轮对话的目标达成度、回复相关性、信息充分性和用户体验',
  },
  {
    key: 'task_completion',
    label: '任务完成度',
    description: '评估多轮对话中Agent是否成功完成了用户的目标(二元: 完成/未完成)',
  },
  {
    key: 'conversation_efficiency',
    label: '对话效率',
    description: '评估完成目标所需的对话轮次是否高效(实际轮次 vs 预期轮次)',
  },
];

interface MetricsSelectorProps {
  value?: string[];
  onChange?: (selected: string[]) => void;
  disabled?: boolean;
}

const MetricsSelector: React.FC<MetricsSelectorProps> = ({
  value = [],
  onChange,
  disabled = false,
}) => {
  const handleChange = (checkedValues: string[]) => {
    onChange?.(checkedValues);
  };

  return (
    <div>
      <Checkbox.Group
        value={value}
        onChange={handleChange}
        disabled={disabled}
        style={{ width: '100%' }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {AVAILABLE_METRICS.map((metric) => (
            <Card
              key={metric.key}
              size="small"
              hoverable
              style={{
                border:
                  value.includes(metric.key)
                    ? '1px solid #1677ff'
                    : undefined,
              }}
            >
              <Checkbox value={metric.key}>
                <Text strong>{metric.label}</Text>
              </Checkbox>
              <br />
              <Text type="secondary" style={{ fontSize: 12, marginLeft: 24 }}>
                {metric.description}
              </Text>
            </Card>
          ))}
        </Space>
      </Checkbox.Group>
      {value.length === 0 && (
        <Text type="danger" style={{ fontSize: 12 }}>
          * 请至少选择一项评估指标
        </Text>
      )}
    </div>
  );
};

export default MetricsSelector;
export { AVAILABLE_METRICS };
