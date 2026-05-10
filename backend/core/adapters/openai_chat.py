"""
OpenAI Chat Completions 兼容适配器

覆盖所有遵循 OpenAI Chat Completions 协议的服务:
- OpenAI 官方 (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, ...)
- DeepSeek (deepseek-chat, deepseek-reasoner)
- Moonshot Kimi (moonshot-v1-8k, ...)
- 智谱 GLM (glm-4-plus, ...)
- 通义千问 (qwen-plus, ...)
- Together / Groq / OpenRouter
- 本地 Ollama (http://localhost:11434/v1) / vLLM / LM Studio

agent_endpoint 应填 chat completions 完整 URL,例如:
  https://api.deepseek.com/v1/chat/completions
  http://localhost:11434/v1/chat/completions

adapter_config 支持的字段:
  - api_key (str, 必填; 也可读环境变量 OPENAI_API_KEY)
  - model (str, 默认 "gpt-4o-mini")
  - system_prompt (str, 可选; 默认让模型扮演旅行规划助手)
  - temperature (float, 默认 0.3)
  - max_tokens (int, 默认 1500)
  - extra_headers (dict, 可选)
"""

import os
import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from core.adapters.base import BaseAgentAdapter, AdapterRegistry


DEFAULT_SYSTEM_PROMPT = (
    "你是一个旅行规划助手。请根据用户需求,生成一份完整的旅行计划。"
    "在回答中务必清晰地写出: 目的地、总天数、总预算(数字)、关键景点名称。"
    "如果需要查询信息,可以调用提供的工具(search_attractions / query_weather / "
    "estimate_budget / search_hotels / search_flights)。"
)


# 用于让模型可以返回结构化工具调用的"工具清单"
# (这些只是给模型看的工具描述,实际不会被真正执行 — 评估只看是否调用)
DEFAULT_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_attractions",
            "description": "搜索某城市的旅游景点",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_weather",
            "description": "查询某城市指定时间段的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "days": {"type": "integer"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_budget",
            "description": "估算旅行预算",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "days": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "搜索酒店",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "搜索机票",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string"},
                    "to_city": {"type": "string"},
                },
            },
        },
    },
]


@AdapterRegistry.register("openai_chat")
class OpenAIChatAdapter(BaseAgentAdapter):
    """OpenAI Chat Completions 协议兼容适配器。"""

    description = (
        "OpenAI Chat Completions 兼容协议 — 支持 OpenAI/DeepSeek/Moonshot/智谱/"
        "通义/Groq/Ollama 等所有遵循 chat/completions 接口的服务"
    )

    # ── 请求构造 ──
    def build_request(
        self,
        case_meta: Dict[str, Any],
        adapter_config: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        cfg = adapter_config or {}

        model = cfg.get("model", "gpt-4o-mini")
        system_prompt = cfg.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        temperature = cfg.get("temperature", 0.3)
        max_tokens = cfg.get("max_tokens", 1500)

        # 构建消息列表
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]

        if history:
            # 多轮模式: 把对话历史合并到 messages 中
            messages.extend(history)
        else:
            # 单轮模式: 直接用测试用例的 input
            messages.append(
                {"role": "user", "content": case_meta.get("input", "")}
            )

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 是否启用工具(默认开启,这样 tool_accuracy 才有数据)
        if cfg.get("enable_tools", True):
            body["tools"] = cfg.get("tools", DEFAULT_TOOLS)
            body["tool_choice"] = "auto"

        return body

    # ── HTTP 头(注入 Authorization) ──
    def headers(
        self, adapter_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        cfg = adapter_config or {}
        api_key = cfg.get("api_key") or os.getenv("OPENAI_API_KEY", "")
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            h["Authorization"] = f"Bearer {api_key}"
        # 用户自定义 header
        extra = cfg.get("extra_headers")
        if isinstance(extra, dict):
            h.update({str(k): str(v) for k, v in extra.items()})
        return h

    # ── 响应翻译 ──
    def parse_response(
        self,
        raw_response: Dict[str, Any],
        adapter_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        choices = raw_response.get("choices") or []
        if not choices:
            return {
                "output": {"plan": ""},
                "trace": [],
                "metrics": self._extract_usage(raw_response),
            }

        message = choices[0].get("message", {}) or {}
        text = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []

        # ── 翻译 trace ──
        # 把 content 当 thought,把 tool_calls 当 tool_call 事件
        trace: List[Dict[str, Any]] = []
        ts = self._now_iso()

        if text:
            trace.append(
                {
                    "timestamp": ts,
                    "event_type": "thought",
                    "data": {"content": text},
                }
            )

        for tc in tool_calls:
            fn = (tc or {}).get("function", {}) or {}
            tool_name = fn.get("name") or ""
            args_raw = fn.get("arguments") or "{}"
            try:
                params = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                params = {"raw": args_raw}
            trace.append(
                {
                    "timestamp": self._now_iso(),
                    "event_type": "tool_call",
                    "data": {"tool_name": tool_name, "params": params},
                }
            )

        # ── 翻译 output ──
        # success_rate 走子串匹配,所以把模型的纯文本回复放在 plan 字段
        # 同时把 tool_calls 一起放进去,便于前端展示
        output = {
            "plan": text,
            "tool_calls": [
                {
                    "name": (tc or {}).get("function", {}).get("name"),
                    "arguments": (tc or {}).get("function", {}).get("arguments"),
                }
                for tc in tool_calls
            ],
        }

        # ── 翻译 metrics ──
        metrics = self._extract_usage(raw_response)
        # 注:OpenAI 协议响应里没有 elapsed_time,evaluator 会兜底用 trace 时间戳;
        # 但这里 trace 时间戳是我们自己 now() 出来的,差值近 0,所以由 executor
        # 在 _call_agent 里把外部测量的 elapsed_time 注入(见 executor 改造)。
        return {"output": output, "trace": trace, "metrics": metrics}

    # ── 内部工具 ──
    def _extract_usage(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        usage = raw.get("usage") or {}
        metrics: Dict[str, Any] = {}
        if "total_tokens" in usage:
            metrics["total_tokens"] = usage["total_tokens"]
        if "prompt_tokens" in usage:
            metrics["prompt_tokens"] = usage["prompt_tokens"]
        if "completion_tokens" in usage:
            metrics["completion_tokens"] = usage["completion_tokens"]
        return metrics

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
