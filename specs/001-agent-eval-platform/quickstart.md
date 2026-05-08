# Quickstart: Agent Evaluation Platform

**Date**: 2026-05-08

## Prerequisites

- Python 3.11+
- Node.js 18+ (LTS)
- npm 9+

## Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database (creates tables + seeds default dataset)
python init_db.py

# Start server
uvicorn main:app --reload --port 8001
```

Backend runs at `http://localhost:8001`. Interactive API docs at `http://localhost:8001/docs`.

## Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at `http://localhost:5173` (Vite default).

## Quick Verification

1. Open `http://localhost:8001/docs` — verify API docs load with all endpoints
2. `GET /api/v1/datasets` — should return the pre-seeded travel dataset
3. `POST /api/v1/tasks` — create a task with the default dataset and a few metrics
4. `POST /api/v1/tasks/{id}/execute` — trigger execution (requires Agent Platform at configured endpoint)
5. Open `http://localhost:5173` — verify the task list page loads

## Default Dataset

The platform seeds a `datasets/travel_cases.json` file with 10 travel planning test cases:

- 3 easy (single-city, short duration)
- 4 medium (multi-city, moderate constraints)
- 3 hard (tight budget, multi-destination, complex constraints)

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| Agent endpoint (per task) | `http://localhost:8000/api/eval/run` | Configurable in task creation form |
| Backend port | `8001` | Hardcoded in `main.py` |
| Max concurrent tasks | `3` | Hardcoded in `executor.py` |
| Case timeout | `120` seconds | Hardcoded in `executor.py` |

## Project Scripts

```bash
# Backend
cd backend
pytest                          # Run all tests
pytest tests/test_api/          # API tests only
pytest tests/test_core/         # Core engine tests only

# Frontend
cd frontend
npm run dev                     # Dev server with HMR
npm run build                   # Production build
npm run preview                 # Preview production build
npm run test                    # Run tests
npm run lint                    # ESLint
```
