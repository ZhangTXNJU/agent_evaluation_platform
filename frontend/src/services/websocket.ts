/**
 * WebSocket客户端Hook (T051)
 * 订阅指定任务的实时进度更新。
 */

import { useEffect, useRef, useCallback } from 'react';

// WebSocket基础URL
const WS_BASE = `ws://${window.location.host}/ws`;

interface ProgressData {
  task_id: string;
  progress_current: number;
  progress_total: number;
  status: string;
}

/**
 * 订阅任务进度推送的Hook
 *
 * @param taskId - 要订阅的任务ID（null/undefined时不连接）
 * @param onProgress - 进度更新回调
 * @param onStatusChange - 状态变更回调
 */
export function useTaskProgress(
  taskId: string | undefined | null,
  onProgress?: (current: number, total: number) => void,
  onStatusChange?: (status: string) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (!taskId) return;

    // 关闭已有连接
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE}/tasks/${taskId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data: ProgressData = JSON.parse(event.data);
        onProgress?.(data.progress_current, data.progress_total);
        onStatusChange?.(data.status);
      } catch {
        // 忽略解析失败的消息
      }
    };

    ws.onerror = () => {
      // 连接失败时静默处理
    };

    ws.onclose = () => {
      // 5秒后自动重连
      reconnectTimer.current = setTimeout(() => {
        connect();
      }, 5000);
    };
  }, [taskId, onProgress, onStatusChange]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    /** 手动关闭连接 */
    close: () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    },
  };
}

export default { useTaskProgress };
