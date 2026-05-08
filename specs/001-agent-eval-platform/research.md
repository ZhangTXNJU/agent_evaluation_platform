# Research & Technical Decisions: Agent Evaluation Platform

**Date**: 2026-05-08
**Feature**: [spec.md](./spec.md)

## 1. Backend Framework: FastAPI

- **Decision**: Python 3.11 + FastAPI
- **Rationale**: FastAPI provides native async support (critical for concurrent evaluation execution), automatic OpenAPI docs generation (useful for course project documentation), and Pydantic-based validation (clean request/response schemas). Python ecosystem has Ragas and httpx — both needed for LLM judging and agent HTTP calls.
- **Alternatives considered**:
  - **Node.js/Express**: Viable but lacks Ragas (Python-only); would require separate Python service for LLM judge metric.
  - **Flask**: Lacks native async; would need additional worker infrastructure for concurrent tasks.

## 2. Async Task Execution: Background Threads

- **Decision**: `asyncio` + `ThreadPoolExecutor` (max_workers=3) with FastAPI `BackgroundTasks` or `lifespan` event to start the executor loop.
- **Rationale**: The constraint is max 3 concurrent evaluations, each with ~10 HTTP-bound test cases. A thread pool is simpler than Celery (no broker, no extra process) and sufficient for this scale. Each test case calls the external Agent Platform synchronously via httpx; wrapping in `run_in_executor` prevents blocking the event loop.
- **Alternatives considered**:
  - **Celery + Redis**: Overkill — adds broker dependency, worker process management, serialization overhead. Only justified at 50+ concurrent tasks.
  - **Ray**: Heavyweight for single-machine deployment.

## 3. Database: SQLite with SQLAlchemy ORM

- **Decision**: SQLite for development; SQLAlchemy ORM for database-agnostic schema (easy migration to PostgreSQL later).
- **Rationale**: Zero-config, file-based storage fits the single-machine course project constraint. SQLAlchemy abstracts the SQL dialect, so switching to PostgreSQL only requires changing the connection string. JSON fields stored as TEXT (SQLite) / JSONB (PostgreSQL) via SQLAlchemy type decorators.
- **Alternatives considered**:
  - **PostgreSQL from start**: More setup burden; no benefit at single-digit concurrent user scale.
  - **Pure JSON file storage**: No query capability for task listing, filtering, pagination.

## 4. Frontend Stack: React + Ant Design + ECharts

- **Decision**: React 18 + Ant Design 5 + ECharts (via `echarts-for-react`)
- **Rationale**:
  - **React**: Most popular ecosystem, Vite for fast dev builds, strong TypeScript support.
  - **Ant Design**: Provides Table, Form, Card, Collapse, Timeline, Select, Badge, Modal — all components directly mapped to spec requirements. Reduces custom CSS work significantly.
  - **ECharts**: Best-in-class radar chart (critical for multi-task comparison), rich interaction (tooltip, zoom), Chinese documentation. Recharts radar is limited by comparison.
- **Alternatives considered**:
  - **Recharts**: Simpler API but radar chart support is minimal; no built-in timeline component.
  - **Chart.js**: Radar chart available but less polished than ECharts for multi-series comparison.
  - **Tailwind CSS instead of Ant Design**: More design control but requires building all component patterns from scratch — not justified for a course project.

## 5. Metrics Framework: Factory Pattern

- **Decision**: Abstract base class `BaseMetric` with `compute(case_result) -> MetricResult` interface. A `MetricFactory` registry maps metric names to classes. Adding a new metric = create a file in `core/metrics/` + register in factory.
- **Rationale**: Spec requires pluggable metrics without modifying the core engine. Factory pattern is the simplest extensibility mechanism — each metric is isolated, independently testable, and auto-discovered.
- **Alternatives considered**:
  - **Plugin system (importlib)**: More dynamic but adds discovery complexity without benefit at 4-6 metrics scale.
  - **Configuration-only**: Insufficient — custom metrics need custom computation logic, not just parameter tweaks.

## 6. Communication: REST + Polling (WebSocket optional)

- **Decision**: REST API for all CRUD + execution triggering. Polling for progress updates (GET /tasks/{id} every 2-3 seconds). WebSocket as optional enhancement for real-time progress.
- **Rationale**: Polling is simpler to implement and debug. WebSocket adds connection management complexity. For 10-case evaluations (target ≤10 min), polling every few seconds provides adequate UX without the overhead.
- **Alternatives considered**:
  - **SSE (Server-Sent Events)**: Simpler than WebSocket but same connection management concerns; overkill for progress-only updates.
  - **WebSocket-only**: Unnecessary for a platform where the primary interaction is CRUD, not real-time collaboration.

## 7. Project Scaffolding: Vite (Frontend) + Manual (Backend)

- **Decision**: `npm create vite@latest` for React+TS frontend. Manual structure for FastAPI backend (no scaffold tool needed — FastAPI projects are minimal).
- **Rationale**: Vite provides fast HMR, TypeScript out of the box, and optimized builds. FastAPI is lightweight enough that scaffolding tools add more magic than value.

## 8. Summary of Key Tradeoffs

| Tradeoff | Chosen | Rejected | Why |
|----------|--------|----------|-----|
| Async tasks | Thread pool | Celery | Scale ≤3 concurrent, no broker needed |
| Database | SQLite | PostgreSQL | Zero-config, single-machine |
| Charts | ECharts | Recharts | Radar chart quality |
| UI Components | Ant Design | Tailwind | Ready-made complex components (Table, Timeline, Collapse) |
| Progress | Polling | WebSocket | Simpler, adequate for 10-min tasks |
| Metric extension | Factory | Plugin system | 4-6 metrics, factory is sufficient |
