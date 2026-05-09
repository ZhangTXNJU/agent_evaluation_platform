"""
Adapter / Endpoint 预设元信息接口

供前端在创建任务页面填充下拉框使用。所有数据均为静态(从 core/adapters/presets.py 读取)。
路由前缀: /api/v1
"""

from typing import Any, Dict, List
from fastapi import APIRouter

from core.adapters.base import AdapterRegistry
import core.adapters  # noqa: F401  触发适配器注册
from core.adapters.presets import ENDPOINT_PRESETS


router = APIRouter(tags=["adapters"])


@router.get("/adapters")
def list_adapters() -> Dict[str, str]:
    """返回所有已注册的适配器及其描述,前端用于动态显示。"""
    return AdapterRegistry.list_all()


@router.get("/endpoint-presets")
def list_endpoint_presets() -> List[Dict[str, Any]]:
    """
    返回常用 Agent 端点预设列表(供前端下拉框)。

    每项: {key, label, description, adapter_type, agent_endpoint, adapter_config}
    """
    return ENDPOINT_PRESETS
