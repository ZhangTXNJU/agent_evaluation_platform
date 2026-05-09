/**
 * 任务状态标签组件 (T035)
 * 根据任务状态显示不同颜色的Tag。
 */

import React from 'react';
import { Tag } from 'antd';
import type { TaskStatus } from '../types';

interface StatusBadgeProps {
  status: TaskStatus;
}

// 状态 → 颜色映射
const STATUS_CONFIG: Record<TaskStatus, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  pending: { color: 'gold', label: '排队中' },
  running: { color: 'processing', label: '运行中' },
  done: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
};

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const config = STATUS_CONFIG[status] || {
    color: 'default',
    label: status,
  };
  return <Tag color={config.color}>{config.label}</Tag>;
};

export default StatusBadge;
