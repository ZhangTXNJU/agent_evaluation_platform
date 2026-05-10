"""
Agent 适配器基类 + 注册中心

适配器负责两件事:
1. build_request: 把测试用例翻译成"目标 Agent"听得懂的 HTTP 请求体
2. parse_response: 把 Agent 原始响应翻译成本平台统一的 {output, trace, metrics} 三段式

所有指标计算逻辑只依赖三段式结果,所以接入新 Agent 协议只需新增一个 Adapter。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type


class BaseAgentAdapter(ABC):
    """
    Agent 协议适配器抽象基类。

    子类必须:
    - 通过 @AdapterRegistry.register("name") 装饰器注册
    - 实现 build_request / parse_response
    可选:
    - 重写 headers() 返回额外 HTTP 头(如 Authorization)
    - 重写 timeout_seconds() 给该 Agent 一个不同的超时

    注意: 适配器是无状态的,每次 _call_agent 都会通过 AdapterRegistry.get() 重新创建实例。
    """

    name: str = ""

    # 子类可选覆盖的描述,用于 /endpoint-presets 接口返回给前端展示
    description: str = ""

    @abstractmethod
    def build_request(
        self,
        case_meta: Dict[str, Any],
        adapter_config: Optional[Dict[str, Any]] = None,
        history: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        把测试用例翻译为发给目标 Agent 的 JSON body。

        Args:
            case_meta: 测试用例字典(含 input / expected_constraints / 等)
            adapter_config: 任务级适配器配置(API key、model、自定义参数)
            history: 多轮对话历史 [{"role":"user","content":"..."}, ...],
                     单轮模式为 None

        Returns:
            HTTP POST 的 JSON body
        """

    @abstractmethod
    def parse_response(
        self,
        raw_response: Dict[str, Any],
        adapter_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        把 Agent 原始 JSON 响应翻译为本平台契约: {output, trace, metrics}。

        Returns:
            必须包含三个键:
            - output: dict | str  (success_rate 用)
            - trace:  list[{timestamp, event_type, data}]  (tool_accuracy/llm_judge 用)
            - metrics: dict (可含 elapsed_time、total_tokens 等;response_time 用)
        """

    def headers(
        self, adapter_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """额外 HTTP 头,默认仅 application/json。子类可加 Authorization 等。"""
        return {"Content-Type": "application/json"}

    def timeout_seconds(
        self, adapter_config: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """单用例请求超时(秒);返回 None 表示沿用 executor 的默认 120s。"""
        return None


class AdapterRegistry:
    """
    适配器注册中心(沿用与 MetricRegistry 一致的工厂模式)。

    使用方式:
        @AdapterRegistry.register("openai_chat")
        class OpenAIChatAdapter(BaseAgentAdapter): ...

        adapter = AdapterRegistry.get("openai_chat")
    """

    _registry: Dict[str, Type[BaseAgentAdapter]] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(adapter_cls: Type[BaseAgentAdapter]):
            adapter_cls.name = name
            cls._registry[name] = adapter_cls
            return adapter_cls

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[BaseAgentAdapter]:
        adapter_cls = cls._registry.get(name)
        if adapter_cls is None:
            return None
        return adapter_cls()

    @classmethod
    def list_all(cls) -> Dict[str, str]:
        return {
            name: adapter_cls.description or name
            for name, adapter_cls in cls._registry.items()
        }

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._registry
