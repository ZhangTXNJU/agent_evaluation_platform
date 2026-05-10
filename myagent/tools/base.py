"""
BaseTool 抽象基类
所有工具必须继承此类并实现抽象方法
"""
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """工具抽象基类，用于Agent核心与工具层的解耦"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称，用于LLM function calling"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述，为LLM提供功能说明"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """工具的JSON Schema参数定义"""
        pass

    @abstractmethod
    def _execute(self, **kwargs) -> Dict[str, Any]:
        """子类实现的实际执行逻辑，返回 data 字段内容"""
        pass

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行工具，自动包装为标准化返回格式，并注入执行元数据。
        返回格式：
        {
            "status": "success" | "error",
            "data": { ..., "execution_metadata": {"duration_ms": int, "provider": str} },
            "error": {"code": "...", "message": "..."}  # 失败时
        }
        """
        start_ts = time.monotonic()
        try:
            result = self._execute(**kwargs)
            duration_ms = int((time.monotonic() - start_ts) * 1000)

            if result.get("status") == "error":
                # 子类主动返回了错误格式
                return result

            # 注入执行元数据
            data = result.get("data", result)
            if isinstance(data, dict):
                data.setdefault("execution_metadata", {
                    "duration_ms": duration_ms,
                    "provider": self._provider_name(),
                })
            return {
                "status": "success",
                "data": data,
            }
        except Exception as exc:
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            return {
                "status": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                },
                "data": {
                    "execution_metadata": {
                        "duration_ms": duration_ms,
                        "provider": self._provider_name(),
                    }
                }
            }

    def _provider_name(self) -> str:
        """子类可覆盖，返回当前使用的API提供商名称"""
        return "mock"

    def to_openai_function(self) -> Dict:
        """转换为OpenAI/DeepSeek function calling格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    @staticmethod
    def error_response(code: str, message: str, **extra) -> Dict[str, Any]:
        """快捷构造错误响应"""
        err = {"code": code, "message": message}
        err.update(extra)
        return {"status": "error", "error": err}
