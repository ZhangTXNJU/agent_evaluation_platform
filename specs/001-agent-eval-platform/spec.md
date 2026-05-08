# Feature Specification: Agent Evaluation Platform

**Feature Branch**: `001-agent-eval-platform`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: "创建分支吧，我打算开始实现这样的一个agent评估平台了"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dataset Management (Priority: P1)

As a platform user, I need to upload and manage test case datasets so that I have standardized test inputs to evaluate agents against.

**Why this priority**: Datasets are the foundation — without test cases, no evaluation task can be created. This is the first thing a user must set up before any evaluation work.

**Independent Test**: Can be fully tested by uploading a JSON dataset file, verifying it appears in the dataset list with correct case count, viewing its details, and deleting it. Delivers a ready-to-use test case library.

**Acceptance Scenarios**:

1. **Given** the platform has no datasets, **When** a user uploads a valid JSON file containing test cases, **Then** the dataset is stored and appears in the dataset list with its name, description, and case count.
2. **Given** a dataset exists, **When** a user views its details, **Then** all test cases are displayed with their input, expected constraints, and difficulty level.
3. **Given** a dataset exists, **When** a user deletes it, **Then** the dataset and all its cases are removed and no longer appear in the list.
4. **Given** a user uploads an invalid JSON file, **When** the upload is attempted, **Then** the system rejects it with a clear error message indicating the format issue.

---

### User Story 2 - Evaluation Task Lifecycle (Priority: P2)

As a platform user, I need to create, execute, and manage evaluation tasks so that I can run automated assessments of an agent against selected datasets and metrics.

**Why this priority**: This is the core workflow — creating and running evaluation tasks is the primary purpose of the platform. It depends on datasets (P1) being available.

**Independent Test**: Can be fully tested by creating a task (selecting a dataset, choosing metrics, configuring agent endpoint), executing it, and observing the status transition from pending → running → done/failed. Delivers complete evaluation execution capability.

**Acceptance Scenarios**:

1. **Given** at least one dataset exists, **When** a user fills in the task creation form (name, agent version, dataset, metrics, agent endpoint) and submits, **Then** a new task with status `pending` is created and appears in the task list.
2. **Given** a task with status `pending`, **When** the user clicks "Execute", **Then** the task status changes to `running` and the backend begins processing test cases.
3. **Given** a running task, **When** all test cases complete successfully, **Then** the task status changes to `done` and results are stored.
4. **Given** a running task, **When** some test cases fail due to agent errors, **Then** the task continues processing remaining cases and the failed cases are recorded with error details.
5. **Given** a task with status `done` or `failed`, **When** the user clicks "Delete", **Then** the task and its results are removed.
6. **Given** a task with status `running`, **When** the user attempts to delete it, **Then** the system prevents deletion with an appropriate message.
7. **Given** a completed or failed task, **When** the user clicks "Re-run", **Then** a new task is created with the same configuration as the original.
8. **Given** the task list has many tasks, **When** the user views it, **Then** each task shows: name, agent version, dataset name, status, creation time, and progress (e.g., "3/10").

---

### User Story 3 - Single Task Result Analysis (Priority: P3)

As a platform user, I need to view detailed evaluation results for a completed task so that I can understand agent performance across all metrics and inspect execution traces.

**Why this priority**: After running evaluations, users need to analyze results. This is the primary consumption of evaluation data. Depends on tasks being executed (P2).

**Independent Test**: Can be fully tested by viewing a completed task's detail page, verifying the overall score card, expanding each metric panel to see breakdowns, and replaying the agent's execution trace step by step. Delivers actionable insights from evaluation results.

**Acceptance Scenarios**:

1. **Given** a completed task, **When** the user opens its detail page, **Then** an overall score card is displayed with the composite weighted score and individual metric scores.
2. **Given** the detail page, **When** the user expands the success rate metric panel, **Then** each test case's pass/fail status and constraint check details are shown.
3. **Given** the detail page, **When** the user expands the tool accuracy metric panel, **Then** expected vs. actual tool call sequences are displayed side by side with mismatches highlighted.
4. **Given** the detail page, **When** the user expands the LLM judge metric panel, **Then** the judge's textual evaluation and score distribution are shown.
5. **Given** the detail page, **When** the user expands the response time metric panel, **Then** a chart shows per-case and average response times.
6. **Given** the detail page, **When** the user selects a specific test case, **Then** the agent's execution trace is displayed as a step-by-step timeline (thought → tool_call → observation), each step expandable to show full details.

---

### User Story 4 - Multi-Task Comparison (Priority: P4)

As a platform user, I need to compare results across multiple completed tasks so that I can evaluate the impact of different agent versions, prompts, or configurations.

**Why this priority**: Comparison unlocks the platform's strategic value — understanding whether changes improve agent performance. It depends on having multiple completed tasks (P2, P3).

**Independent Test**: Can be fully tested by selecting 2+ completed tasks, entering the comparison view, and verifying that radar charts, bar charts, and a summary table are generated showing metric differences across tasks. Delivers cross-task analytical capability.

**Acceptance Scenarios**:

1. **Given** at least 2 completed tasks, **When** the user selects them and enters the comparison view, **Then** a radar chart is displayed comparing all metric scores across tasks.
2. **Given** the comparison view, **When** the user views the grouped bar chart, **Then** each metric can be compared side by side across selected tasks.
3. **Given** the comparison view, **When** the user views the summary table, **Then** each task's individual metric scores and composite score are listed in a sortable table.
4. **Given** fewer than 2 tasks are selected, **When** the user attempts to compare, **Then** the system prompts to select at least 2 tasks.

---

### Edge Cases

- What happens when the agent endpoint is unreachable during execution? → The affected test case is marked as failed with a connection error message; remaining cases continue.
- What happens when a single test case exceeds the 120-second timeout? → The case is marked as failed with a timeout error; the executor proceeds to the next case.
- What happens when the dataset contains zero test cases? → Task creation should warn or reject empty datasets.
- What happens when the user uploads a dataset with duplicate case IDs? → The system should reject or warn about duplicate IDs.
- What happens when the agent returns a malformed response (missing trace, output, or metrics)? → The case is marked as failed with a data format error; remaining cases continue.
- What happens when all 3 concurrent execution slots are occupied? → Newly triggered tasks remain in `pending` status and are dequeued when a slot becomes available.
- What happens when a user tries to re-run a task whose dataset has been deleted? → The system should prevent re-run and show an appropriate error.
- What happens when the task list is empty? → Display an empty state with guidance to create the first task.
- What happens when the dataset list is empty and a user tries to create a task? → The dataset dropdown is empty; the user is prompted to upload a dataset first.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to upload datasets in JSON format, each containing one or more test cases with unique IDs, input text, expected constraints, expected tool sequences, and difficulty levels.
- **FR-002**: System MUST provide a pre-populated default dataset of at least 10 travel planning test cases covering different difficulty levels.
- **FR-003**: System MUST display all datasets with name, description, and case count in a list view.
- **FR-004**: System MUST allow users to view full dataset details including all test cases.
- **FR-005**: System MUST allow users to delete datasets (and prevent deletion if the dataset is referenced by an active task).
- **FR-006**: System MUST allow users to create evaluation tasks by specifying: task name, agent version identifier, dataset selection, metric selection (at least 1), agent endpoint URL, and optional weight configuration.
- **FR-007**: System MUST support at least 4 metric types: success rate, tool call accuracy, LLM-as-a-Judge reasoning quality, and response time.
- **FR-008**: System MUST allow users to select which metrics to compute for each task (multi-select, minimum 1).
- **FR-009**: System MUST support configurable metric weights for composite score calculation, with equal weights as default.
- **FR-010**: System MUST display all tasks in a paginated list showing: task name, agent version, dataset name, status, creation time, and progress.
- **FR-011**: System MUST support task status lifecycle: `pending` → `running` → `done` / `failed`.
- **FR-012**: System MUST allow manual triggering of task execution (status transition from `pending` to `running`).
- **FR-013**: System MUST execute evaluations asynchronously with a maximum of 3 concurrent tasks.
- **FR-014**: System MUST enforce a 120-second timeout per individual test case.
- **FR-015**: System MUST ensure that a single test case failure does not abort the entire evaluation task.
- **FR-016**: System MUST provide real-time task progress updates (current case / total cases) during execution.
- **FR-017**: System MUST allow deletion of tasks that are not currently running.
- **FR-018**: System MUST allow re-running a completed or failed task by creating a new task with the same configuration.
- **FR-019**: System MUST compute success rate by checking agent output against expected constraints for each test case.
- **FR-020**: System MUST compute tool call accuracy by comparing actual tool call sequences (extracted from trace) with expected sequences, tolerating order variations where semantically equivalent.
- **FR-021**: System MUST compute LLM-as-a-Judge reasoning quality scores by evaluating agent thought chains on dimensions of plan reasonableness, tool selection appropriateness, and self-correction effectiveness.
- **FR-022**: System MUST compute response time from agent elapsed time or call duration.
- **FR-023**: System MUST display a composite overall score (weighted average of selected metrics) for completed tasks.
- **FR-024**: System MUST display per-metric breakdowns for a completed task: success rate by test case, tool accuracy comparison table, LLM judge comments and scores, response time distribution.
- **FR-025**: System MUST provide an agent execution trace viewer that replays thought → tool_call → observation events step by step for any selected test case.
- **FR-026**: System MUST allow users to select 2 or more completed tasks and compare their metric scores via radar chart, grouped bar chart, and summary table.
- **FR-027**: System MUST integrate with an external agent platform via a configurable HTTP endpoint that accepts test input and returns output, trace, and metrics.
- **FR-028**: System MUST add new metric types through a pluggable architecture without modifying the core execution engine.
- **FR-029**: System MUST log key execution steps for debugging purposes.

### Key Entities

- **Dataset**: A named collection of test cases. Attributes: name, description, list of test cases, creation timestamp.
- **Test Case**: A single evaluation input within a dataset. Attributes: unique ID, natural language input, expected constraints (destination, duration, budget, keywords), expected tool call sequence, difficulty level.
- **Task**: An evaluation run configuration and its result. Attributes: name, agent version, selected dataset reference, selected metrics list, agent endpoint URL, optional weight configuration, status (pending/running/done/failed), progress (current/total), result data, timestamps.
- **Trace Event**: A single step in the agent's execution. Attributes: timestamp, event type (thought/tool_call/observation), data payload (content, tool name, parameters, results).
- **Metric Result**: The computed score for one metric on one test case or aggregated across all cases. Attributes: metric name, score value (0-1), detailed breakdown (per-case results, comments).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a dataset and a task within 5 minutes of first accessing the platform.
- **SC-002**: A 10-case evaluation task completes within 10 minutes under normal agent response conditions.
- **SC-003**: System supports at least 3 concurrent evaluations without performance degradation.
- **SC-004**: 100% of test case failures in one case do not cause data loss or abort other cases in the same task.
- **SC-005**: Users can compare up to 5 tasks simultaneously with all charts rendering within 3 seconds.
- **SC-006**: All 4 core metrics (success rate, tool accuracy, LLM judge, response time) produce scores in the 0-1 range with human-readable breakdowns.
- **SC-007**: Trace replay shows all event types (thought, tool_call, observation) in chronological order with expandable detail.
- **SC-008**: New metric types can be added by creating a single new file and registering it, without modifying existing metric or engine code.

## Assumptions

- The external Agent Platform is available and conforms to the expected request/response format (`POST /api/eval/run` with `{input, session_config}` → `{output, trace, metrics}`).
- Target users are developers or researchers evaluating agent performance — no consumer-grade UX polish required.
- No authentication or multi-tenancy is needed (course project scope).
- Desktop web browser is the primary access method; mobile responsiveness is not required for v1.
- The platform uses a file-based or embedded database for data storage (no distributed database setup required).
- A pre-populated travel planning dataset of 10 cases is provided with the platform.
- The platform is deployed on a single machine; horizontal scaling is out of scope.
- The LLM judge metric requires access to an LLM (either local or API-based) for scoring; this dependency is configured separately.
