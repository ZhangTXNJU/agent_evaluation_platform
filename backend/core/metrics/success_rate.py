"""
任务成功率指标 (T027)
通过检查Agent输出是否满足预期约束条件来计算得分。

评估逻辑：
- 解析Agent输出中的关键信息（目的地、天数、预算、关键词）
- 与预期约束进行对比匹配
- 每项约束匹配得分后取平均
"""

from typing import Any, Dict, List
from core.metrics.base import BaseMetric
from core.metric_factory import MetricRegistry


@MetricRegistry.register("success_rate")
class SuccessRateMetric(BaseMetric):
    """任务成功率的指标——检查Agent规划是否满足用户约束"""

    description = "检查Agent输出是否满足预期约束条件（目的地、天数、预算、关键词覆盖率）"

    def compute(self, case_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算单个测试用例的成功率得分。

        case_result包含:
            - case_meta: 测试用例的预期约束
            - agent_output: Agent的输出文本/JSON
        """
        case_meta = case_result.get("case_meta", {})
        agent_output = case_result.get("agent_output", {})
        output_text = self._get_output_text(agent_output)

        constraints = case_meta.get("expected_constraints") or {}

        # 逐项检查约束，每项得分0或1
        checks: Dict[str, float] = {}
        total_checks = 0

        # 检查目的地
        if "destination" in constraints and constraints["destination"]:
            total_checks += 1
            dest = constraints["destination"]
            checks["destination"] = 1.0 if dest in output_text else 0.0

        # 检查天数
        if "days" in constraints and constraints["days"]:
            total_checks += 1
            days = constraints["days"]
            checks["days"] = 1.0 if str(days) in output_text else 0.0

        # 检查预算限制
        if "budget_limit" in constraints and constraints["budget_limit"] is not None:
            total_checks += 1
            budget = constraints["budget_limit"]
            checks["budget_limit"] = 1.0 if str(budget) in output_text else 0.0

        # 检查必须包含的关键词
        if (
            "must_include_keywords" in constraints
            and constraints["must_include_keywords"]
        ):
            keywords: List[str] = constraints["must_include_keywords"]
            total_checks += len(keywords)
            for kw in keywords:
                checks[f"keyword:{kw}"] = 1.0 if kw in output_text else 0.0

        # 计算总分
        if total_checks == 0:
            score = 1.0  # 无约束时默认通过
        else:
            score = sum(checks.values()) / total_checks

        return {
            "score": self.validate_score(score),
            "details": {
                "checks": checks,
                "passed": sum(1 for v in checks.values() if v >= 1.0),
                "total": total_checks,
            },
        }

    def _get_output_text(self, agent_output: Any) -> str:
        """从Agent输出中提取文本（兼容dict和string格式）"""
        if isinstance(agent_output, str):
            return agent_output
        if isinstance(agent_output, dict):
            # 尝试从常见字段提取
            for key in ("plan", "output", "text", "content", "result"):
                val = agent_output.get(key)
                if isinstance(val, str):
                    return val
            # 无文本字段时，将整个dict转为字符串
            return str(agent_output)
        return str(agent_output)
