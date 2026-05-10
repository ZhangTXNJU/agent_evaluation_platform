"""
MyAgent 的 HTTP API 包装层

将 AutonomousTravelAgent 包装为一个 HTTP 服务，暴露评估平台兼容的原生协议:
  POST /api/eval/run
  请求: {"input": "...", "session_config": {}}
  响应: {"output": {...}, "trace": [...], "metrics": {...}}

启动方式:
  cd myagent
  python api_server.py          # 默认监听 localhost:8000

然后在评估平台创建任务时:
  - 端点预设: 选 "本地原生 Agent (localhost:8000)"
  - Agent端点URL: http://localhost:8000/api/eval/run
  - 适配器: native
"""

import time
import json
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

from agent_core import AutonomousTravelAgent
from config import load_settings

app = FastAPI(title="MyAgent API Server")


class EvalRequest(BaseModel):
    input: str = ""
    session_config: dict = {}
    history: list = []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.post("/api/eval/run")
def run_eval(req: EvalRequest):
    """评估端点 — 符合评估平台原生三段式契约"""
    settings = load_settings()
    agent = AutonomousTravelAgent(settings=settings)

    t0 = time.time()

    # 构建 Agent 输入: 多轮模式下将场景上下文和历史分开处理
    agent_input = req.input or ""
    if req.history:
        history_text = "\n".join(
            f"[{h.get('role', 'unknown')}]: {h.get('content', '')}"
            for h in req.history
        )
        # 多轮对话模式: 提供场景背景 + 对话历史
        if agent_input:
            agent_input = f"{agent_input}\n\n[对话历史]\n{history_text}\n\n请根据上述对话历史,以旅行助手的身份回复用户最后一条消息。"
        else:
            agent_input = f"[对话历史]\n{history_text}\n\n请根据上述对话历史,以旅行助手的身份回复用户最后一条消息。"

    # 执行 Agent
    result = agent.run(agent_input)

    elapsed = round(time.time() - t0, 2)

    # 构建输出
    output = {
        "plan": result.final_response,
        "session_id": result.session_id,
        "status": result.status,
    }

    # trace 已经符合评估平台格式: {timestamp, event_type, data}
    trace = result.trace

    metrics = {
        "elapsed_time": elapsed,
        "total_tokens": 0,  # httpx 不暴露 token 数, 由评估平台自行估算
        "trace_events": len(trace),
    }

    return {"output": output, "trace": trace, "metrics": metrics}


@app.get("/health")
def health():
    return {"status": "ok", "service": "MyAgent API Server"}


@app.get("/")
def root():
    return {
        "service": "MyAgent API Server",
        "endpoint": "/api/eval/run",
        "protocol": "native (三段式契约)",
        "hint": "评估平台创建任务时选择 '本地原生 Agent' 预设, 端点填 http://localhost:8000/api/eval/run",
    }


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", "8000"))
    print(f"MyAgent API Server 启动中... port={port}")
    print(f"评估端点: http://localhost:{port}/api/eval/run")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
