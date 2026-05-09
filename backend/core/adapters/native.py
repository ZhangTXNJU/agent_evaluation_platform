"""
原生适配器 — 评估平台默认契约 (向后兼容)

请求格式: {input, session_config}
响应格式: {output, trace, metrics}

适用于按照本平台契约实现的 Agent (例如对接同一项目里"旅行 Agent 平台"的同学)。
"""

from typing import Any, Dict, Optional
from core.adapters.base import BaseAgentAdapter, AdapterRegistry


@AdapterRegistry.register("native")
class NativeAdapter(BaseAgentAdapter):
    """直通适配器 — Agent 已按本平台契约实现,不做任何翻译。"""

    description = "原生协议: POST {input, session_config} -> {output, trace, metrics}"

    def build_request(
        self,
        case_meta: Dict[str, Any],
        adapter_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # 透传 case 信息,session_config 由调用方/任务级配置决定
        session_config: Dict[str, Any] = {
            "case_id": case_meta.get("id"),
            "difficulty": case_meta.get("difficulty"),
        }
        # 任务级 adapter_config 中允许覆盖 session_config
        if adapter_config and isinstance(adapter_config.get("session_config"), dict):
            session_config.update(adapter_config["session_config"])

        return {
            "input": case_meta.get("input", ""),
            "session_config": session_config,
        }

    def parse_response(
        self,
        raw_response: Dict[str, Any],
        adapter_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # 已经是三段式,直接返回(做最小防御)
        return {
            "output": raw_response.get("output", {}),
            "trace": raw_response.get("trace", []) or [],
            "metrics": raw_response.get("metrics", {}) or {},
        }
