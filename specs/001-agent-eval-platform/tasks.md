# Tasks: Agent Evaluation Platform

**Input**: Design documents from `/specs/001-agent-eval-platform/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/api-v1.yaml

**Tests**: Not explicitly requested in spec — test tasks are omitted. Add `/speckit-checklist` if tests are desired.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Scaffold backend project: create `backend/` directory structure (main.py, api/, core/, core/metrics/, models/, schemas/, ws/, tests/) per plan.md
- [ ] T002 [P] Create `backend/requirements.txt` with dependencies: fastapi, uvicorn, sqlalchemy, pydantic, httpx, openai (for LLM judge), pytest, httpx (test client)
- [ ] T003 Scaffold frontend project using Vite React+TS template in `frontend/`
- [ ] T004 [P] Install frontend dependencies: antd, @ant-design/icons, echarts, echarts-for-react, react-router-dom
- [ ] T005 [P] Create pre-populated dataset `datasets/travel_cases.json` with 10 travel planning test cases (3 easy, 4 medium, 3 hard)
- [ ] T006 Create `backend/db.py` — SQLAlchemy engine, session factory, Base, init_db() function with FK pragma
- [ ] T007 [P] Create `backend/main.py` — FastAPI app instance, CORS middleware, router includes for api/datasets, api/tasks, api/compare, lifespan for DB init
- [ ] T008 [P] Create `.gitignore` with Python, Node, and IDE patterns

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Create `backend/models/__init__.py` and `backend/models/dataset.py` — Dataset ORM model (id, name, description, cases JSON, created_at) per data-model.md
- [ ] T010 [P] Create `backend/models/task.py` — Task ORM model (id, name, agent_version, dataset_id FK, metrics JSON, agent_endpoint, weight_config JSON, status, progress_current, progress_total, result JSON, error_message, timestamps) per data-model.md
- [ ] T011 Create `backend/schemas/__init__.py` and `backend/schemas/dataset.py` — Pydantic schemas: DatasetCreate, DatasetSummary, DatasetDetail, TestCase per contracts/api-v1.yaml
- [ ] T012 [P] Create `backend/schemas/task.py` — Pydantic schemas: TaskCreate, TaskSummary, TaskListResponse, TaskDetail per contracts/api-v1.yaml
- [ ] T013 Create `frontend/src/services/api.ts` — base HTTP client (axios or fetch wrapper) with baseURL, error handling, typed request/response helpers
- [ ] T014 [P] Create `frontend/src/types/index.ts` — TypeScript type definitions matching API contracts: Dataset, TestCase, Task, TaskCreate, TaskDetail, CaseResult, TraceEvent, CompareData
- [ ] T015 [P] Create `frontend/src/App.tsx` — root layout with React Router (routes for /, /tasks/new, /tasks/:id, /compare), Ant Design ConfigProvider
- [ ] T016 [P] Create `backend/core/__init__.py` and `backend/core/metrics/__init__.py` — metric base class and factory registry
- [ ] T017 [P] Create `backend/core/metrics/base.py` — abstract BaseMetric class with compute(case_result) -> MetricResult interface and class registry decorator

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Dataset Management (Priority: P1)

**Goal**: Users can upload, view, list, and delete test case datasets. The platform ships with a pre-populated travel dataset.

**Independent Test**: Upload a JSON dataset, verify it appears in the list with correct case count, open detail view, delete it. Full CRUD validated without any task dependency.

### Implementation for User Story 1

- [ ] T018 [P] [US1] Implement `backend/api/__init__.py` and `backend/api/datasets.py` — GET /datasets (list), POST /datasets (create with validation), GET /datasets/{id} (detail), DELETE /datasets/{id} (with running task check)
- [ ] T019 [US1] Register datasets router in `backend/main.py` with prefix /api/v1/datasets
- [ ] T020 [P] [US1] Create `frontend/src/pages/DatasetList.tsx` — table showing datasets (name, description, case count, created_at), upload button, delete action with confirmation modal
- [ ] T021 [US1] Add dataset upload modal/component to DatasetList — JSON file selector + text editor, validation feedback
- [ ] T022 [US1] Add dataset detail drawer/modal — expandable view of all test cases with their fields
- [ ] T023 [US1] Wire dataset API calls in `frontend/src/services/api.ts` — listDatasets, getDataset, createDataset, deleteDataset

**Checkpoint**: Dataset CRUD fully functional — upload, list, view, delete all working end-to-end

---

## Phase 4: User Story 2 - Evaluation Task Lifecycle (Priority: P2)

**Goal**: Users can create evaluation tasks (selecting dataset + metrics + endpoint config), view task list with status/progress, execute tasks, delete (non-running) tasks, and re-run from existing config.

**Independent Test**: Create a task with dataset + metrics, view it in the list (status=pending), execute it, observe pending→running→done transition, delete it. Re-run creates a copy.

### Implementation for User Story 2

- [ ] T024 [P] [US2] Implement `backend/api/tasks.py` — POST /tasks (create, validate dataset exists, metrics non-empty), GET /tasks (paginated list, ?status filter), GET /tasks/{id} (detail with result if done)
- [ ] T025 [US2] Add DELETE /tasks/{id} (block if running) and POST /tasks/{id}/execute (trigger async execution) to `backend/api/tasks.py`
- [ ] T026 [US2] Register tasks router in `backend/main.py` with prefix /api/v1/tasks
- [ ] T027 [P] [US2] Implement `backend/core/metrics/success_rate.py` — check agent output against expected_constraints, return 0-1 score per data-model.md
- [ ] T028 [P] [US2] Implement `backend/core/metrics/tool_accuracy.py` — extract tool_call events from trace, fuzzy match with expected_tool_sequence (order-tolerant), return 0-1 score
- [ ] T029 [P] [US2] Implement `backend/core/metrics/llm_judge.py` — call LLM API to evaluate thought chains on plan reasonableness, tool appropriateness, self-correction; return 0-1 score
- [ ] T030 [P] [US2] Implement `backend/core/metrics/response_time.py` — extract elapsed_time from agent metrics or compute from timestamps, normalize to 0-1
- [ ] T031 [US2] Create `backend/core/metric_factory.py` — MetricRegistry class mapping metric name strings to BaseMetric subclasses, with auto-discovery from core/metrics/
- [ ] T032 [US2] Implement `backend/core/executor.py` — EvaluationExecutor class:
  - Runs in background thread pool (max_workers=3)
  - Polls for pending tasks, sets status to running
  - Iterates dataset cases, calls Agent Platform via httpx (120s timeout per case)
  - Computes selected metrics via MetricRegistry
  - Handles case-level errors (marks failed, continues to next case)
  - Updates progress_current after each case
  - Sets status to done/failed on completion, stores result JSON
- [ ] T033 [US2] Wire executor startup in `backend/main.py` lifespan — start executor background loop, graceful shutdown
- [ ] T034 [P] [US2] Create `frontend/src/pages/TaskList.tsx` — table with columns: name, agent_version, dataset name, status (StatusBadge), progress (e.g. "3/10"), created_at, action buttons (Execute / View / Delete / Re-run)
- [ ] T035 [P] [US2] Create `frontend/src/components/StatusBadge.tsx` — colored tag: pending=default, running=processing/blue, done=success/green, failed=error/red
- [ ] T036 [US2] Create `frontend/src/pages/CreateTask.tsx` — form with fields: name (Input), agent_version (Input), dataset_id (Select from API), metrics (Checkbox group: success_rate, tool_accuracy, llm_judge, response_time), agent_endpoint (Input with default), weight_config (optional DynamicForm). Frontend validation: name required, metrics min 1
- [ ] T037 [US2] Create `frontend/src/components/MetricsSelector.tsx` — checkbox group with metric descriptions, at least 1 required validation
- [ ] T038 [US2] Wire task API calls in `frontend/src/services/api.ts` — listTasks, getTask, createTask, deleteTask, executeTask

**Checkpoint**: Full task lifecycle working — create, list, execute, status transitions, delete, re-run all functional

---

## Phase 5: User Story 3 - Single Task Result Analysis (Priority: P3)

**Goal**: Users can open a completed task to see overall score cards, per-metric breakdown accordion panels, per-case pass/fail details, LLM judge comments, and step-by-step trace timeline replay.

**Independent Test**: Open a completed task's detail page, verify score cards display correctly, expand each metric panel to see breakdowns, select a test case and replay its trace step by step.

### Implementation for User Story 3

- [ ] T039 [US3] Add GET /tasks/{id}/result and GET /tasks/{id}/result/summary to `backend/api/tasks.py` per contracts/api-v1.yaml
- [ ] T040 [P] [US3] Create `frontend/src/components/ScoreCard.tsx` — displays overall_score (large number, 0-1), metric_scores as colored bars, execution metadata (duration, timestamps)
- [ ] T041 [US3] Create `frontend/src/pages/TaskDetail.tsx` — top section: task info (name, version, dataset, status, time) + ScoreCard. Middle section: Ant Design Collapse with panels per metric:
  - Success Rate: per-case pass/fail table with constraint check details
  - Tool Accuracy: expected vs actual tool sequence comparison (highlight mismatches)
  - LLM Judge: judge comments text + score distribution
  - Response Time: horizontal bar chart (per-case duration)
- [ ] T042 [US3] Create `frontend/src/components/TraceTimeline.tsx` — Ant Design Timeline component. For each trace event: icon (Thought=💭, ToolCall=🔧, Observation=👁), timestamp, expandable JSON payload. Case selector dropdown to pick which test case's trace to view.
- [ ] T043 [US3] Wire result API calls in `frontend/src/services/api.ts` — getTaskResult, getTaskResultSummary

**Checkpoint**: Full result analysis working — score overview, metric drill-downs, trace replay all functional

---

## Phase 6: User Story 4 - Multi-Task Comparison (Priority: P4)

**Goal**: Users can select 2+ completed tasks and view side-by-side comparison via radar chart, grouped bar chart, and summary data table.

**Independent Test**: Select 2+ completed tasks, open comparison view, verify radar chart renders with correct metric axes, bar chart shows grouped comparisons, summary table lists all scores.

### Implementation for User Story 4

- [ ] T044 [US4] Implement `backend/api/compare.py` — POST /compare (accept {task_ids}, validate ≥2, all must be done, return comparison data), GET /compare/data?ids=id1,id2 (convenience GET)
- [ ] T045 [US4] Register compare router in `backend/main.py` with prefix /api/v1/compare
- [ ] T046 [P] [US4] Create `frontend/src/components/RadarCompare.tsx` — ECharts radar chart: each task = one series, each metric = one axis, legend for task names
- [ ] T047 [P] [US4] Create `frontend/src/components/BarCompare.tsx` — ECharts grouped bar chart: x-axis = metric names, grouped bars per task, value labels on bars
- [ ] T048 [US4] Create `frontend/src/pages/CompareView.tsx` — top section: Ant Design Select (multiple) to pick completed tasks (min 2). Below: RadarCompare, BarCompare, and a summary table (Ant Table) listing each task's scores + overall in rows. Empty state when <2 tasks selected.
- [ ] T049 [US4] Wire compare API calls in `frontend/src/services/api.ts` — compareTasks (POST), compareTasksGet (GET)

**Checkpoint**: Multi-task comparison fully functional — radar, bar, and table views all rendering

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T050 [P] Implement `backend/ws/manager.py` — WebSocket connection manager for /ws/tasks/{task_id} progress push; emit progress events from executor after each case completes
- [ ] T051 [P] Create `frontend/src/services/websocket.ts` — WebSocket hook for real-time task progress updates
- [ ] T052 [P] Add frontend empty states: TaskList empty ("Create your first task"), DatasetList empty ("Upload a dataset"), CompareView <2 selected
- [ ] T053 [P] Add frontend error boundaries and loading states (Spin/Skeleton) for all pages
- [ ] T054 Seed default dataset on first startup — `backend/init_db.py` that creates tables + inserts datasets/travel_cases.json if Dataset table is empty
- [ ] T055 Run through quickstart.md validation — verify all steps work end-to-end on a clean setup

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — Dataset CRUD, no other story dependencies
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 (needs datasets to exist for task creation)
- **User Story 3 (Phase 5)**: Depends on Foundational + US2 (needs completed tasks with results)
- **User Story 4 (Phase 6)**: Depends on Foundational + US2 + US3 (needs multiple completed tasks + metric data)
- **Polish (Phase 7)**: Depends on all implemented user stories

### User Story Dependencies

```
Setup → Foundational → US1 (Dataset CRUD)
                          ↓
                       US2 (Task Lifecycle + Execution Engine)
                          ↓
                       US3 (Result Analysis + Trace Replay)
                          ↓
                       US4 (Multi-Task Comparison)
                          ↓
                       Polish
```

- **US1**: Can start after Foundational — no dependencies on other stories
- **US2**: Requires US1 (datasets must exist to select in task creation form)
- **US3**: Requires US2 (needs executed tasks with results to display)
- **US4**: Requires US2 + US3 (needs completed tasks and metric comparison data)

### Within Each User Story

- Backend endpoints before frontend pages (API must exist before UI consumes it)
- Models/schemas before API endpoints (endpoints depend on schemas)
- Core components before pages (pages import shared components)
- Wire API calls before page integration

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Within US2: all 4 metric calculators (T027-T030) can be implemented in parallel
- Within US2: TaskList (T034) and StatusBadge (T035) can be built in parallel
- Within US4: RadarCompare (T046) and BarCompare (T047) can be built in parallel
- Within Phase 3 (US1): backend endpoint (T018) and frontend page (T020) can be developed in parallel with API contract as reference
- Within Polish: T050, T051, T052, T053 all independent

---

## Parallel Example: User Story 2

```bash
# Launch all metrics in parallel (different files, no shared state):
Task: "Implement success_rate metric in backend/core/metrics/success_rate.py"
Task: "Implement tool_accuracy metric in backend/core/metrics/tool_accuracy.py"
Task: "Implement llm_judge metric in backend/core/metrics/llm_judge.py"
Task: "Implement response_time metric in backend/core/metrics/response_time.py"

# Launch frontend components in parallel:
Task: "Create TaskList page in frontend/src/pages/TaskList.tsx"
Task: "Create StatusBadge component in frontend/src/components/StatusBadge.tsx"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (Datasets) ← Users can upload test cases
4. Complete Phase 4: US2 (Tasks + Execution) ← **MVP: Run evaluations end-to-end**
5. **STOP and VALIDATE**: Create dataset → Create task → Execute → See results in API

### Incremental Delivery

1. Setup + Foundational → Project skeleton ready
2. US1 → Datasets functional → Upload/view/delete test cases
3. US2 → **MVP!** Full evaluation loop working → Create, execute, get results
4. US3 → Rich result visualization → Score drill-down, trace replay
5. US4 → Comparison → Radar/bar charts across tasks
6. Polish → Real-time progress, empty states, seed data

### Suggested MVP Scope

Phases 1-4 (Setup through US2) = MVP. Users can:
- Upload datasets
- Create and run evaluation tasks
- Get raw results via API

Phases 5-6 add visualization and comparison — critical for usability but the evaluation engine is the core deliverable.

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Backend path: `backend/` (not `backend/src/`)
- Frontend path: `frontend/src/`
- Total tasks: 55
