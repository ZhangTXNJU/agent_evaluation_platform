"""
Endpoint 预设清单 — 前端下拉框的"常用选项"

每个预设描述一个常见的接入场景:
- key: 标识符
- label: 下拉框显示文字
- description: 鼠标悬停说明
- adapter_type: 用哪个 adapter
- agent_endpoint: 默认 URL(用户可改)
- adapter_config: 默认 adapter 配置(用户可改;敏感字段如 api_key 留空)

新增预设只需在此 list 里加一项,无需改后端逻辑或前端代码。
"""

from typing import Any, Dict, List


ENDPOINT_PRESETS: List[Dict[str, Any]] = [
    # ── native 协议 ─────────────────────────────────────────────
    {
        "key": "native_local",
        "label": "本地原生 Agent (localhost:8000)",
        "description": "对接同项目的旅行 Agent 平台,使用本平台原生三段式契约。",
        "adapter_type": "native",
        "agent_endpoint": "http://localhost:8000/api/eval/run",
        "adapter_config": {},
    },
    {
        "key": "native_custom",
        "label": "自定义原生 Agent",
        "description": "任何按本平台契约 ({input,session_config} -> {output,trace,metrics}) 实现的 Agent。",
        "adapter_type": "native",
        "agent_endpoint": "",
        "adapter_config": {},
    },
    # ── OpenAI 兼容协议 ─────────────────────────────────────────
    {
        "key": "openai_official",
        "label": "OpenAI 官方 (gpt-4o-mini)",
        "description": "OpenAI 官方 Chat Completions 接口,需要 OPENAI_API_KEY。",
        "adapter_type": "openai_chat",
        "agent_endpoint": "https://api.openai.com/v1/chat/completions",
        "adapter_config": {
            "model": "gpt-4o-mini",
            "api_key": "",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
    },
    {
        "key": "deepseek",
        "label": "DeepSeek (deepseek-chat)",
        "description": "DeepSeek 官方,OpenAI 兼容接口。",
        "adapter_type": "openai_chat",
        "agent_endpoint": "https://api.deepseek.com/v1/chat/completions",
        "adapter_config": {
            "model": "deepseek-chat",
            "api_key": "",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
    },
    {
        "key": "moonshot",
        "label": "Moonshot Kimi (moonshot-v1-8k)",
        "description": "月之暗面 Kimi,OpenAI 兼容接口。",
        "adapter_type": "openai_chat",
        "agent_endpoint": "https://api.moonshot.cn/v1/chat/completions",
        "adapter_config": {
            "model": "moonshot-v1-8k",
            "api_key": "",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
    },
    {
        "key": "zhipu",
        "label": "智谱 GLM (glm-4-plus)",
        "description": "智谱 AI GLM,OpenAI 兼容接口。",
        "adapter_type": "openai_chat",
        "agent_endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "adapter_config": {
            "model": "glm-4-plus",
            "api_key": "",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
    },
    {
        "key": "qwen",
        "label": "通义千问 (qwen-plus)",
        "description": "阿里通义千问,使用 OpenAI 兼容模式。",
        "adapter_type": "openai_chat",
        "agent_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "adapter_config": {
            "model": "qwen-plus",
            "api_key": "",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
    },
    {
        "key": "ollama_local",
        "label": "本地 Ollama (llama3.1)",
        "description": "本地 Ollama 服务,无需 API key。",
        "adapter_type": "openai_chat",
        "agent_endpoint": "http://localhost:11434/v1/chat/completions",
        "adapter_config": {
            "model": "llama3.1",
            "api_key": "ollama",  # Ollama 不校验,但 Bearer 头需要非空
            "temperature": 0.3,
            "max_tokens": 1500,
        },
    },
    {
        "key": "openai_compatible_custom",
        "label": "自定义 OpenAI 兼容服务",
        "description": "任何遵循 OpenAI Chat Completions 协议的服务,自行填写 URL、model、api_key。",
        "adapter_type": "openai_chat",
        "agent_endpoint": "",
        "adapter_config": {
            "model": "",
            "api_key": "",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
    },
]
