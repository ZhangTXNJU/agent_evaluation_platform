/**
 * 任务详情页面 (T041)
 * 展示任务的完整信息：基本信息、评分卡片、各指标面板、执行追踪回放。
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Collapse,
  Table,
  Typography,
  Button,
  Spin,
  message,
  Space,
  Tag,
  Empty,
  Divider,
} from 'antd';
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons';
import { taskApi, resultApi } from '../services/api';
import ScoreCard from '../components/ScoreCard';
import TraceTimeline from '../components/TraceTimeline';
import StatusBadge from '../components/StatusBadge';
import { useTaskProgress } from '../services/websocket';
import type { TaskDetail as TaskDetailType, CaseResult, TraceEvent } from '../types';

const { Title, Text, Paragraph } = Typography;

const TaskDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [task, setTask] = useState<TaskDetailType | null>(null);
  const [loading, setLoading] = useState(true);

  // WebSocket实时进度更新
  const { close: closeWs } = useTaskProgress(
    id,
    (current, total) => {
      setTask((prev) =>
        prev ? { ...prev, progress_current: current, progress_total: total } : prev
      );
    },
    (status) => {
      setTask((prev) => (prev ? { ...prev, status: status as TaskDetailType['status'] } : prev));
    }
  );

  // ── 加载任务详情 ──
  const loadTask = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await taskApi.get(id);
      setTask(data);
    } catch (err) {
      message.error('加载任务详情失败: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTask();
    return () => closeWs();
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!task) {
    return <Empty description="任务未找到" />;
  }

  const result = task.result;
  const caseResults: CaseResult[] = result?.case_results || [];

  // ── 成功/失败/错误统计 ──
  const statusCounts = {
    passed: caseResults.filter((c) => c.status === 'passed').length,
    failed: caseResults.filter((c) => c.status === 'failed').length,
    error: caseResults.filter((c) => c.status === 'error').length,
  };

  return (
    <div>
      {/* 顶部返回栏 */}
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
            返回列表
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadTask}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 任务基本信息 */}
      <Card title="任务信息" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={{ xs: 1, sm: 2, lg: 3 }} size="small">
          <Descriptions.Item label="任务名称">{task.name}</Descriptions.Item>
          <Descriptions.Item label="Agent版本">
            <Tag>{task.agent_version}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="数据集">{task.dataset_name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <StatusBadge status={task.status} />
          </Descriptions.Item>
          <Descriptions.Item label="进度">
            {task.progress_current}/{task.progress_total}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(task.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="评估指标" span={3}>
            {task.metrics?.map((m) => (
              <Tag key={m} color="blue">
                {m}
              </Tag>
            ))}
          </Descriptions.Item>
          {task.error_message && (
            <Descriptions.Item label="错误信息" span={3}>
              <Text type="danger">{task.error_message}</Text>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* 结果区域（仅已完成/失败的任务展示） */}
      {(task.status === 'done' || task.status === 'failed') && result && (
        <>
          {/* 评分卡片 */}
          <div style={{ marginBottom: 16 }}>
            <ScoreCard
              overallScore={result.overall_score}
              metricScores={result.metric_scores}
              executionTime={result.execution_time_seconds}
            />
          </div>

          {/* 用例状态统计 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space size="large">
              <span>
                <Tag color="success">通过</Tag> {statusCounts.passed}
              </span>
              <span>
                <Tag color="error">失败</Tag> {statusCounts.failed}
              </span>
              <span>
                <Tag color="warning">错误</Tag> {statusCounts.error}
              </span>
              <span>总计: {caseResults.length}</span>
            </Space>
          </Card>

          {/* 指标详情面板 */}
          <Card title="指标详细分析" style={{ marginBottom: 16 }}>
            <Collapse
              items={(task.metrics || []).map((metricName) => {
                const metricMeta: Record<string, string> = {
                  success_rate: '任务成功率',
                  tool_accuracy: '工具调用准确性',
                  llm_judge: 'LLM推理评分',
                  response_time: '响应时间',
                };

                return {
                  key: metricName,
                  label: (
                    <Space>
                      <Text strong>{metricMeta[metricName] || metricName}</Text>
                      <Tag>
                        {((result.metric_scores[metricName] || 0) * 100).toFixed(0)}分
                      </Tag>
                    </Space>
                  ),
                  children: (
                    <MetricDetailPanel
                      metricName={metricName}
                      caseResults={caseResults}
                    />
                  ),
                };
              })}
            />
          </Card>

          {/* 执行追踪回放 */}
          <Card title="Agent执行追踪回放" style={{ marginBottom: 16 }}>
            <TraceTimeline
              traces={caseResults.map((c) => c.agent_trace || [])}
              caseIds={caseResults.map((c) => c.case_id)}
            />
          </Card>
        </>
      )}

      {/* 未完成的状态提示 */}
      {task.status === 'pending' && (
        <Card>
          <Empty description={'任务尚未执行，请返回列表页点击"执行"按钮'} />
        </Card>
      )}
      {task.status === 'running' && (
        <Card>
          <Spin tip="任务执行中，请稍候...">
            <div style={{ padding: 50, textAlign: 'center' }}>
              <p>
                当前进度: {task.progress_current}/{task.progress_total}
              </p>
            </div>
          </Spin>
        </Card>
      )}
    </div>
  );
};

// ── 指标详情面板子组件 ──
const MetricDetailPanel: React.FC<{
  metricName: string;
  caseResults: CaseResult[];
}> = ({ metricName, caseResults }) => {
  if (metricName === 'success_rate') {
    return (
      <Table
        dataSource={caseResults}
        rowKey="case_id"
        size="small"
        pagination={false}
        columns={[
          { title: '用例ID', dataIndex: 'case_id', key: 'case_id' },
          {
            title: '得分',
            key: 'score',
            render: (_, r) => {
              const score = r.metric_scores[metricName];
              const pct = score !== undefined ? `${(score * 100).toFixed(0)}%` : '-';
              return (
                <Tag color={score && score >= 0.8 ? 'success' : 'error'}>
                  {pct}
                </Tag>
              );
            },
          },
          {
            title: '约束检查详情',
            key: 'details',
            render: (_, r) => {
              const details = r.metric_details[metricName] as Record<string, unknown> | undefined;
              if (!details) return '-';
              const checks = details.checks as Record<string, number> | undefined;
              if (!checks) return JSON.stringify(details);
              return (
                <Space wrap>
                  {Object.entries(checks).map(([k, v]) => (
                    <Tag key={k} color={v >= 1 ? 'success' : 'error'}>
                      {k}: {v >= 1 ? '✓' : '✗'}
                    </Tag>
                  ))}
                </Space>
              );
            },
          },
        ]}
      />
    );
  }

  if (metricName === 'tool_accuracy') {
    return (
      <Table
        dataSource={caseResults}
        rowKey="case_id"
        size="small"
        pagination={false}
        columns={[
          { title: '用例ID', dataIndex: 'case_id', key: 'case_id' },
          {
            title: '得分',
            key: 'score',
            render: (_, r) => {
              const score = r.metric_scores[metricName];
              return score !== undefined ? `${(score * 100).toFixed(0)}%` : '-';
            },
          },
          {
            title: '预期序列',
            key: 'expected',
            render: (_, r) => {
              const d = r.metric_details[metricName] as Record<string, unknown> | undefined;
              const seq = d?.expected_sequence as string[] | undefined;
              return seq ? seq.join(' → ') : '-';
            },
          },
          {
            title: '实际序列',
            key: 'actual',
            render: (_, r) => {
              const d = r.metric_details[metricName] as Record<string, unknown> | undefined;
              const seq = d?.actual_sequence as string[] | undefined;
              return seq ? seq.join(' → ') : '-';
            },
          },
        ]}
      />
    );
  }

  if (metricName === 'llm_judge') {
    return (
      <Table
        dataSource={caseResults}
        rowKey="case_id"
        size="small"
        pagination={false}
        columns={[
          { title: '用例ID', dataIndex: 'case_id', key: 'case_id' },
          {
            title: '综合分',
            key: 'score',
            render: (_, r) => {
              const score = r.metric_scores[metricName];
              return score !== undefined ? `${(score * 100).toFixed(0)}%` : '-';
            },
          },
          {
            title: 'LLM评语',
            key: 'comment',
            ellipsis: true,
            render: (_, r) => {
              const d = r.metric_details[metricName] as Record<string, unknown> | undefined;
              return (d?.comment as string) || '-';
            },
          },
        ]}
      />
    );
  }

  if (metricName === 'response_time') {
    return (
      <Table
        dataSource={caseResults}
        rowKey="case_id"
        size="small"
        pagination={false}
        columns={[
          { title: '用例ID', dataIndex: 'case_id', key: 'case_id' },
          {
            title: '得分',
            key: 'score',
            render: (_, r) => {
              const score = r.metric_scores[metricName];
              return score !== undefined ? `${(score * 100).toFixed(0)}%` : '-';
            },
          },
          {
            title: '耗时',
            key: 'elapsed',
            render: (_, r) => {
              const d = r.metric_details[metricName] as Record<string, unknown> | undefined;
              const elapsed = d?.elapsed_seconds as number | undefined;
              return elapsed !== undefined ? `${elapsed.toFixed(2)}s` : '-';
            },
          },
        ]}
      />
    );
  }

  return <pre>{JSON.stringify(caseResults, null, 2)}</pre>;
};

export default TaskDetailPage;
