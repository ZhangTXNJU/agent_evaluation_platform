"""
适配器单元测试

验证:
- AdapterRegistry 注册/查找
- NativeAdapter 透传契约
- OpenAIChatAdapter 请求构造与响应翻译
- ENDPOINT_PRESETS 完整性
"""

import json
import pytest

import core.adapters  # noqa: F401  触发注册
from core.adapters.base import AdapterRegistry, BaseAgentAdapter
from core.adapters.native import NativeAdapter
from core.adapters.openai_chat import OpenAIChatAdapter
from core.adapters.presets import ENDPOINT_PRESETS


# ── Registry ───────────────────────────────────────────────────
class TestAdapterRegistry:
    def test_native_registered(self):
        assert AdapterRegistry.is_registered("native")
        assert isinstance(AdapterRegistry.get("native"), NativeAdapter)

    def test_openai_chat_registered(self):
        assert AdapterRegistry.is_registered("openai_chat")
        assert isinstance(AdapterRegistry.get("openai_chat"), OpenAIChatAdapter)

    def test_unknown_returns_none(self):
        assert AdapterRegistry.get("nonexistent_xyz") is None

    def test_list_all_has_descriptions(self):
        m = AdapterRegistry.list_all()
        assert "native" in m and "openai_chat" in m
        assert all(isinstance(v, str) and len(v) > 0 for v in m.values())


# ── NativeAdapter ──────────────────────────────────────────────
class TestNativeAdapter:
    def setup_method(self):
        self.a = NativeAdapter()
        self.case = {
            "id": "case_01",
            "input": "去北京3天",
            "difficulty": "easy",
            "expected_constraints": {"destination": "北京"},
        }

    def test_build_request_shape(self):
        req = self.a.build_request(self.case, {})
        assert req["input"] == "去北京3天"
        assert req["session_config"]["case_id"] == "case_01"
        assert req["session_config"]["difficulty"] == "easy"

    def test_build_request_session_config_override(self):
        cfg = {"session_config": {"case_id": "OVERRIDE", "extra": "x"}}
        req = self.a.build_request(self.case, cfg)
        assert req["session_config"]["case_id"] == "OVERRIDE"
        assert req["session_config"]["extra"] == "x"

    def test_parse_response_passthrough(self):
        raw = {
            "output": {"plan": "x"},
            "trace": [{"event_type": "thought", "data": {"content": "y"}}],
            "metrics": {"elapsed_time": 1.5},
        }
        parsed = self.a.parse_response(raw, {})
        assert parsed == raw

    def test_parse_response_missing_fields(self):
        parsed = self.a.parse_response({}, {})
        assert parsed["output"] == {}
        assert parsed["trace"] == []
        assert parsed["metrics"] == {}


# ── OpenAIChatAdapter ──────────────────────────────────────────
class TestOpenAIChatAdapter:
    def setup_method(self):
        self.a = OpenAIChatAdapter()
        self.case = {"id": "case_01", "input": "去北京3天", "difficulty": "easy"}

    def test_build_request_basic(self):
        req = self.a.build_request(
            self.case, {"model": "gpt-4o-mini", "api_key": "sk-x"}
        )
        assert req["model"] == "gpt-4o-mini"
        assert len(req["messages"]) == 2  # system + user
        assert req["messages"][0]["role"] == "system"
        assert req["messages"][1]["role"] == "user"
        assert req["messages"][1]["content"] == "去北京3天"
        # 默认开启工具
        assert "tools" in req
        assert req["tool_choice"] == "auto"

    def test_build_request_disable_tools(self):
        req = self.a.build_request(
            self.case, {"enable_tools": False, "api_key": "sk-x"}
        )
        assert "tools" not in req

    def test_build_request_custom_temperature(self):
        req = self.a.build_request(
            self.case, {"api_key": "sk-x", "temperature": 0.7, "max_tokens": 800}
        )
        assert req["temperature"] == 0.7
        assert req["max_tokens"] == 800

    def test_build_request_default_model(self):
        req = self.a.build_request(self.case, {})
        assert req["model"] == "gpt-4o-mini"

    def test_headers_with_api_key(self):
        h = self.a.headers({"api_key": "sk-test"})
        assert h["Authorization"] == "Bearer sk-test"

    def test_headers_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        h = self.a.headers({})
        assert "Authorization" not in h

    def test_headers_extra_headers(self):
        h = self.a.headers({"api_key": "sk-x", "extra_headers": {"X-Custom": "abc"}})
        assert h["X-Custom"] == "abc"

    def test_parse_response_full(self):
        raw = {
            "choices": [
                {
                    "message": {
                        "content": "我推荐北京3天行程",
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
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150,
            },
        }
        parsed = self.a.parse_response(raw, {})

        # output 含纯文本与工具调用清单
        assert parsed["output"]["plan"] == "我推荐北京3天行程"
        assert len(parsed["output"]["tool_calls"]) == 2

        # trace 含 1 个 thought + 2 个 tool_call
        events = parsed["trace"]
        types = [e["event_type"] for e in events]
        assert types == ["thought", "tool_call", "tool_call"]
        assert events[0]["data"]["content"] == "我推荐北京3天行程"
        assert events[1]["data"]["tool_name"] == "search_attractions"
        assert events[1]["data"]["params"] == {"city": "北京"}
        assert events[2]["data"]["tool_name"] == "estimate_budget"

        # metrics 含 token 用量
        assert parsed["metrics"]["total_tokens"] == 150
        assert parsed["metrics"]["prompt_tokens"] == 50
        assert parsed["metrics"]["completion_tokens"] == 100

    def test_parse_response_empty_choices(self):
        parsed = self.a.parse_response({"choices": []}, {})
        assert parsed["output"]["plan"] == ""
        assert parsed["trace"] == []

    def test_parse_response_text_only_no_tool_calls(self):
        raw = {
            "choices": [{"message": {"content": "纯文本回复"}}],
        }
        parsed = self.a.parse_response(raw, {})
        events = parsed["trace"]
        assert len(events) == 1
        assert events[0]["event_type"] == "thought"

    def test_parse_response_malformed_arguments(self):
        """模型偶尔返回非法 JSON 的 arguments,不应崩溃"""
        raw = {
            "choices": [
                {
                    "message": {
                        "content": None,  # OpenAI 也允许 content=None
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "foo",
                                    "arguments": "{not valid json",
                                }
                            }
                        ],
                    }
                }
            ]
        }
        parsed = self.a.parse_response(raw, {})
        events = parsed["trace"]
        assert len(events) == 1  # 只有 tool_call,无 thought(content=None)
        assert events[0]["event_type"] == "tool_call"
        assert events[0]["data"]["tool_name"] == "foo"
        assert "raw" in events[0]["data"]["params"]


# ── 预设清单 ───────────────────────────────────────────────────
class TestEndpointPresets:
    def test_presets_not_empty(self):
        assert len(ENDPOINT_PRESETS) > 0

    def test_each_preset_has_required_fields(self):
        for p in ENDPOINT_PRESETS:
            assert "key" in p and isinstance(p["key"], str)
            assert "label" in p
            assert "description" in p
            assert "adapter_type" in p
            assert "agent_endpoint" in p  # 可以是空字符串
            assert "adapter_config" in p
            assert isinstance(p["adapter_config"], dict)

    def test_preset_keys_unique(self):
        keys = [p["key"] for p in ENDPOINT_PRESETS]
        assert len(keys) == len(set(keys))

    def test_all_preset_adapter_types_registered(self):
        for p in ENDPOINT_PRESETS:
            assert AdapterRegistry.is_registered(p["adapter_type"]), (
                f"preset '{p['key']}' uses unregistered adapter '{p['adapter_type']}'"
            )

    def test_has_native_local_default(self):
        keys = [p["key"] for p in ENDPOINT_PRESETS]
        assert "native_local" in keys
