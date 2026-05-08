"""
工具调用准确性指标 (T028)
对比Agent实际调用的工具序列与预期工具序列，使用模糊匹配算法。

评估逻辑：
- 从trace事件中提取所有tool_call类型事件
- 与预期工具序列进行序列比对
- 容忍顺序差异（使用集合重叠 + 顺序惩罚）
"""

from typing import Any, Dict, List
from core.metrics.base import BaseMetric
from core.metric_factory import MetricRegistry


@MetricRegistry.register("tool_accuracy")
class ToolAccuracyMetric(BaseMetric):
    """工具调用准确性——对比实际工具序列与预期序列"""

    description = "对比Agent实际调用的工具序列与预期序列，容忍合理的顺序差异"

    def compute(self, case_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算工具调用准确性得分。

        case_result包含:
            - case_meta: 测试用例元数据（含expected_tool_sequence）
            - agent_trace: Agent执行追踪事件列表
        """
        case_meta = case_result.get("case_meta", {})
        agent_trace = case_result.get("agent_trace", [])

        expected = case_meta.get("expected_tool_sequence") or []
        actual = self._extract_tool_sequence(agent_trace)

        # 边界情况
        if not expected:
            return {"score": 1.0, "details": {"reason": "无需验证的工具序列", "expected": [], "actual": actual}}

        # ── 计算得分 ──
        # 1. 召回率（期望的工具被调用了多少）
        expected_set = set(expected)
        actual_set = set(actual)
        intersection = expected_set & actual_set
        recall = len(intersection) / len(expected_set) if expected_set else 1.0

        # 2. 精确率（实际调用了多少相关工具，忽略无关工具）
        precision = len(intersection) / len(actual_set) if actual_set else 0.0

        # 3. 顺序分（Longest Common Subsequence / 期望长度）
        lcs_len = self._lcs_length(expected, actual)
        order_score = lcs_len / len(expected) if expected else 1.0

        # 综合得分：召回40% + 精确20% + 顺序40%
        score = 0.4 * recall + 0.2 * precision + 0.4 * order_score

        # 找出遗漏和多余的工具
        missing = list(expected_set - actual_set)
        extra = list(actual_set - expected_set)

        return {
            "score": self.validate_score(score),
            "details": {
                "expected_sequence": expected,
                "actual_sequence": actual,
                "matched": sorted(list(intersection)),
                "missing": missing,
                "extra": extra,
                "recall": round(recall, 3),
                "precision": round(precision, 3),
                "order_score": round(order_score, 3),
            },
        }

    def _extract_tool_sequence(self, trace: List[Dict]) -> List[str]:
        """从trace事件中提取工具调用序列"""
        tools = []
        for event in trace:
            if event.get("event_type") == "tool_call":
                tool_name = None
                data = event.get("data", {})
                if isinstance(data, dict):
                    tool_name = data.get("tool_name") or data.get("name") or data.get("function")
                if not tool_name and isinstance(event.get("data"), str):
                    tool_name = event.get("data")
                if tool_name:
                    tools.append(tool_name)
        return tools

    def _lcs_length(self, a: List[str], b: List[str]) -> int:
        """计算最长公共子序列的长度（动态规划）"""
        m, n = len(a), len(b)
        if m == 0 or n == 0:
            return 0

        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n]
