"""
评估指标基类 (T017)
定义所有评估指标的抽象接口和新指标注册的工厂模式。

每个指标模块在 core/metrics/ 下独立实现，只需：
1. 继承 BaseMetric
2. 实现 compute() 方法
3. 使用 @MetricRegistry.register("metric_name") 装饰器注册
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseMetric(ABC):
    """
    评估指标抽象基类。

    子类必须：
    - 设置类属性 name（指标名称）
    - 设置类属性 description（指标描述）
    - 实现 compute(case_result) 方法，返回 0-1 范围的分数
    """

    # 指标名称，子类必须覆盖
    name: str = ""
    # 指标描述
    description: str = ""

    @abstractmethod
    def compute(self, case_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算单个测试用例的指标得分。

        Args:
            case_result: 来自Agent Platform的响应数据，包含:
                - output: Agent的输出文本
                - trace: 执行追踪事件列表
                - metrics: Agent自身提供的度量数据
                以及评估用例的预期约束等。

        Returns:
            包含以下字段的字典:
            - score: float (0-1 范围)
            - details: dict (指标详情，用于前端展示)
        """
        ...

    def validate_score(self, score: float) -> float:
        """确保分数在 0-1 范围内"""
        return max(0.0, min(1.0, score))
