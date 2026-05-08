# Implementation Plan: Agent Evaluation Platform

**Branch**: `001-agent-eval-platform` | **Date**: 2026-05-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-agent-eval-platform/spec.md`

## Summary

Build a full-stack web application for automated, multi-dimensional evaluation of a "Travel Planning Autonomous Agent." The platform manages evaluation task lifecycle (create → execute → analyze → compare), computes 4+ pluggable metrics (success rate, tool accuracy, LLM-as-a-Judge, response time), and provides single-result visualization and multi-task comparison with radar/bar charts. Backend is Python FastAPI with async task execution; frontend is React + Ant Design + ECharts.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic, React 18, Ant Design 5, ECharts (via echarts-for-react)
**Storage**: SQLite (dev); PostgreSQL-compatible schema via SQLAlchemy for future migration
**Testing**: pytest + httpx (backend), Vitest + React Testing Library (frontend)
**Target Platform**: Desktop web browser (Linux/Windows/Mac)
**Project Type**: Web application (SPA frontend + REST API backend)
**Performance Goals**: 10-case evaluation ≤ 10 minutes, 3 concurrent evaluations without degradation, chart rendering ≤ 3 seconds
**Constraints**: Max 3 concurrent evaluations, 120s per-case timeout, single-machine deployment, no authentication
**Scale/Scope**: Single-digit concurrent users (course project), ~10-50 evaluation tasks, 4 pages (TaskList, CreateTask, TaskDetail, CompareView)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**No constitution defined.** The project constitution template has not been filled. Skipping gate checks. Run `/speckit-constitution` to define project principles before critical implementation decisions are made.

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-eval-platform/
├── plan.md              # This file
├── research.md          # Phase 0: tech decisions & rationale
├── data-model.md        # Phase 1: entity design
├── quickstart.md        # Phase 1: developer onboarding
├── contracts/           # Phase 1: API contracts
│   └── api-v1.yaml      # OpenAPI 3.0 spec
└── tasks.md             # Phase 2: /speckit-tasks output
```

### Source Code (repository root)

```text
backend/
├── main.py                  # FastAPI app entry, CORS, lifespan
├── db.py                    # Database init, session factory
├── requirements.txt         # Python dependencies
├── api/
│   ├── __init__.py
│   ├── datasets.py          # /api/v1/datasets endpoints
│   ├── tasks.py             # /api/v1/tasks endpoints
│   └── compare.py            # /api/v1/compare endpoints
├── core/
│   ├── __init__.py
│   ├── executor.py           # Evaluation execution engine (async worker)
│   ├── metric_factory.py     # Metric registry & factory pattern
│   └── metrics/
│       ├── __init__.py
│       ├── base.py           # Abstract base metric class
│       ├── success_rate.py   # Constraint satisfaction check
│       ├── tool_accuracy.py  # Tool sequence fuzzy matching
│       ├── llm_judge.py      # LLM-as-a-Judge reasoning quality
│       └── response_time.py  # Response time measurement
├── models/
│   ├── __init__.py
│   ├── task.py               # Task ORM model
│   └── dataset.py            # Dataset ORM model
├── schemas/
│   ├── __init__.py
│   ├── task.py               # Pydantic request/response schemas
│   └── dataset.py            # Pydantic dataset schemas
├── ws/
│   ├── __init__.py
│   └── manager.py            # WebSocket connection manager
└── tests/
    ├── test_api/
    ├── test_core/
    └── conftest.py

frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx              # React entry, router setup
│   ├── App.tsx               # Root layout & routing
│   ├── pages/
│   │   ├── TaskList.tsx      # Task table + actions
│   │   ├── CreateTask.tsx    # Task creation form
│   │   ├── TaskDetail.tsx    # Single result drill-down
│   │   └── CompareView.tsx   # Multi-task comparison
│   ├── components/
│   │   ├── StatusBadge.tsx    # Task status tag
│   │   ├── MetricsSelector.tsx
│   │   ├── ScoreCard.tsx
│   │   ├── TraceTimeline.tsx  # Trace event replay
│   │   ├── RadarCompare.tsx
│   │   └── BarCompare.tsx
│   ├── services/
│   │   ├── api.ts            # HTTP client wrapper
│   │   └── websocket.ts      # WebSocket hook
│   ├── types/
│   │   └── index.ts          # TypeScript type definitions
│   └── styles/
│       └── global.css
└── tests/

datasets/
└── travel_cases.json         # Pre-populated 10 test cases
```

**Structure Decision**: Option 2 (Web application). Separate `backend/` and `frontend/` directories with clear separation of concerns. Backend follows FastAPI conventions with `api/`, `core/`, `models/`, `schemas/` layers. Frontend follows React conventions with `pages/`, `components/`, `services/`, `types/`.

## Complexity Tracking

No constitution violations — constitution is empty, no gates were evaluated.
