# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent评估平台 (Agent Evaluation Platform) — a full-stack web application for automated, multi-dimensional evaluation of a "Travel Planning Autonomous Agent." The platform manages evaluation task lifecycle, combines multiple metric suites, and provides single-result visualization and multi-task comparison analysis.

## Tech Stack

- **Frontend**: React + Ant Design / Tailwind CSS, Recharts or ECharts for charts
- **Backend**: Python FastAPI with async task support
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Task Queue**: background threads (low concurrency) or Celery/Bull
- **Metrics**: Ragas for LLM-as-a-Judge, custom Python scripts

## Architecture

```
Frontend (React) → HTTP REST / WebSocket → Backend (FastAPI) → POST /api/eval/run → Agent Platform (external)
```

Backend modules:
- `api/` — REST endpoints: tasks CRUD, datasets CRUD, evaluation execution/results, comparison
- `core/executor.py` — async evaluation engine: iterates test cases, calls Agent Platform, computes metrics
- `core/metrics/` — pluggable metric calculators: success_rate, tool_accuracy, llm_judge, response_time
- `models/` — SQLAlchemy/ORM models for tasks, datasets

Frontend pages:
- TaskList — table with status badges, action buttons (execute/view/delete/re-run)
- CreateTask — form with dataset dropdown, metrics multi-select, agent endpoint input
- TaskDetail — score cards, metric accordion panels, trace log replay timeline
- CompareView — multi-task selector, radar/bar charts, summary table

## Key API Routes (prefix: `/api/v1`)

- `GET/POST /api/v1/datasets`, `GET/DELETE /api/v1/datasets/{id}`
- `GET/POST /api/v1/tasks`, `GET/DELETE /api/v1/tasks/{id}`, `POST /api/v1/tasks/{id}/execute`
- `GET /api/v1/tasks/{id}/result`, `GET /api/v1/tasks/{id}/result/summary`
- `POST /api/v1/compare`, `GET /api/v1/compare/data?ids=id1,id2`
- `WS /ws/tasks/{task_id}` — task progress push

## External Integration

The platform calls the Agent Platform at `POST /api/eval/run` with `{input, session_config}` and expects `{output, trace, metrics}` in response. The trace contains events of type `thought`, `tool_call`, `observation`. Agent endpoint is configurable per task.

## Development Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Database
```bash
cd backend
python init_db.py  # creates tables and seeds default dataset
```

## Project Structure (planned)

```
eval-platform/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   │   ├── tasks.py
│   │   ├── datasets.py
│   │   └── compare.py
│   ├── core/
│   │   ├── executor.py      # evaluation execution engine
│   │   └── metrics/
│   │       ├── success_rate.py
│   │       ├── tool_accuracy.py
│   │       ├── llm_judge.py
│   │       └── response_time.py
│   ├── models/
│   │   └── task.py
│   └── db.py                # database init
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── TaskList.tsx
│   │   │   ├── CreateTask.tsx
│   │   │   ├── TaskDetail.tsx
│   │   │   └── CompareView.tsx
│   │   └── components/
│   └── package.json
└── datasets/                # preset dataset files
    └── travel_cases.json
```

## Non-functional Constraints

- Max 3 concurrent evaluations
- Single test case timeout: 120 seconds
- 10-case evaluation should complete within 10 minutes
- No authentication (course project)
- New metrics must be addable via a metric factory pattern without modifying the core engine

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
