"""
任务完成度指标 (task_completion)
判断多轮对话中用户的目标是否被Agent完成。

数据来源:
- UserSimulator 的 final_evaluation 结果 (task_completed 字段)
- 兜底: 通过对话历史分析是否达到 success_criteria
"""

from typing import Any, Dict
from core.metrics.base import BaseMetric
from core.metric_factory import MetricRegistry


@MetricRegistry.register("task_completion")
class TaskCompletionMetric(BaseMetric):
    """任务完成度——判断Agent是否完成了用户的对话目标"""

    description = "评估多轮对话中Agent是否成功完成了用户的任务目标(二元:0或1)"

    def compute(self, case_result: Dict[str, Any]) -> Dict[str, Any]:
        agent_output = case_result.get("agent_output", {}) or {}

        # 优先从 UserSimulator 的评估结果中获取
        simulator_eval = agent_output.get("simulator_eval")
        if simulator_eval and isinstance(simulator_eval, dict):
            completed = simulator_eval.get("task_completed", False)
            reason = simulator_eval.get("completion_reason", "")
            satisfaction = simulator_eval.get("user_satisfaction", 0.0)
            return {
                "score": 1.0 if completed else 0.0,
                "details": {
                    "task_completed": completed,
                    "completion_reason": reason,
                    "user_satisfaction": satisfaction,
                    "source": "simulator",
                },
            }

        # 兜底: 从 agent_output 直接检查
        completed = agent_output.get("task_completed")
        if completed is not None:
            return {
                "score": 1.0 if completed else 0.0,
                "details": {
                    "task_completed": bool(completed),
                    "completion_reason": agent_output.get("completion_reason", ""),
                    "user_satisfaction": 0.5,
                    "source": "agent_output",
                },
            }

        # 最终兜底
        return {
            "score": 0.0,
            "details": {
                "task_completed": False,
                "completion_reason": "无法获取任务完成状态",
                "user_satisfaction": 0.0,
                "source": "fallback",
            },
        }
