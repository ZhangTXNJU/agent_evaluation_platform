"""
响应时间指标 (T030)
衡量Agent执行速度和效率。

评估逻辑：
- 从Agent Platform返回的metrics中提取执行时间
- 或通过trace事件时间戳计算总耗时
- 使用分段函数归一化到0-1范围（基于120s超时限制）
"""

from typing import Any, Dict, List
from datetime import datetime
from core.metrics.base import BaseMetric
from core.metric_factory import MetricRegistry


# 响应时间阈值（秒），基于系统120s超时限制
FAST_THRESHOLD = 30  # ≤30s 得满分
SLOW_THRESHOLD = 120  # ≥120s 得最低分


@MetricRegistry.register("response_time")
class ResponseTimeMetric(BaseMetric):
    """响应时间指标——衡量Agent的执行效率"""

    description = "衡量Agent处理单个测试用例的响应时间，归一化到0-1"

    def compute(self, case_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算响应时间得分。

        case_result包含:
            - agent_metrics: Agent返回的metrics（含elapsed_time等）
            - agent_trace: 执行追踪事件（用于计算时间跨度）
        """
        agent_metrics = case_result.get("agent_metrics", {}) or {}
        agent_trace = case_result.get("agent_trace", []) or []

        # 优先从Agent Metrics获取
        elapsed = self._extract_elapsed_time(agent_metrics, agent_trace)

        # 归一化到0-1（越小越好，≤30s满分，≥120s最低0.1分）
        if elapsed <= FAST_THRESHOLD:
            score = 1.0
        elif elapsed >= SLOW_THRESHOLD:
            score = 0.1
        else:
            # 线性插值：30s→1.0, 120s→0.1
            ratio = (elapsed - FAST_THRESHOLD) / (SLOW_THRESHOLD - FAST_THRESHOLD)
            score = 1.0 - ratio * 0.9  # 从1.0线性降到0.1

        return {
            "score": self.validate_score(score),
            "details": {
                "elapsed_seconds": round(elapsed, 2),
                "threshold_fast": FAST_THRESHOLD,
                "threshold_slow": SLOW_THRESHOLD,
            },
        }

    def _extract_elapsed_time(
        self, agent_metrics: Dict[str, Any], trace: List[Dict]
    ) -> float:
        """从多种来源提取响应时间"""

        # 方式1：直接从metrics中获取
        for key in ("elapsed_time", "execution_time", "response_time", "duration"):
            val = agent_metrics.get(key)
            if val is not None and isinstance(val, (int, float)) and val > 0:
                return float(val)

        # 方式2：从trace事件时间戳计算
        if trace and len(trace) >= 1:
            first_ts = self._parse_timestamp(trace[0].get("timestamp"))
            last_ts = self._parse_timestamp(trace[-1].get("timestamp"))
            if first_ts and last_ts and last_ts > first_ts:
                return (last_ts - first_ts).total_seconds()

        # 默认值
        return SLOW_THRESHOLD

    def _parse_timestamp(self, ts: Any) -> datetime | None:
        """解析时间戳字符串或对象"""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
            ):
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue
        return None
