/**
 * 执行追踪时间线组件 (T042)
 * 逐步展示Agent的思考→工具调用→观察事件流程。
 */

import React, { useState } from 'react';
import { Timeline, Tag, Collapse, Select, Empty, Typography } from 'antd';
import {
  BulbOutlined,
  ToolOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { TraceEvent } from '../types';

const { Text, Paragraph } = Typography;

interface TraceTimelineProps {
  traces: TraceEvent[][];  // 每个用例一个trace数组
  caseIds: string[];
}

// 事件类型配置
const EVENT_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  thought: { color: '#722ed1', icon: <BulbOutlined />, label: '思考' },
  tool_call: { color: '#1677ff', icon: <ToolOutlined />, label: '工具调用' },
  observation: { color: '#52c41a', icon: <EyeOutlined />, label: '观察结果' },
};

const TraceTimeline: React.FC<TraceTimelineProps> = ({ traces, caseIds }) => {
  const [selectedCaseIdx, setSelectedCaseIdx] = useState(0);

  const currentTrace = traces[selectedCaseIdx] || [];

  return (
    <div>
      {/* 用例选择器 */}
      <div style={{ marginBottom: 16 }}>
        <Text strong>选择测试用例：</Text>
        <Select
          value={selectedCaseIdx}
          onChange={setSelectedCaseIdx}
          style={{ width: 200, marginLeft: 12 }}
          options={caseIds.map((id, idx) => ({
            value: idx,
            label: `${id}${idx === 0 ? ' (默认)' : ''}`,
          }))}
        />
      </div>

      {/* 时间线 */}
      {currentTrace.length === 0 ? (
        <Empty description="该用例无执行追踪数据" />
      ) : (
        <Timeline>
          {currentTrace.map((event, idx) => {
            const config = EVENT_CONFIG[event.event_type] || {
              color: '#999',
              icon: null,
              label: event.event_type,
            };

            return (
              <Timeline.Item
                key={idx}
                color={config.color}
                dot={config.icon}
              >
                <Tag color={config.color}>{config.label}</Tag>
                {event.timestamp && (
                  <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                    {new Date(event.timestamp).toLocaleTimeString('zh-CN')}
                  </Text>
                )}
                {event.data && (
                  <Collapse
                    ghost
                    size="small"
                    items={[
                      {
                        key: 'detail',
                        label: '查看详情',
                        children: (
                          <pre
                            style={{
                              background: '#f5f5f5',
                              padding: 12,
                              borderRadius: 4,
                              fontSize: 12,
                              maxHeight: 300,
                              overflow: 'auto',
                            }}
                          >
                            {JSON.stringify(event.data, null, 2)}
                          </pre>
                        ),
                      },
                    ]}
                  />
                )}
              </Timeline.Item>
            );
          })}
        </Timeline>
      )}
    </div>
  );
};

export default TraceTimeline;
