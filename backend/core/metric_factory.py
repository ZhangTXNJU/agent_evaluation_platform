"""
指标工厂注册中心 (T016 / T031)
管理所有评估指标的注册和获取，支持按名称查找指标实例。
"""

from typing import Dict, Type, Optional
from core.metrics.base import BaseMetric


class MetricRegistry:
    """
    指标注册中心——工厂模式实现。

    使用方式：
        # 注册指标
        @MetricRegistry.register("success_rate")
        class SuccessRateMetric(BaseMetric):
            ...

        # 获取指标实例
        metric = MetricRegistry.get("success_rate")

        # 列出所有已注册指标
        metrics = MetricRegistry.list_all()
    """

    # 类变量：存储 {指标名称: 指标类}
    _registry: Dict[str, Type[BaseMetric]] = {}

    @classmethod
    def register(cls, name: str):
        """
        装饰器：将指标类注册到工厂。

        Args:
            name: 指标名称，如 "success_rate"、"tool_accuracy"

        Returns:
            装饰器函数
        """

        def decorator(metric_cls: Type[BaseMetric]):
            metric_cls.name = name
            cls._registry[name] = metric_cls
            return metric_cls

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[BaseMetric]:
        """
        根据名称获取指标实例。

        Args:
            name: 指标名称

        Returns:
            指标实例，如果未找到则返回None
        """
        metric_cls = cls._registry.get(name)
        if metric_cls is None:
            return None
        return metric_cls()

    @classmethod
    def list_all(cls) -> Dict[str, str]:
        """
        列出所有已注册的指标及其描述。

        Returns:
            {指标名称: 指标描述} 字典
        """
        return {
            name: metric_cls.description or name
            for name, metric_cls in cls._registry.items()
        }

    @classmethod
    def get_names(cls) -> list:
        """返回所有已注册的指标名称列表"""
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查指标名称是否已注册"""
        return name in cls._registry
