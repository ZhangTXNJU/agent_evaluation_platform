"""
WebSocket连接管理器 (T050)
管理WebSocket连接，支持向特定任务的订阅者推送进度更新。

使用方式:
    manager = WebSocketManager()
    await manager.connect(task_id, websocket)
    await manager.broadcast(task_id, {"progress": 5, "total": 10})
    manager.disconnect(task_id, websocket)
"""

import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    WebSocket连接管理器。

    按task_id分组管理连接，允许多个客户端订阅同一任务的进度推送。
    """

    def __init__(self):
        # task_id → 订阅该任务的WebSocket连接集合
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        """接受新的WebSocket连接并注册到对应的任务组"""
        await websocket.accept()
        if task_id not in self._connections:
            self._connections[task_id] = set()
        self._connections[task_id].add(websocket)
        logger.debug("WebSocket连接: task=%s, 当前订阅数=%d", task_id, len(self._connections[task_id]))

    def disconnect(self, task_id: str, websocket: WebSocket):
        """移除WebSocket连接"""
        if task_id in self._connections:
            self._connections[task_id].discard(websocket)
            if not self._connections[task_id]:
                del self._connections[task_id]

    async def broadcast(self, task_id: str, data: dict):
        """向订阅指定任务的所有客户端推送消息"""
        if task_id not in self._connections:
            return

        dead: list = []
        for ws in self._connections[task_id]:
            try:
                await ws.send_json(data)
            except Exception:
                logger.debug("WebSocket发送失败，标记为断开: task=%s", task_id)
                dead.append(ws)

        # 清理已断开的连接
        for ws in dead:
            self.disconnect(task_id, ws)

    @property
    def active_connections(self) -> int:
        """返回当前活跃连接总数"""
        return sum(len(v) for v in self._connections.values())


# 全局单例
ws_manager = WebSocketManager()
