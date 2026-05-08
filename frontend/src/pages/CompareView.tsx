/**
 * 多任务对比页面 (T048)
 * 选择2+已完成任务，展示雷达图、柱状图和汇总表格。
 */

import React, { useEffect, useState } from 'react';
import {
  Card,
  Select,
  Button,
  Table,
  Typography,
  Empty,
  Space,
  message,
  Spin,
} from 'antd';
import {
  BarChartOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { taskApi, compareApi } from '../services/api';
import RadarCompare from '../components/RadarCompare';
import BarCompare from '../components/BarCompare';
import StatusBadge from '../components/StatusBadge';
import type { TaskSummary, CompareResponse } from '../types';

const { Title, Text } = Typography;

const CompareView: React.FC = () => {
  const [allTasks, setAllTasks] = useState<TaskSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [compareData, setCompareData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [comparing, setComparing] = useState(false);

  // ── 加载已完成任务列表 ──
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        // 加载所有已完成/失败的任务
        const [doneData, failedData] = await Promise.all([
          taskApi.list(1, 100, 'done'),
          taskApi.list(1, 100, 'failed'),
        ]);
        const available = [...doneData.items, ...failedData.items];
        setAllTasks(available);
      } catch (err) {
        message.error('加载任务列表失败');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // ── 执行对比 ──
  const handleCompare = async () => {
    if (selectedIds.length < 2) {
      message.warning('请至少选择2个任务');
      return;
    }
    setComparing(true);
    try {
      const data = await compareApi.compare({ task_ids: selectedIds });
      setCompareData(data);
    } catch (err) {
      message.error('对比失败: ' + (err as Error).message);
    } finally {
      setComparing(false);
    }
  };

  const metricNames = (compareData?.metrics_comparison?.metric_names as string[]) || [];
  const scores = (compareData?.metrics_comparison?.scores as CompareResponse['metrics_comparison']['scores']) || [];

  // ── 汇总表格列定义 ──
  const summaryColumns = [
    { title: '任务名称', dataIndex: 'task_name', key: 'task_name' },
    ...metricNames.map((name) => ({
      title: name,
      key: name,
      render: (_: unknown, record: { metric_scores: Record<string, number> }) => {
        const s = record.metric_scores[name];
        return s !== undefined ? `${(s * 100).toFixed(0)}%` : '-';
      },
    })),
    {
      title: '综合得分',
      key: 'overall',
      render: (_: unknown, record: { overall_score: number }) =>
        `${(record.overall_score * 100).toFixed(1)}%`,
    },
  ];

  return (
    <div>
      <Title level={4}>
        <BarChartOutlined /> 多任务对比分析
      </Title>

      {/* 任务选择器 */}
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>选择要对比的任务（至少2个）：</Text>
          </div>
          <Select
            mode="multiple"
            placeholder="搜索并选择已完成的任务..."
            value={selectedIds}
            onChange={setSelectedIds}
            style={{ minWidth: 500, maxWidth: '100%' }}
            loading={loading}
            options={allTasks.map((t) => ({
              value: t.id,
              label: `${t.name} (${t.agent_version}) - ${t.dataset_name}`,
            }))}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
            }
          />
          <Button
            type="primary"
            icon={<SwapOutlined />}
            onClick={handleCompare}
            loading={comparing}
            disabled={selectedIds.length < 2}
          >
            开始对比 ({selectedIds.length}个任务)
          </Button>
        </Space>
      </Card>

      {/* 对比结果 */}
      {comparing ? (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" tip="加载对比数据..." />
        </div>
      ) : compareData ? (
        <>
          {/* 雷达图 */}
          <Card style={{ marginBottom: 16 }}>
            <RadarCompare metricNames={metricNames} scores={scores} />
          </Card>

          {/* 柱状图 */}
          <Card style={{ marginBottom: 16 }}>
            <BarCompare metricNames={metricNames} scores={scores} />
          </Card>

          {/* 汇总表格 */}
          <Card title="分数汇总表">
            <Table
              dataSource={scores}
              rowKey="task_id"
              columns={summaryColumns}
              pagination={false}
              size="small"
            />
          </Card>
        </>
      ) : (
        <Card>
          <Empty
            description={
              <span>
                请选择至少2个<Text type="success">已完成</Text>的任务，然后点击"开始对比"
              </span>
            }
          />
        </Card>
      )}
    </div>
  );
};

export default CompareView;
