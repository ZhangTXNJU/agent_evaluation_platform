"""
工具层入口
自动注册所有工具，提供统一的工具列表供Agent核心使用
"""
from .base import BaseTool
from .attraction import AttractionSearchTool
from .weather import WeatherQueryTool, set_mock_weather_scenario
from .transport import TransportDistanceTool
from .budget import BudgetCurrencyTool, ExchangeRateTool


def get_all_tools() -> list[BaseTool]:
    """返回所有已注册工具的实例列表"""
    return [
        AttractionSearchTool(),
        WeatherQueryTool(),
        TransportDistanceTool(),
        BudgetCurrencyTool(),
        ExchangeRateTool(),
    ]


def get_tool_by_name(name: str) -> BaseTool | None:
    """按名称查找工具"""
    for tool in get_all_tools():
        if tool.name == name:
            return tool
    return None


__all__ = [
    "BaseTool",
    "AttractionSearchTool",
    "WeatherQueryTool",
    "TransportDistanceTool",
    "BudgetCurrencyTool",
    "ExchangeRateTool",
    "get_all_tools",
    "get_tool_by_name",
    "set_mock_weather_scenario",
]
