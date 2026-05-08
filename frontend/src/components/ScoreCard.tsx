/**
 * 评分卡片组件 (T040)
 * 展示评估任务的综合得分和各指标分数，带彩色进度条。
 */

import React from 'react';
import { Card, Progress, Row, Col, Typography, Space, Statistic } from 'antd';
import {
  TrophyOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ToolOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

// 指标对应的图标和颜色
const METRIC_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  success_rate: {
    icon: <CheckCircleOutlined />,
    color: '#52c41a',
    label: '任务成功率',
  },
  tool_accuracy: {
    icon: <ToolOutlined />,
    color: '#1677ff',
    label: '工具准确性',
  },
  llm_judge: {
    icon: <RobotOutlined />,
    color: '#722ed1',
    label: 'LLM推理评分',
  },
  response_time: {
    icon: <ThunderboltOutlined />,
    color: '#fa8c16',
    label: '响应时间',
  },
};

interface ScoreCardProps {
  overallScore: number;
  metricScores: Record<string, number>;
  executionTime?: number;
}

const ScoreCard: React.FC<ScoreCardProps> = ({
  overallScore,
  metricScores,
  executionTime,
}) => {
  // 总分百分比
  const overallPercent = Math.round(overallScore * 100);

  // 总分颜色
  const getOverallColor = (score: number) => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#1677ff';
    if (score >= 0.4) return '#fa8c16';
    return '#ff4d4f';
  };

  return (
    <Card>
      {/* 总分区域 */}
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <TrophyOutlined
          style={{ fontSize: 32, color: getOverallColor(overallScore) }}
        />
        <Title level={2} style={{ margin: '8px 0' }}>
          {(overallScore * 100).toFixed(1)}
          <Text type="secondary" style={{ fontSize: 16 }}>
            /100
          </Text>
        </Title>
        <Progress
          percent={overallPercent}
          strokeColor={getOverallColor(overallScore)}
          showInfo={false}
          style={{ maxWidth: 300, margin: '0 auto' }}
        />
        <Text type="secondary">综合加权得分</Text>
        {executionTime !== undefined && (
          <div style={{ marginTop: 8 }}>
            <ClockCircleOutlined />{' '}
            <Text type="secondary">
              执行耗时: {executionTime.toFixed(1)}s
            </Text>
          </div>
        )}
      </div>

      {/* 各指标分数 */}
      <Row gutter={[16, 16]}>
        {Object.entries(metricScores).map(([name, score]) => {
          const meta = METRIC_META[name] || {
            icon: null,
            color: '#999',
            label: name,
          };
          const percent = Math.round(score * 100);

          return (
            <Col key={name} xs={24} sm={12} lg={6}>
              <Card size="small" bordered>
                <div style={{ textAlign: 'center' }}>
                  <Space>
                    <span style={{ color: meta.color, fontSize: 18 }}>
                      {meta.icon}
                    </span>
                    <Text strong>{meta.label}</Text>
                  </Space>
                  <div style={{ marginTop: 8 }}>
                    <Statistic
                      value={percent}
                      suffix="分"
                      valueStyle={{
                        fontSize: 28,
                        color: meta.color,
                      }}
                    />
                  </div>
                  <Progress
                    percent={percent}
                    strokeColor={meta.color}
                    showInfo={false}
                    size="small"
                  />
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>
    </Card>
  );
};

export default ScoreCard;
