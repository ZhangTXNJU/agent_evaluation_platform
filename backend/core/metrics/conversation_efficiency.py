"""
对话效率指标 (conversation_efficiency)
衡量Agent完成用户目标所需的对话轮次是否高效。

公式: score = min(1.0, expected_turns / actual_turns)
- 如果实际轮次 <= 预期轮次 -> 1.0 (高效)
- 如果实际轮次 > 预期轮次 -> 按比例降低 (低效)
"""

from typing import Any, Dict
from core.metrics.base import BaseMetric
from core.metric_factory import MetricRegistry


@MetricRegistry.register("conversation_efficiency")
class ConversationEfficiencyMetric(BaseMetric):
    """对话效率——评估Agent完成目标所需的对话轮次"""

    description = "评估多轮对话的效率:实际轮次 vs 预期轮次,越少轮次完成越高效"

    def compute(self, case_result: Dict[str, Any]) -> Dict[str, Any]:
        case_meta = case_result.get("case_meta", {})
        agent_output = case_result.get("agent_output", {}) or {}

        # 获取预期轮次
        expected_turns = case_meta.get("expected_turns")
        if expected_turns is None:
            expected_turns = 5  # 默认预期5轮

        # 获取实际轮次
        actual_turns = agent_output.get("turns", 0)
        if actual_turns == 0:
            # 尝试从 transcript 推断
            transcript = agent_output.get("transcript") or []
            if isinstance(transcript, list):
                actual_turns = sum(1 for t in transcript if t.get("role") == "assistant")

        if actual_turns == 0:
            return {
                "score": 0.0,
                "details": {
                    "expected_turns": expected_turns,
                    "actual_turns": 0,
                    "efficiency_ratio": 0.0,
                    "comment": "无法获取对话轮次",
                },
            }

        # 效率比 = 预期 / 实际 (上限1.0)
        efficiency_ratio = min(1.0, expected_turns / max(actual_turns, 1))
        score = round(efficiency_ratio, 4)

        return {
            "score": self.validate_score(score),
            "details": {
                "expected_turns": expected_turns,
                "actual_turns": actual_turns,
                "efficiency_ratio": efficiency_ratio,
                "comment": self._comment(efficiency_ratio, expected_turns, actual_turns),
            },
        }

    @staticmethod
    def _comment(ratio: float, expected: int, actual: int) -> str:
        if ratio >= 0.9:
            return f"高效! 预期{expected}轮,实际{actual}轮"
        elif ratio >= 0.6:
            return f"正常,预期{expected}轮,实际{actual}轮"
        else:
            return f"低效,预期{expected}轮,实际用了{actual}轮"
