"""
Mock Agent Platform — 用于演示评估平台与被评估Agent之间的对接接口。

这是一个示例Agent，模拟一个旅行规划助手的行为。
它接收用户的旅行需求，返回规划结果 + 思考链 + 工具调用追踪。

启动方式:
    python mock_agent.py
    → 监听 http://localhost:8000/api/eval/run

然后在评估平台中创建任务时，Agent端点填写: http://localhost:8000/api/eval/run
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Mock Travel Agent")

# 允许跨域请求
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/api/eval/run")
def evaluate(request: dict):
    """
    评估平台调用的核心接口。

    接收格式:
    {
        "input": "请帮我规划一次为期3天的北京之旅，预算控制在3000元以内。",
        "session_config": {
            "case_id": "case_01",
            "difficulty": "easy"
        }
    }

    返回格式 (必须):
    {
        "output": { ... 规划结果, 可以任意结构 ... },
        "trace": [
            {"event_type": "thought", "timestamp": "...", "data": {"content": "思考内容"}},
            {"event_type": "tool_call", "timestamp": "...", "data": {"tool_name": "...", "params": {...}}},
            {"event_type": "observation", "timestamp": "...", "data": {"result_summary": "..."}},
            ...
        ],
        "metrics": {
            "elapsed_time": 12.5   # 执行耗时(秒)
        }
    }
    """
    user_input = request.get("input", "")
    session_config = request.get("session_config", {})
    case_id = session_config.get("case_id", "unknown")
    difficulty = session_config.get("difficulty", "medium")

    # ── 根据用户输入智能生成模拟的输出 ──
    # 实际Agent会在这里调用自己的推理逻辑
    output = generate_mock_output(user_input, case_id, difficulty)

    # ── 生成模拟的思考链和工具调用追踪 ──
    trace = generate_mock_trace(user_input, case_id)

    # ── 计算模拟的响应时间 ──
    import random
    elapsed = random.uniform(5.0, 25.0)  # 模拟5~25秒的执行时间

    return {"output": output, "trace": trace, "metrics": {"elapsed_time": round(elapsed, 2)}}


def generate_mock_output(user_input: str, case_id: str, difficulty: str) -> dict:
    """
    模拟Agent的规划输出。

    实际Agent这里会经过:
    LLM推理 → 工具调用 → 结果整合 → 生成最终方案
    """
    # 从输入中提取基本信息（实际Agent会用NLP解析）
    destinations = {
        "case_01": "北京",
        "case_02": "上海",
        "case_03": "成都",
        "case_04": "三亚",
        "case_05": "昆明、大理、丽江、香格里拉",
        "case_06": "桂林、阳朔",
        "case_07": "西安",
        "case_08": "乌鲁木齐、天山、喀纳斯、吐鲁番、喀什",
        "case_09": "哈尔滨、雪乡、长白山、沈阳",
        "case_10": "南京、苏州、周庄、同里、乌镇、南浔、西塘、杭州",
    }
    destination = destinations.get(case_id, "目的地")

    return {
        "plan": f"已为您规划{destination}旅行方案",
        "destination": destination,
        "itinerary": [
            {"day": 1, "activities": [f"抵达{destination}", "入住酒店", "自由活动"]},
            {"day": 2, "activities": ["上午游览景点", "下午文化体验", "晚上品尝当地美食"]},
            {"day": 3, "activities": ["购物纪念品", "返程"]},
        ],
        "budget_estimate": {"total": 2800, "breakdown": {"交通": 1000, "住宿": 900, "餐饮": 500, "门票": 400}},
        "tips": ["建议提前预订门票", "注意天气变化", "携带身份证件"],
    }


def generate_mock_trace(user_input: str, case_id: str) -> list:
    """
    模拟Agent的执行追踪——这是评估平台进行指标打分的核心数据来源。

    每个事件包含:
    - event_type: thought(思考) / tool_call(工具调用) / observation(观察结果)
    - timestamp: ISO格式时间戳
    - data: 事件的详细数据

    评估平台各指标对trace的使用:
    - tool_accuracy: 提取所有tool_call事件中的tool_name，与预期工具序列对比
    - llm_judge: 提取所有thought事件中的content，发给GPT评分
    - response_time: 从第一个到最后一个事件的时间戳计算耗时
    """
    import datetime

    now = datetime.datetime.utcnow()
    ts = lambda offset: (now + datetime.timedelta(seconds=offset)).isoformat() + "Z"

    return [
        # Step 1: 思考——分析用户需求
        {
            "event_type": "thought",
            "timestamp": ts(0),
            "data": {
                "content": f"收到用户需求: {user_input}。首先需要搜索目的地的热门景点，了解有哪些可游玩的地方。"
            },
        },
        # Step 2: 调用搜索景点工具
        {
            "event_type": "tool_call",
            "timestamp": ts(1),
            "data": {
                "tool_name": "search_attractions",
                "params": {"query": "热门景点", "limit": 10},
            },
        },
        # Step 3: 观察搜索结果
        {
            "event_type": "observation",
            "timestamp": ts(2),
            "data": {
                "result_summary": "找到15个景点，包括5A级景区3个、博物馆2个、自然风光5个、美食街5个",
                "top_attractions": ["景点A", "景点B", "景点C"],
            },
        },
        # Step 4: 思考——规划预算
        {
            "event_type": "thought",
            "timestamp": ts(3),
            "data": {
                "content": "已获取景点列表，接下来需要估算旅行预算。用户提到的预算限制需要重点考虑。"
            },
        },
        # Step 5: 调用预算估算工具
        {
            "event_type": "tool_call",
            "timestamp": ts(4),
            "data": {
                "tool_name": "estimate_budget",
                "params": {"destinations": ["目的地"], "days": 3, "style": "standard"},
            },
        },
        # Step 6: 观察预算估算结果
        {
            "event_type": "observation",
            "timestamp": ts(5),
            "data": {
                "result_summary": "估算总费用约2800元，包含交通、住宿、餐饮、门票",
                "details": {"交通": 1000, "住宿": 900, "餐饮": 500, "门票": 400},
            },
        },
        # Step 7: 思考——检查天气
        {
            "event_type": "thought",
            "timestamp": ts(6),
            "data": {
                "content": "预算合理。为了确保旅行顺利，还需要查询目的地的天气情况，以便给出合理的出行建议。"
            },
        },
        # Step 8: 调用天气查询工具
        {
            "event_type": "tool_call",
            "timestamp": ts(7),
            "data": {
                "tool_name": "query_weather",
                "params": {"city": "目的地", "days": 3},
            },
        },
        # Step 9: 观察天气结果
        {
            "event_type": "observation",
            "timestamp": ts(8),
            "data": {
                "result_summary": "未来3天天气晴朗，气温20-28°C，适宜出行",
                "forecast": [
                    {"day": 1, "weather": "晴", "temp_high": 28, "temp_low": 20},
                    {"day": 2, "weather": "多云", "temp_high": 26, "temp_low": 19},
                    {"day": 3, "weather": "晴", "temp_high": 27, "temp_low": 21},
                ],
            },
        },
        # Step 10: 最终思考——汇总方案
        {
            "event_type": "thought",
            "timestamp": ts(9),
            "data": {
                "content": "所有信息已收集完毕。景点丰富、预算合理、天气良好。现在整合所有信息，生成最终的旅行规划方案。"
            },
        },
    ]


if __name__ == "__main__":
    print("=" * 60)
    print("Mock Travel Agent 启动中...")
    print("")
    print("评估平台对接地址: POST http://localhost:8000/api/eval/run")
    print("")
    print("在评估平台中创建任务时，Agent端点填写:")
    print("  http://localhost:8000/api/eval/run")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
