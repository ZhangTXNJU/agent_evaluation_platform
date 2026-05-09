"""
FastAPI应用入口 (T007)
组装路由、CORS中间件、数据库初始化、启动评估执行引擎。
启动命令: uvicorn main:app --reload --port 8001
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# 全局执行引擎实例
_executor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化DB和执行引擎，关闭时清理资源"""
    global _executor

    # 启动时：初始化数据库表 + 导入种子数据
    from db import init_db

    init_db()

    # 导入种子数据（首次启动幂等）
    import init_db as seed_module

    seed_module.seed_default_dataset()

    # 启动评估执行引擎（后台线程）
    from core.executor import EvaluationExecutor

    _executor = EvaluationExecutor()
    _executor.start()

    yield

    # 关闭时：停止执行引擎
    if _executor:
        _executor.stop()


# ── 创建FastAPI应用实例 ──
app = FastAPI(
    title="Agent Evaluation Platform API",
    version="1.0.0",
    description="智能Agent评估平台后端API——管理评估任务、数据集和对比分析",
    lifespan=lifespan,
)

# ── CORS中间件（开发环境允许前端开发服务器来源） ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST API 路由注册 ──
from api.datasets import router as datasets_router
from api.tasks import router as tasks_router
from api.compare import router as compare_router
from api.adapters import router as adapters_router

app.include_router(datasets_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(compare_router, prefix="/api/v1")
app.include_router(adapters_router, prefix="/api/v1")


# ── WebSocket 端点（T050：实时进度推送） ──
from ws.manager import ws_manager


@app.websocket("/ws/tasks/{task_id}")
async def websocket_task_progress(websocket: WebSocket, task_id: str):
    """订阅指定任务的实时执行进度"""
    await ws_manager.connect(task_id, websocket)
    try:
        while True:
            # 保持连接，接收客户端心跳/pong
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(task_id, websocket)
    except Exception:
        ws_manager.disconnect(task_id, websocket)


@app.get("/health")
def health_check():
    """健康检查端点"""
    return {"status": "ok", "version": "1.0.0"}
