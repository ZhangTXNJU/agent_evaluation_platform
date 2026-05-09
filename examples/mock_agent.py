"""
Mock 旅行规划 Agent — 用于评估平台的演示后端

这是一个不需要任何 API key 的"假 Agent",符合本评估平台的原生三段式契约:
  POST /api/eval/run
  请求体: {"input": "...", "session_config": {...}}
  响应体: {"output": {...}, "trace": [...], "metrics": {...}}

启动方式:
    pip install fastapi uvicorn        # (如果还没装)
    python examples/mock_agent.py      # 监听 http://localhost:8000

然后在评估平台前端创建任务时:
  - 端点预设: 选 "本地原生 Agent (localhost:8000)"
  - 适配器配置: {} (留空即可)
  - 取消勾选 llm_judge 指标(它需要真实 LLM API)

特意设计了 3 档"Agent 表现"供你切换演示:
  AGENT_QUALITY = "good"    -> 各项指标 0.8+(完美 Agent)
  AGENT_QUALITY = "medium"  -> 各项指标 0.5~0.7(普通 Agent)
  AGENT_QUALITY = "bad"     -> 各项指标 0.2~0.4(差劲 Agent)

通过同一个 Mock 跑 3 个不同任务(每次改一下 AGENT_QUALITY 重启),
就能在"多任务对比"页看到雷达图差异 — 完美的演示效果。
"""

import os
import time
import random
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


# ── 演示开关:控制 mock agent 表现质量 ─────────────────────────
# 也可通过环境变量 AGENT_QUALITY 覆盖,启动多个不同质量的 mock 进程做对比
AGENT_QUALITY = os.getenv("AGENT_QUALITY", "good").lower()
# 端口可通过 PORT 环境变量覆盖。默认 9001 (避开本机已被占用的 8000/9000)
PORT = int(os.getenv("PORT", "9001"))


app = FastAPI(title=f"Mock Travel Agent ({AGENT_QUALITY})")


class EvalRequest(BaseModel):
    input: str
    session_config: dict = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 简单关键词抽取(用于 mock 的"思考") ───────────────────────
_CITIES = [
    "北京",
    "上海",
    "成都",
    "三亚",
    "杭州",
    "西安",
    "哈尔滨",
    "厦门",
    "云南",
    "西藏",
    "广州",
    "深圳",
    "南京",
    "苏州",
    "长沙",
]
_KEYWORDS = [
    "故宫",
    "长城",
    "外滩",
    "东方明珠",
    "大熊猫",
    "都江堰",
    "海边酒店",
    "机票",
    "昆明",
    "大理",
    "丽江",
    "香格里拉",
    "高铁",
    "兵马俑",
    "大唐不夜城",
    "鼓浪屿",
    "西湖",
]


def _extract_destination(text: str) -> str:
    for c in _CITIES:
        if c in text:
            return c
    return "北京"


def _extract_days(text: str) -> int:
    for ch in text:
        if ch.isdigit():
            try:
                return int(ch)
            except ValueError:
                continue
    return 3


def _extract_budget(text: str) -> int:
    import re

    nums = re.findall(r"(\d{3,6})\s*[元¥万]?", text)
    if nums:
        # 简单取第一个 >= 1000 的数字
        for n in nums:
            v = int(n)
            if v >= 1000:
                return v
    return 3000


# ── 三种质量配置 ─────────────────────────────────────────────
QUALITY_PROFILES = {
    "good": {
        "include_keywords": True,  # 是否在 plan 中提到关键词
        "include_destination": True,
        "include_days": True,
        "include_budget": True,
        "tool_completeness": 1.0,  # 工具调用完备度(1.0 全调,0.5 少调一半)
        "tool_extra_noise": 0,  # 多余工具调用数量
        "tool_order_correct": True,  # 工具顺序是否对
        "delay_min": 1.0,
        "delay_max": 2.5,
    },
    "medium": {
        "include_keywords": True,
        "include_destination": True,
        "include_days": True,
        "include_budget": False,  # 不写预算
        "tool_completeness": 0.7,
        "tool_extra_noise": 1,
        "tool_order_correct": True,
        "delay_min": 2.0,
        "delay_max": 4.0,
    },
    "bad": {
        "include_keywords": False,  # 不提关键词
        "include_destination": True,
        "include_days": False,
        "include_budget": False,
        "tool_completeness": 0.4,
        "tool_extra_noise": 2,
        "tool_order_correct": False,
        "delay_min": 4.0,
        "delay_max": 6.0,
    },
}


@app.post("/api/eval/run")
def run(req: EvalRequest):
    """评估端点 — 模拟一个旅行规划 Agent 的完整执行过程"""
    profile = QUALITY_PROFILES.get(AGENT_QUALITY, QUALITY_PROFILES["good"])

    t0 = time.time()
    input_text = req.input

    # ── 1. 解析用户需求 ──
    dest = _extract_destination(input_text)
    days = _extract_days(input_text)
    budget = _extract_budget(input_text)

    # ── 2. 模拟思考过程(trace 中的 thought 事件) ──
    thoughts = [
        f"用户想去{dest}玩{days}天,预算{budget}元左右",
        f"我应该先查询{dest}的热门景点",
    ]

    # ── 3. 构造工具调用序列 ──
    full_tools = [
        ("search_attractions", {"city": dest}),
        ("query_weather", {"city": dest, "days": days}),
        ("estimate_budget", {"city": dest, "days": days}),
        ("search_hotels", {"city": dest}),
        ("search_flights", {"to_city": dest}),
    ]
    n_tools = max(1, int(len(full_tools) * profile["tool_completeness"]))
    selected = full_tools[:n_tools]

    # 顺序错误时打乱
    if not profile["tool_order_correct"]:
        random.shuffle(selected)

    # 加噪声工具
    noise_pool = [
        ("search_restaurants", {"city": dest}),
        ("get_traffic_info", {"city": dest}),
        ("check_holiday", {}),
    ]
    for _ in range(profile["tool_extra_noise"]):
        selected.append(random.choice(noise_pool))

    # ── 4. 构造 trace 事件列表 ──
    trace = []
    for t in thoughts:
        trace.append(
            {
                "timestamp": _now_iso(),
                "event_type": "thought",
                "data": {"content": t},
            }
        )
    for tool_name, params in selected:
        trace.append(
            {
                "timestamp": _now_iso(),
                "event_type": "tool_call",
                "data": {"tool_name": tool_name, "params": params},
            }
        )
        trace.append(
            {
                "timestamp": _now_iso(),
                "event_type": "observation",
                "data": {
                    "tool_name": tool_name,
                    "result_summary": f"{tool_name} 返回了 mock 数据",
                },
            }
        )

    # ── 5. 构造 plan 文本(success_rate 会做子串匹配) ──
    plan_parts = []
    if profile["include_destination"]:
        plan_parts.append(f"为您规划{dest}之旅")
    else:
        plan_parts.append("为您规划一段精彩旅程")

    if profile["include_days"]:
        plan_parts.append(f"行程共 {days} 天")

    if profile["include_budget"]:
        plan_parts.append(f"总预算约 {budget} 元(包含交通、住宿、餐饮)")

    if profile["include_keywords"]:
        # 把数据集中常见关键词都堆上,提高 success_rate
        relevant_kws = [k for k in _KEYWORDS if k in input_text]
        if not relevant_kws:
            # 兜底:加一些常见景点名
            if dest == "北京":
                relevant_kws = ["故宫", "长城"]
            elif dest == "上海":
                relevant_kws = ["外滩", "东方明珠"]
            else:
                relevant_kws = []
        if relevant_kws:
            plan_parts.append(f"包含主要景点: {', '.join(relevant_kws)}")

    plan_parts.append(f"Day1: 抵达{dest},适应环境")
    if days >= 2:
        plan_parts.append(f"Day2-{days}: 深度游玩")

    plan_text = "\n".join(plan_parts)

    # ── 6. 模拟延时 ──
    delay = random.uniform(profile["delay_min"], profile["delay_max"])
    time.sleep(delay)

    elapsed = round(time.time() - t0, 2)

    # ── 7. 返回三段式响应 ──
    return {
        "output": {
            "plan": plan_text,
            "destination": dest,
            "days": days,
            "estimated_budget": budget,
        },
        "trace": trace,
        "metrics": {
            "elapsed_time": elapsed,
            "total_tokens": random.randint(150, 400),
        },
    }


@app.get("/")
def root():
    return {
        "service": "Mock Travel Agent",
        "quality": AGENT_QUALITY,
        "port": PORT,
        "endpoint": "/api/eval/run",
        "hint": "通过环境变量 AGENT_QUALITY=good|medium|bad 切换演示质量",
    }


if __name__ == "__main__":
    print(f"Mock Travel Agent 启动中... quality={AGENT_QUALITY}, port={PORT}")
    print(f"评估端点: http://localhost:{PORT}/api/eval/run")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
