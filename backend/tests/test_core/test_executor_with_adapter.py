"""
Executor + Adapter 端到端测试

mock 掉 httpx.Client.post 来模拟外部 Agent 响应,验证:
- executor 通过 adapter.build_request 构造请求
- 接收响应后通过 adapter.parse_response 翻译为三段式
- 翻译结果被指标计算器消费
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import httpx

from core.executor import EvaluationExecutor
import core.adapters  # noqa: F401  触发注册


# ── 一个会被 mock 替换的"假 httpx 响应" ───────────────────────
def _mock_resp(json_body: dict, status: int = 200):
    """构造一个像 httpx.Response 的假对象"""
    m = MagicMock()
    m.status_code = status
    m.raise_for_status = MagicMock()
    m.json = MagicMock(return_value=json_body)
    return m


# ── native adapter 路径 ──────────────────────────────────────
class TestExecutorWithNativeAdapter:
    def test_call_agent_uses_native_request_format(self, monkeypatch):
        """executor._call_agent 应当走 native adapter 的 build_request"""
        captured = {}

        def fake_post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["body"] = json
            captured["headers"] = headers
            return _mock_resp(
                {
                    "output": {"plan": "去北京3天,预算3000,游故宫长城"},
                    "trace": [
                        {"event_type": "thought", "data": {"content": "..."}},
                        {
                            "event_type": "tool_call",
                            "data": {"tool_name": "search_attractions"},
                        },
                    ],
                    "metrics": {"elapsed_time": 5.0},
                }
            )

        monkeypatch.setattr(httpx.Client, "post", fake_post)

        from core.adapters.base import AdapterRegistry

        adapter = AdapterRegistry.get("native")
        ex = EvaluationExecutor()

        case = {"id": "case_01", "input": "去北京", "difficulty": "easy"}
        result = ex._call_agent("http://target/api/eval/run", case, adapter, {})

        # 验证发出的请求格式(native 契约)
        assert captured["url"] == "http://target/api/eval/run"
        assert captured["body"]["input"] == "去北京"
        assert captured["body"]["session_config"]["case_id"] == "case_01"

        # 验证响应已翻译成三段式
        assert "output" in result and "trace" in result and "metrics" in result
        assert result["output"]["plan"].startswith("去北京")
        assert len(result["trace"]) == 2
        assert result["metrics"]["elapsed_time"] == 5.0


# ── openai_chat adapter 路径 ─────────────────────────────────
class TestExecutorWithOpenAIChatAdapter:
    def test_call_agent_translates_to_chat_completions(self, monkeypatch):
        """executor._call_agent 应当走 openai_chat adapter 的 build_request"""
        captured = {}

        def fake_post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["body"] = json
            captured["headers"] = headers
            # 模拟 OpenAI 标准响应
            return _mock_resp(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "好的,北京3天:故宫、长城,预算3000",
                                "tool_calls": [
                                    {
                                        "id": "c1",
                                        "type": "function",
                                        "function": {
                                            "name": "search_attractions",
                                            "arguments": '{"city":"北京"}',
                                        },
                                    },
                                    {
                                        "id": "c2",
                                        "type": "function",
                                        "function": {
                                            "name": "estimate_budget",
                                            "arguments": '{"days":3}',
                                        },
                                    },
                                ],
                            }
                        }
                    ],
                    "usage": {
                        "total_tokens": 200,
                        "prompt_tokens": 100,
                        "completion_tokens": 100,
                    },
                }
            )

        monkeypatch.setattr(httpx.Client, "post", fake_post)

        from core.adapters.base import AdapterRegistry

        adapter = AdapterRegistry.get("openai_chat")
        ex = EvaluationExecutor()

        case = {"id": "case_01", "input": "去北京3天,预算3000"}
        result = ex._call_agent(
            "https://api.deepseek.com/v1/chat/completions",
            case,
            adapter,
            {"model": "deepseek-chat", "api_key": "sk-test"},
        )

        # 验证发出的是 OpenAI 协议请求
        assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"
        body = captured["body"]
        assert body["model"] == "deepseek-chat"
        assert body["messages"][1]["content"] == "去北京3天,预算3000"
        assert "tools" in body  # 默认开了工具
        # Authorization 头注入
        assert captured["headers"]["Authorization"] == "Bearer sk-test"

        # 响应已翻译成三段式
        assert result["output"]["plan"].startswith("好的")
        events = result["trace"]
        assert [e["event_type"] for e in events] == [
            "thought",
            "tool_call",
            "tool_call",
        ]
        assert events[1]["data"]["tool_name"] == "search_attractions"
        assert events[2]["data"]["tool_name"] == "estimate_budget"
        assert result["metrics"]["total_tokens"] == 200
        # executor 应当回填 elapsed_time(adapter 没给)
        assert "elapsed_time" in result["metrics"]


# ── 验证翻译后的 trace 真的能让 tool_accuracy 算分 ─────────────
class TestEndToEndScoringFlow:
    def test_openai_chat_response_feeds_tool_accuracy(self, monkeypatch):
        """完整链路: openai_chat 响应 -> 三段式 -> tool_accuracy 指标算分"""

        def fake_post(self, url, json=None, headers=None):
            return _mock_resp(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "去北京3天",
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "search_attractions",
                                            "arguments": "{}",
                                        }
                                    },
                                    {
                                        "function": {
                                            "name": "estimate_budget",
                                            "arguments": "{}",
                                        }
                                    },
                                    {
                                        "function": {
                                            "name": "query_weather",
                                            "arguments": "{}",
                                        }
                                    },
                                ],
                            }
                        }
                    ],
                }
            )

        monkeypatch.setattr(httpx.Client, "post", fake_post)

        from core.adapters.base import AdapterRegistry
        from core.metric_factory import MetricRegistry

        adapter = AdapterRegistry.get("openai_chat")
        ex = EvaluationExecutor()

        case = {
            "id": "c1",
            "input": "去北京",
            "expected_tool_sequence": [
                "search_attractions",
                "estimate_budget",
                "query_weather",
            ],
        }
        agent_response = ex._call_agent("http://x", case, adapter, {"api_key": "k"})

        # 用 tool_accuracy 算分,应该接近满分(完全匹配 + 顺序一致)
        metric = MetricRegistry.get("tool_accuracy")
        compute_input = {
            "case_meta": case,
            "agent_output": agent_response["output"],
            "agent_trace": agent_response["trace"],
            "agent_metrics": agent_response["metrics"],
        }
        result = metric.compute(compute_input)
        assert result["score"] >= 0.9, (
            f"score={result['score']}, details={result['details']}"
        )
        assert result["details"]["recall"] == 1.0
        assert result["details"]["precision"] == 1.0
        assert result["details"]["order_score"] == 1.0
