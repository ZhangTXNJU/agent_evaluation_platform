<!--
================================================================================
SYNC IMPACT REPORT
==================
Version Change: N/A (template) → 1.0.0 (initial ratification)
Modified Principles: N/A (all new)
Added Sections:
  - Core Principles (5 principles)
  - Technical Constraints
  - Development Workflow
  - Governance
Removed Sections: None
Templates Requiring Updates:
  - .specify/templates/plan-template.md ✅ (Constitution Check section compatible)
  - .specify/templates/spec-template.md ✅ (User scenarios + requirements compatible)
  - .specify/templates/tasks-template.md ✅ (Phase-based task organization compatible)
  - .specify/templates/checklist-template.md ⚠ pending (not read; no constitution reference expected)
Follow-up TODOs: None
================================================================================
-->

# Agent Evaluation Platform 项目宪法

## 核心原则

### I. 可插拔指标架构 (Pluggable Metric Architecture)

所有评估指标必须通过抽象基类和工厂模式注册，不修改核心执行引擎即可新增指标类型。

- 每个指标以独立模块实现，继承 `BaseMetric` 基类，位于 `backend/core/metrics/` 目录下。
- 新增指标只需创建新文件并在工厂中注册，不得修改 `executor.py` 或已有指标的代码。
- 每个指标模块必须可独立进行单元测试，不依赖其他指标模块。
- 指标输出统一为 0-1 范围的分数，附带可读的详细分解数据。

**理由**: 这是架构的核心非功能性需求（FR-028），确保平台在课程项目结束后仍可持续扩展新的评估维度而不产生回归风险。

### II. 异步评估引擎 (Async-First Execution Engine)

所有评估任务异步执行，引擎负责并发控制、超时处理和错误隔离。

- 同一时间最多 3 个评估任务并发执行，新任务在队列中等待。
- 每个测试用例有 120 秒超时限制，超时后标记失败并继续下一个用例。
- 单个测试用例的失败绝不得中止整个评估任务——必须继续处理剩余用例。
- 任务状态机严格遵循 `pending → running → done/failed`，不得出现非法的状态跳转。
- 只有 `pending`/`done`/`failed` 状态的任务允许删除，`running` 状态的任务禁止删除。

**理由**: 评估耗时较长（10 个用例 10 分钟），异步执行 + 错误隔离保障了平台的健壮性和用户体验。状态机确保数据一致性。

### III. API 优先设计 (API-First Design)

REST API 是前端和后端之间的唯一契约，WebSocket 用于实时推送。

- 所有 API 端点必须在 `specs/001-agent-eval-platform/contracts/api-v1.yaml`（OpenAPI 3.0）中定义后才可实施。
- 前端通过 `frontend/src/services/api.ts` 统一封装 HTTP 请求，不得在页面组件中直接调用 `fetch` 或 `axios`。
- WebSocket 仅用于任务进度推送（`/ws/tasks/{task_id}`），不得用于数据传输。
- API 路径前缀统一为 `/api/v1/`。

**理由**: API 契约作为前后端开发的共同真相源，减少集成摩擦。OpenAPI 文档可供后续自动化测试和工具生成使用。

### IV. 数据完整性与状态管理 (Data Integrity & State Management)

数据库操作必须保障引用完整性，前端展示的状态必须与后端一致。

- Dataset 被 `running` 状态的任务引用时，禁止删除该 Dataset（应用层校验）。
- 前端任务状态徽章必须实时反映后端状态变化（通过 WebSocket 推送 + 轮询回退）。
- 空数据集不得用于创建任务——创建时前端应阻止提交，后端应返回校验错误。
- JSON 字段（Dataset.cases、Task.result）必须校验格式合法性，不符合 schema 的数据拒绝存储。

**理由**: 评估结果的可信度取决于数据一致性。如果数据集被删除但任务仍引用它，或状态显示不同步，用户会失去对平台的信任。

### V. 简洁优先与课程项目范围 (Simplicity First — Course Project Scope)

在课程项目的范围内，选择最简单的可行方案，避免过度工程化。

- 不实现用户认证和多租户——这是课程项目，非生产系统。
- 开发环境使用 SQLite，通过 SQLAlchemy 保持与 PostgreSQL 的 schema 兼容性，以便将来迁移。
- 不实现移动端响应式布局——桌面浏览器是唯一目标平台。
- 前端状态管理使用 React 内置 hooks（useState、useEffect、useContext），不引入 Redux 等第三方状态库，除非确实需要。
- 评估执行使用后台线程（threading），不引入 Celery 或 Bull 等重量级任务队列，除非并发需求超出单机能力。
- 遵循 YAGNI（You Aren't Gonna Need It）原则：只实现已明确要求的功能，不为假想的未来需求预留扩展点。

**理由**: 课程项目时间有限，简洁的技术栈降低开发和学习成本。SQLAlchemy 抽象层确保未来可低成本切换到 PostgreSQL。

## 技术约束

- **后端**: Python 3.11 + FastAPI + SQLAlchemy + Pydantic
- **前端**: TypeScript 5.x + React 18 + Ant Design 5 + ECharts (echarts-for-react)
- **存储**: SQLite（开发） / PostgreSQL 兼容 schema（生产迁移目标）
- **测试**: pytest + httpx（后端），Vitest + React Testing Library（前端）
- **并发上限**: 3 个并行评估任务
- **超时限制**: 单个测试用例 120 秒
- **性能目标**: 10 用例评估 ≤ 10 分钟，图表渲染 ≤ 3 秒
- **部署**: 单机部署，无水平扩展需求

## 开发工作流

- **分支策略**: 功能分支命名遵循 `<编号>-<功能名>` 格式（如 `001-agent-eval-platform`）。
- **规范优先开发**: 功能实现遵循 `spec → plan → tasks → implement` 流程。
  - `spec.md` 定义用户故事、需求、验收场景。
  - `plan.md` 确定技术方案和项目结构。
  - `tasks.md` 生成依赖排序的可执行任务列表。
  - 按任务顺序实施，每个用户故事可独立验证。
- **代码审查**: 每个任务完成后自检——验收场景是否通过，是否引入了回归。
- **提交规范**: 每个任务或逻辑组完成后提交一次，提交信息使用中文描述变更内容。
- **测试策略**: 测试为可选但推荐——核心引擎和 API 端点优先覆盖。

## 治理

本宪法是本项目的最高指导文件，所有代码实现、技术决策和流程变更必须与之保持一致。

- **修正程序**: 宪法修正需要通过 `/speckit-constitution` 命令执行，记录修正内容和理由，并更新版本号。
- **版本策略**: 遵循语义化版本。
  - MAJOR: 原则移除或重新定义，导致向后不兼容的治理变更。
  - MINOR: 新增原则或章节，或现有内容实质性扩展。
  - PATCH: 措辞澄清、排版修正、非语义性完善。
- **合规审查**: 每次 `/speckit-plan` 执行的 Constitution Check 门禁必须根据本宪法逐条检查。
- **运行时指导**: 日常开发细节和命令参考见 `CLAUDE.md`，宪法专注于原则性约束。

**Version**: 1.0.0 | **Ratified**: 2026-05-08 | **Last Amended**: 2026-05-08
