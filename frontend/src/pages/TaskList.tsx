/**
 * 任务列表页面 (T034)
 * 展示所有评估任务，支持执行/查看/删除/重跑操作，状态筛选和分页。
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Space,
  message,
  Popconfirm,
  Select,
  Tag,
  Card,
  Typography,
} from 'antd';
import {
  PlayCircleOutlined,
  EyeOutlined,
  DeleteOutlined,
  ReloadOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { taskApi } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import type { TaskSummary, TaskStatus } from '../types';

const { Title } = Typography;

const TaskList: React.FC = () => {
  const navigate = useNavigate();

  // ── 状态 ──
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  // ── 加载任务列表 ──
  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await taskApi.list(page, pageSize, statusFilter);
      setTasks(data.items);
      setTotal(data.total);
    } catch (err) {
      message.error('加载任务列表失败: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  // ── 自动轮询: 列表里有 pending/running 状态时,每 3 秒刷新一次 ──
  // 用 useEffect 监听 tasks 变化,只在需要时启动定时器,避免无谓开销
  useEffect(() => {
    const hasActiveTask = tasks.some(
      (t) => t.status === 'pending' || t.status === 'running'
    );
    if (!hasActiveTask) return;

    const timer = setInterval(() => {
      loadTasks();
    }, 3000);
    return () => clearInterval(timer);
  }, [tasks, loadTasks]);

  // ── 执行任务 ──
  const handleExecute = async (id: string) => {
    try {
      await taskApi.execute(id);
      message.success('任务已提交执行');
      loadTasks();
    } catch (err) {
      message.error('执行失败: ' + (err as Error).message);
    }
  };

  // ── 重跑任务 ──
  const handleRerun = async (task: TaskSummary) => {
    try {
      // 重跑：用相同配置创建新任务
      await taskApi.create({
        name: `${task.name} (重跑)`,
        agent_version: task.agent_version,
        dataset_id: task.dataset_id,
        metrics: task.metrics,
        agent_endpoint: task.agent_endpoint,
      });
      message.success('重跑任务已创建');
      loadTasks();
    } catch (err) {
      message.error('重跑失败: ' + (err as Error).message);
    }
  };

  // ── 删除任务 ──
  const handleDelete = async (id: string) => {
    try {
      await taskApi.delete(id);
      message.success('任务已删除');
      loadTasks();
    } catch (err) {
      message.error('删除失败: ' + (err as Error).message);
    }
  };

  // ── 分页变化 ──
  const handlePageChange = (p: number, s: number) => {
    setPage(p);
    setPageSize(s);
  };

  // ── 表格列定义 ──
  const columns: ColumnsType<TaskSummary> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: 200,
    },
    {
      title: 'Agent版本',
      dataIndex: 'agent_version',
      key: 'agent_version',
      width: 110,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '数据集',
      dataIndex: 'dataset_name',
      key: 'dataset_name',
      width: 160,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: TaskStatus) => <StatusBadge status={status} />,
    },
    {
      title: '进度',
      key: 'progress',
      width: 90,
      align: 'center',
      render: (_, record) => (
        <span>
          {record.progress_current}/{record.progress_total}
        </span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_, record) => (
        <Space size="small">
          {/* 执行：draft / pending / failed 都允许点 */}
          {(record.status === 'draft' ||
            record.status === 'pending' ||
            record.status === 'failed') && (
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record.id)}
            >
              执行
            </Button>
          )}
          {/* 重跑：done/failed可重跑 */}
          {(record.status === 'done' || record.status === 'failed') && (
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRerun(record)}
            >
              重跑
            </Button>
          )}
          {/* 查看详情 */}
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/tasks/${record.id}`)}
          >
            查看
          </Button>
          {/* 删除：非running可删除 */}
          {record.status !== 'running' && (
            <Popconfirm
              title="确定删除此任务？"
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* ── 顶部操作栏 ── */}
      <Card style={{ marginBottom: 16 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <Title level={4} style={{ margin: 0 }}>
            评估任务列表
          </Title>
          <Space>
            <Select
              allowClear
              placeholder="按状态筛选"
              style={{ width: 130 }}
              value={statusFilter}
              onChange={(val) => {
                setStatusFilter(val);
                setPage(1);
              }}
              options={[
                { value: 'pending', label: '待执行' },
                { value: 'running', label: '运行中' },
                { value: 'done', label: '已完成' },
                { value: 'failed', label: '失败' },
              ]}
            />
            <Button icon={<ReloadOutlined />} onClick={loadTasks}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/tasks/new')}
            >
              创建任务
            </Button>
          </Space>
        </div>
      </Card>

      {/* ── 任务表格 ── */}
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: pageSize,
          total: total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 个任务`,
          onChange: handlePageChange,
        }}
        locale={{
          emptyText: (
            <div style={{ padding: 40 }}>
              <p style={{ fontSize: 16, color: '#999' }}>暂无评估任务</p>
              <p style={{ color: '#bbb' }}>
                请先上传数据集，然后创建并执行评估任务
              </p>
            </div>
          ),
        }}
      />
    </div>
  );
};

export default TaskList;
