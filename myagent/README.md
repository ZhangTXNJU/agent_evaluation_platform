# 旅行规划自治 Agent 

该项目实现一个可运行的旅行规划 Agent，满足：

- 不是固定 workflow，而是每一轮由模型自主决策下一步（反思 / 调用工具 / 结束）。
- 具备短期记忆（当前会话事件流）和长期记忆（JSONL 落盘检索）。
- 支持外部工具调用（天气、交通、景点、预算），通过动态加载 `tools` 目录下的工具。
- 在 `.env` 中预留 `BASE_URL`、`API_KEY`、`MODEL_NAME` 等配置。

## 目录

- `cli.py`：CLI 入口（支持 `/status`、`/quit`）
- `agent_core.py`：自治 Agent 循环与核心逻辑
- `memory.py`：短期/长期记忆模块
- `tools/`：各类外部工具模块实现
- `config.py`：环境配置加载
- `.env.example`：配置模板
- `healthcheck.py`：模型接口连通性测试

## 运行说明

1. 创建并激活虚拟环境：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. 安装依赖：
```powershell
pip install -r requirements.txt
```

3. 复制配置模板并填写：
```powershell
copy .env.example .env
```
（确保不要将包含真实 API Key 的 `.env` 提交到仓库中！）

4. 启动交互测试：
```powershell
python cli.py
```
