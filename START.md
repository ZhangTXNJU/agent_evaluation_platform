# Agent 评估平台 — 使用指南

## 项目简介

Agent 评估平台是一个全栈 Web 应用，用于对旅行规划 AI Agent 进行自动化、多维度评估。平台支持两种评估模式：

- **单轮评估**：给 Agent 发送一个任务请求，拿回结果，从成功率、工具准确度、LLM-as-Judge 推理质量、响应时间四个维度评分
- **多轮对话评估**（新增）：由一个 LLM 扮演"用户"（User Simulator），与被测试 Agent 进行多轮对话，根据对话过程和结果综合评估 Agent 的对话能力

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React + Ant Design + Tailwind CSS |
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| 被评估 Agent | MyAgent（基于 LLM 的自主旅行规划 Agent） |

## 目录结构

```
agent_evaluate_platform/
├── backend/              # FastAPI 后端
│   ├── main.py           # 应用入口
│   ├── api/              # REST 路由 (tasks, datasets, compare)
│   ├── core/             # 核心引擎
│   │   ├── executor.py   # 评估执行引擎
│   │   ├── user_simulator.py  # 多轮对话用户模拟器
│   │   ├── adapters/     # Agent 协议适配器
│   │   └── metrics/      # 指标计算插件
│   ├── models/           # ORM 模型
│   ├── schemas/          # Pydantic 数据校验
│   └── eval_platform.db # SQLite 数据库（含评估历史）
├── frontend/             # React 前端
│   └── src/pages/        # 页面组件
├── myagent/              # 被测试的 Agent
│   ├── api_server.py     # HTTP API 包装层
│   └── agent_core.py     # Agent 核心逻辑
├── datasets/             # 预设数据集 JSON
├── start.ps1             # 一键启动脚本 (PowerShell)
├── stop.ps1              # 一键停止脚本 (PowerShell)
└── START.md              # 本文档
```

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Git

### 1. 克隆项目

```bash
git clone git@github.com:ZhangTXNJU/agent_evaluation_platform.git
cd agent_evaluation_platform
```

### 2. 安装依赖

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd ../frontend
npm install
```

### 3. 配置 API Key

项目使用 DeepSeek API 驱动 User Simulator 和 LLM Judge 指标。配置 API Key：

```powershell
# 在 backend 目录下创建 .env 文件
cd backend
@"
OPENAI_API_KEY=sk-your-deepseek-api-key
OPENAI_API_BASE=https://api.deepseek.com/v1
LLM_JUDGE_MODEL=deepseek-chat
SIMULATOR_MODEL=deepseek-chat
"@ | Out-File -Encoding utf8 .env
```

> 注意：`.env` 文件已在 `.gitignore` 中排除，不会被提交到仓库。

### 4. 初始化数据库（首次使用）

```bash
cd backend
python init_db.py
```

这会创建 SQLite 数据库并导入种子数据集。如果仓库已包含 `eval_platform.db`（含评估历史），跳过此步。

### 5. 启动全部服务

**一键启动：**

```powershell
# 在项目根目录
.\start.ps1
```

**或分别启动：**

```powershell
# 终端 1：启动 MyAgent（被测试 Agent）
cd myagent
.\.venv\Scripts\Activate.ps1
$env:PORT = "9003"
python api_server.py

# 终端 2：启动后端
cd backend
python -m uvicorn main:app --port 8001

# 终端 3：启动前端
cd frontend
npm run dev
```

### 6. 打开前端

浏览器访问 **http://localhost:5173**

### 7. 停止服务

```powershell
.\stop.ps1
```

---

## 使用流程

### 单轮评估

1. 点击首页 **"创建评估任务"** 按钮
2. 填写任务信息：

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| 任务名称 | 任意名称 | "MyAgent 单轮测试" |
| 评估模式 | 选择 **单轮** | single_turn |
| Agent 端点 | MyAgent 的 HTTP URL | `http://localhost:9003/api/eval/run` |
| 适配器 | 选择 **native** | native |
| 数据集 | 选择 **旅行规划Agent测试数据集** | 10个用例 |
| 指标 | 勾选 success_rate / tool_accuracy / llm_judge / response_time | 全选 |
| Agent版本 | 任意版本号 | v1.0.0 |

3. 点击 **"创建并执行"**
4. 跳转到任务详情页，实时查看进度和结果

### 多轮对话评估

1. 点击首页 **"创建评估任务"** 按钮
2. 填写任务信息：

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| 任务名称 | 任意名称 | "MyAgent 多轮对话测试" |
| 评估模式 | 选择 **多轮对话** | multi_turn |
| Agent 端点 | MyAgent 的 HTTP URL | `http://localhost:9003/api/eval/run` |
| 适配器 | 选择 **native** | native |
| 数据集 | 选择 **多轮对话测试集** | 5个用例 |
| 指标 | 勾选 dialogue_quality / task_completion / conversation_efficiency | 全选 |
| Agent版本 | 任意版本号 | v1.0.0 |

3. 展开 **"User Simulator 配置"** 区域：

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| API Base | LLM API 地址 | `https://api.deepseek.com/v1` |
| API Key | LLM API 密钥 | `sk-你的密钥` |
| Model | 模型名称 | `deepseek-chat` |
| Temperature | 创造性控制 (0-1) | `0.7` |

> 如不填写 Simulator 配置，平台会使用 `.env` 中的环境变量作为默认值。

4. 点击 **"创建并执行"**
5. 在任务详情页可查看：
   - 每个用例的完整对话转录本
   - User Simulator 的完成判定和满意度评分
   - 对话质量、任务完成度、对话效率三个维度的指标详情

---

## 测试场景说明

多轮对话测试集包含 5 个场景，覆盖不同难度：

| 用例 ID | 场景 | 难度 | 关键成功标准 |
|---------|------|------|-------------|
| conv_easy_001 | 规划 3 天北京游，预算 3000 元 | easy | 行程含故宫/长城/颐和园，费用在预算内 |
| conv_easy_002 | 咨询杭州景点推荐，周末 2 日游 | easy | 推荐 3 个以上知名景点并说明理由 |
| conv_medium_001 | 带家人（含 6 岁儿童）成都 4 日游 | medium | 含大熊猫基地的亲子行程，节奏适合儿童 |
| conv_medium_002 | 上海 vs 南京 2 日游比较选择 | medium | 从多维度对比分析，给出有说服力的推荐 |
| conv_hard_001 | 多城市行程：广州→厦门→福州→杭州 5 日 | hard | 4 城市交通衔接合理，每个城市至少 1 个景点 |

---

## 指标说明

### 单轮评估指标

| 指标 | 说明 | 评分方式 |
|------|------|---------|
| success_rate | 任务是否满足预期的约束条件（目的地/天数/预算等） | 规则匹配 |
| tool_accuracy | 使用的工具是否与预期工具序列匹配 | 序列对齐算法 |
| llm_judge | 对 Agent 推理链的评分（计划合理性/工具选择/自我修正） | LLM-as-a-Judge |
| response_time | 响应时间是否在可接受范围内 | 分段评分函数 |

### 多轮对话评估指标

| 指标 | 说明 | 评分方式 |
|------|------|---------|
| dialogue_quality | 对话质量（目标达成/回复相关/信息充分/用户体验） | LLM-as-a-Judge |
| task_completion | 任务是否根据成功标准完成 | User Simulator 判定 + LLM 验证 |
| conversation_efficiency | 对话效率（实际轮次 vs 预期轮次） | min(1, expected/actual) |

---

## 适配器说明

平台通过适配器模式支持不同的 Agent 协议。当前提供：

| 适配器 | 说明 | 适用场景 |
|--------|------|---------|
| native | 平台原生三段式契约 `{input, session_config}` → `{output, trace, metrics}` | MyAgent、遵循相同契约的 Agent |
| openai_chat | OpenAI Chat Completions 兼容协议 | 任何兼容 OpenAI Chat API 的 Agent |

---

## 常见问题

### Q: 端口被占用？

```powershell
# 查找并终止占用端口的进程
Get-NetTCPConnection -LocalPort 8001 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### Q: 多轮对话任务一直卡在 running 状态？

可能是后端异常退出导致。在数据库中重置任务状态：

```bash
cd backend
python -c "import sqlite3; conn = sqlite3.connect('eval_platform.db'); conn.execute(\"UPDATE tasks SET status='pending', progress_current=0 WHERE status='running'\"); conn.commit(); conn.close()"
```

### Q: User Simulator 生成的首条消息与场景不一致？

确认数据集用例包含完整的 `scenario` 字段（goal/persona/context/success_criteria）。如无 scenario 字段，平台会自动将 `input` 作为 goal 使用。

### Q: 如何添加新的测试用例？

编辑 `backend/datasets/` 下的 JSON 文件，或在前端数据集管理页面创建新数据集。多轮对话用例的 scenario 格式：

```json
{
  "id": "my_case_001",
  "scenario": {
    "goal": "用户想规划一个3天北京游，预算3000元",
    "persona": "对北京不熟悉的游客，喜欢历史文化，从上海出发",
    "context": "偏好高铁出行，对住宿要求干净即可",
    "success_criteria": "Agent提供了包含故宫、长城、颐和园的行程，交通+住宿+门票在3000元以内"
  },
  "max_turns": 10,
  "expected_turns": 6,
  "difficulty": "easy"
}
```
