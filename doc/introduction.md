# Agent 评估平台 — 项目介绍

## 项目概述

**Agent 评估平台**（Agent Evaluation Platform）是一个全栈 Web 应用，用于对"旅行规划自主 Agent"进行自动化、多维度的质量评估。

平台的核心理念是：给定一组标准化的测试用例（数据集），自动调用被评估的 Agent，从多个维度（任务成功率、工具调用准确性、推理质量、响应时间）对其输出进行量化打分，并支持单任务结果深度分析和多任务横向对比。

**适用场景**：开发者或研究人员对 Agent 进行版本迭代时，通过批量自动化评估快速了解每次改动对 Agent 整体表现的影响。

---

## 核心功能

平台围绕 4 大用户场景（User Story）构建，按优先级从低到高：

### 1. 数据集管理（P1 — 基础）

上传和管理测试用例数据集，是整个平台的基石。

- 以 JSON 格式上传测试用例集合（名称、描述、用例列表）
- 每个用例包含：自然语言输入、预期约束（目的地/天数/预算/关键词）、预期工具调用序列、难度级别
- 支持数据集列表浏览、详情查看、删除
- 平台内置一个包含 10 个旅行规划测试用例的种子数据集（3 简单 + 4 中等 + 3 困难）

### 2. 评估任务生命周期（P2 — 核心）

创建、执行和管理评估任务，是平台的核心工作流。

- 创建评估任务：选择数据集 + 勾选评估指标 + 配置 Agent 端点 + 自定义权重
- 任务状态机严守 `pending → running → done/failed` 流转
- 异步后台执行：最大 3 并发、单用例 120 秒超时
- 单用例失败绝不中止整体任务——剩余用例继续执行
- 实时进度推送（WebSocket）：前端可看到 `3/10` 的动态进度
- 支持任务列表分页、按状态筛选、删除（非运行中）和重跑

### 3. 单任务结果分析（P3 — 深度分析）

对一次完成的评估任务进行多维度结果剖析。

- 综合评分卡片：加权总分 + 各指标分项得分（彩色进度条）
- 按指标展开的详情面板（折叠面板）：
  - **任务成功率**：逐用例展示每项约束的命中/未命中检查
  - **工具调用准确性**：预期序列 vs 实际序列对比，遗漏/多余工具高亮
  - **LLM 推理评分**：LLM 评审意见 + 计划合理性/工具恰当性/自我修正分数
  - **响应时间**：每个用例的耗时明细
- Agent 执行追踪时间线回放：逐步骤展示 "思考 → 工具调用 → 观察" 事件，支持展开查看完整 JSON 数据

### 4. 多任务对比分析（P4 — 全局视角）

横向对比多个已完成任务的各维度得分，发现变化趋势。

- 雷达图：多任务在多指标上的综合形态对比
- 分组柱状图：逐指标并排对比各任务的得分
- 汇总数据表：所有分数一览，方便排序和导出
- 最少选择 2 个已完成任务才触发对比

---

## 技术栈

| 层面 | 技术选型 | 说明 |
|------|----------|------|
| **后端框架** | Python 3.11 + FastAPI | 异步 REST API，自动生成 OpenAPI 文档 |
| **数据库 ORM** | SQLAlchemy 2.0 | 开发环境 SQLite，可通过改连接串切换到 PostgreSQL |
| **数据校验** | Pydantic 2.x | 请求/响应 Schema 定义 + 自动校验 |
| **前端框架** | React 18 + TypeScript 5.x | SPA 单页应用 |
| **UI 组件库** | Ant Design 5 | 中文友好，丰富的表格/表单/弹窗组件 |
| **图表可视化** | ECharts 5 (echarts-for-react) | 雷达图 + 分组柱状图（按需加载） |
| **HTTP 客户端** | httpx (后端) / fetch (前端) | 后端调用外部 Agent Platform；前端调用平台 API |
| **实时通信** | WebSocket (FastAPI 原生) | 任务执行进度实时推送 |
| **LLM 集成** | openai SDK | LLM-as-a-Judge 指标（可选，需配置 API Key） |
| **测试** | pytest + httpx (后端) / Vitest (前端) | 单元测试 + API 集成测试 |
| **构建工具** | Vite 6 | 前端开发服务器 + 生产构建 |

---

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                     前端 (React SPA)                      │
│  TaskList │ CreateTask │ TaskDetail │ CompareView         │
│  HTTP REST ←→ WebSocket 实时进度                          │
└──────────────────────┬───────────────────────────────────┘
                       │ :5173 (Vite Dev Server → :8001)
                       ▼
┌──────────────────────────────────────────────────────────┐
│                   后端 (FastAPI :8001)                     │
│                                                          │
│  api/datasets.py  api/tasks.py  api/compare.py           │
│         │               │             │                   │
│         ▼               ▼             ▼                   │
│  ┌─────────────────────────────────────────────┐         │
│  │           core/executor.py                   │         │
│  │   后台线程池 (max 3 并发，120s 超时)          │         │
│  │   逐个用例调用 Agent → 计算指标 → 汇总存储    │         │
│  └─────────────────────────────────────────────┘         │
│         │                                                 │
│         ▼                                                 │
│  core/metrics/ (可插拔指标工厂)                            │
│  ├── success_rate.py    # 约束满足检查                     │
│  ├── tool_accuracy.py   # 工具序列模糊匹配 (LCS)           │
│  ├── llm_judge.py       # LLM-as-a-Judge 推理评分          │
│  └── response_time.py   # 响应时间归一化                   │
│                                                          │
│  数据层: SQLAlchemy ORM → SQLite / PostgreSQL             │
│  WebSocket: ws/manager.py → 实时进度推送                   │
└──────────────────────┬───────────────────────────────────┘
                       │ POST /api/eval/run
                       ▼
┌──────────────────────────────────────────────────────────┐
│          外部 Agent Platform (被评估对象)                   │
│  接收 {input, session_config}                             │
│  返回 {output, trace, metrics}                            │
│  trace 格式: [thought | tool_call | observation]          │
└──────────────────────────────────────────────────────────┘
```

---

## 项目目录结构

```
agent_evaluate_platform/
├── backend/                        # Python 后端
│   ├── main.py                     # FastAPI 入口：路由、CORS、生命周期
│   ├── db.py                       # SQLAlchemy 引擎、会话工厂、外键约束
│   ├── init_db.py                  # 数据库初始化 + 种子数据导入
│   ├── requirements.txt            # Python 依赖
│   ├── api/                        # REST API 路由层
│   │   ├── datasets.py             # 数据集 CRUD
│   │   ├── tasks.py                # 任务 CRUD + 执行 + 结果查询
│   │   └── compare.py              # 多任务对比
│   ├── core/                       # 核心业务逻辑
│   │   ├── executor.py             # 评估执行引擎（后台线程）
│   │   ├── metric_factory.py       # 指标注册中心（工厂模式）
│   │   └── metrics/                # 可插拔评估指标
│   │       ├── base.py             # 抽象基类 BaseMetric
│   │       ├── success_rate.py     # 任务成功率指标
│   │       ├── tool_accuracy.py    # 工具调用准确性指标
│   │       ├── llm_judge.py        # LLM 推理评分指标
│   │       └── response_time.py    # 响应时间指标
│   ├── models/                     # SQLAlchemy ORM 模型
│   │   ├── dataset.py              # Dataset 实体
│   │   └── task.py                 # Task 实体（含状态机）
│   ├── schemas/                    # Pydantic 请求/响应模型
│   │   ├── dataset.py              # 数据集相关 Schema
│   │   └── task.py                 # 任务 + 结果 + 对比 Schema
│   ├── ws/                         # WebSocket 管理
│   │   └── manager.py              # 连接管理器（按 task_id 分组推送）
│   └── tests/                      # 后端测试
│       ├── conftest.py             # 测试夹具（内存数据库）
│       ├── test_api/               # API 端点测试
│       └── test_core/              # 核心引擎测试
│
├── frontend/                       # React + TypeScript 前端
│   ├── package.json                # Node 依赖
│   ├── vite.config.ts              # Vite 构建配置（含 API 代理）
│   ├── tsconfig.json               # TypeScript 配置
│   ├── index.html                  # HTML 入口
│   └── src/
│       ├── main.tsx                # React 入口
│       ├── App.tsx                 # 根组件：路由 + 布局 + 导航
│       ├── pages/                  # 页面组件
│       │   ├── TaskList.tsx        # 任务列表（含筛选 + 分页 + 操作按钮）
│       │   ├── CreateTask.tsx      # 创建任务表单
│       │   ├── TaskDetail.tsx      # 任务详情（评分 + 指标面板 + 追踪回放）
│       │   ├── DatasetList.tsx     # 数据集管理（上传 + 查看 + 删除）
│       │   └── CompareView.tsx     # 多任务对比（雷达图 + 柱状图 + 汇总表）
│       ├── components/             # 可复用组件
│       │   ├── StatusBadge.tsx     # 任务状态标签（pending/running/done/failed）
│       │   ├── MetricsSelector.tsx # 指标多选器（带中文描述）
│       │   ├── ScoreCard.tsx       # 综合评分卡片（总分 + 各指标进度条）
│       │   ├── TraceTimeline.tsx   # 执行追踪时间线（thought → tool_call → observation）
│       │   ├── RadarCompare.tsx    # ECharts 雷达图
│       │   └── BarCompare.tsx      # ECharts 分组柱状图
│       ├── services/               # API 调用层
│       │   ├── api.ts              # REST API 客户端封装
│       │   └── websocket.ts        # WebSocket 进度订阅 Hook
│       ├── types/                  # TypeScript 类型定义
│       │   └── index.ts            # 与 OpenAPI 合约对齐的全部类型
│       └── styles/
│           └── global.css          # 全局样式
│
├── datasets/                       # 预置数据集
│   └── travel_cases.json           # 10 个旅行规划测试用例
│
├── specs/                          # 设计文档
│   └── 001-agent-eval-platform/
│       ├── spec.md                 # 功能规格说明
│       ├── plan.md                 # 实现计划
│       ├── data-model.md           # 数据模型
│       ├── tasks.md                # 任务清单（55 个任务）
│       ├── research.md             # 技术选型研究
│       ├── quickstart.md           # 快速入门指南
│       └── contracts/api-v1.yaml   # OpenAPI 3.0 接口合约
│
├── doc/                            # 项目文档
│   └── introduction.md             # 本文档
│
├── .specify/memory/constitution.md # 项目宪法（5 项核心原则）
├── CLAUDE.md                       # AI 辅助开发指引
└── .gitignore
```

---

## 快速开始

### 环境要求

- **Python** ≥ 3.11
- **Node.js** ≥ 18
- **npm** ≥ 9

### 1. 启动后端

```bash
# 进入后端目录
cd backend

# 安装 Python 依赖
pip install -r requirements.txt

# 初始化数据库并导入种子数据（首次启动自动执行）
python init_db.py

# 启动 FastAPI 服务
python -m uvicorn main:app --reload --port 8001
```

后端启动后访问：
- API 文档 (Swagger)：`http://localhost:8001/docs`
- 健康检查：`http://localhost:8001/health`

### 2. 启动前端

```bash
# 进入前端目录
cd frontend

# 安装 Node 依赖
npm install

# 启动 Vite 开发服务器
npm run dev
```

前端启动后访问：`http://localhost:5173`

> Vite 开发服务器已配置 API 代理：所有 `/api` 和 `/ws` 请求自动转发到 `localhost:8001`。

### 3. 开始使用

1. 访问"数据集"页面——平台已预置 10 个旅行规划测试用例
2. 访问"创建任务"页面——选择数据集、勾选评估指标、填写 Agent 端点
3. 点击"执行"——后台自动逐用例调用 Agent 并计算各指标得分
4. 查看"任务详情"——评分卡片、各指标逐用例分析、执行追踪回放
5. 创建第二个任务并执行——进入"任务对比"页面进行多任务雷达图/柱状图对比

---

## API 概览

所有 API 路由前缀：`/api/v1`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/datasets` | 列出所有数据集 |
| `POST` | `/datasets` | 上传新数据集（JSON） |
| `GET` | `/datasets/{id}` | 获取数据集详情（含全部用例） |
| `DELETE` | `/datasets/{id}` | 删除数据集（运行中任务引用时禁止） |
| `GET` | `/tasks` | 分页列出任务（支持 `?status=` 筛选） |
| `POST` | `/tasks` | 创建新评估任务 |
| `GET` | `/tasks/{id}` | 获取任务详情（含结果） |
| `DELETE` | `/tasks/{id}` | 删除任务（运行中禁止） |
| `POST` | `/tasks/{id}/execute` | 触发执行 |
| `GET` | `/tasks/{id}/result` | 获取完整评估结果 |
| `GET` | `/tasks/{id}/result/summary` | 获取结果摘要（仅总分） |
| `POST` | `/compare` | 提交多任务对比 |
| `GET` | `/compare/data?ids=` | GET 方式获取对比数据 |
| `WS` | `/ws/tasks/{task_id}` | WebSocket 实时进度推送 |

详细接口定义见 `specs/001-agent-eval-platform/contracts/api-v1.yaml`（OpenAPI 3.0）。

---

## 评估指标详解

### 任务成功率 (success_rate)

检查 Agent 输出是否满足测试用例的预期约束。逐项匹配目的地、天数、预算和关键词，计算命中率。

### 工具调用准确性 (tool_accuracy)

对比 Agent 实际调用的工具序列与预期序列。使用最长公共子序列（LCS）算法模糊匹配，容忍合理的顺序差异。综合评分 = 召回率 × 40% + 精确率 × 20% + 顺序分 × 40%。

### LLM 推理评分 (llm_judge)

调用外部 LLM 对 Agent 的思考链（thought 事件）从三个维度评分：
- **计划合理性**：规划步骤是否逻辑清晰
- **工具选择恰当性**：选用的工具是否适合当前任务
- **自我修正有效性**：发现错误后的调整能力

需要配置环境变量 `LLM_JUDGE_API_KEY` 或 `OPENAI_API_KEY`。LLM 不可用时返回默认 50 分。

### 响应时间 (response_time)

从 Agent 返回的 metrics 中提取执行耗时，或从 trace 时间戳计算总时长。得分归一化规则：≤30 秒满分（1.0），30~120 秒线性递减至 0.1，≥120 秒最低 0.1 分。

---

## 扩展指南

### 新增评估指标

按"可插拔架构"设计原则，新增指标只需 3 步，不必修改核心引擎：

**1. 创建指标模块**（`backend/core/metrics/` 下新建文件）：

```python
from core.metrics.base import BaseMetric
from core.metric_factory import MetricRegistry

@MetricRegistry.register("my_metric")  # 注册指标名称
class MyMetric(BaseMetric):
    description = "我的自定义指标描述"

    def compute(self, case_result: dict) -> dict:
        # 实现指标计算逻辑，返回 {"score": 0.0~1.0, "details": {...}}
        score = ...
        return {"score": self.validate_score(score), "details": {...}}
```

**2. 导入模块**（在 `backend/core/executor.py` 中添加一行 `import`）：

```python
import core.metrics.my_metric  # 触发自动注册
```

**3. 前端添加展示**：在 `MetricsSelector.tsx` 的 `AVAILABLE_METRICS` 数组中添加新指标的描述信息；在 `TaskDetail.tsx` 的 `MetricDetailPanel` 中添加该指标的详情面板渲染逻辑。

---

## 设计原则

本项目遵循 5 项核心宪法原则（详见 `.specify/memory/constitution.md`）：

1. **可插拔指标架构**：新指标通过工厂模式注册，不修改核心引擎
2. **异步评估引擎**：最大 3 并发、120s 单用例超时、单点故障不终止任务
3. **API 优先设计**：REST + WebSocket，OpenAPI 合约作为前后端共同真相源
4. **数据完整性与状态管理**：严格状态机 + 参照完整性校验
5. **简洁优先**：课程项目范围，SQLite 开发、无认证、React Hooks 状态管理

---

## 非功能性约束

| 约束项 | 值 |
|--------|-----|
| 最大并发评估 | 3 个任务 |
| 单用例超时 | 120 秒 |
| 10 用例评估目标时间 | ≤ 10 分钟 |
| 图表渲染目标 | ≤ 3 秒 |
| 认证 | 无（课程项目） |
| 数据库 | SQLite（可切换 PostgreSQL） |
| 部署 | 单机 |
