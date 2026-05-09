"""
Agent 适配器模块

提供可插拔的 Agent 协议适配器,让评估平台可以接入不同格式的 Agent 服务:
- native: 平台原生三段式契约 ({input,session_config} -> {output,trace,metrics})
- openai_chat: OpenAI Chat Completions 兼容 API (覆盖 DeepSeek/Moonshot/智谱/通义/Ollama 等)

新增适配器只需:
1. 在本目录新建文件,继承 BaseAgentAdapter,实现 build_request / parse_response
2. 用 @AdapterRegistry.register("name") 装饰器注册
3. 在 PRESETS 列表里加一个预设(可选)
"""

# 触发各适配器注册
from core.adapters.base import BaseAgentAdapter, AdapterRegistry  # noqa: F401
from core.adapters import native  # noqa: F401
from core.adapters import openai_chat  # noqa: F401
from core.adapters.presets import ENDPOINT_PRESETS  # noqa: F401
