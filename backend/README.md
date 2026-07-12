# Feature Flag Management System

Application Feature Planning and Release Governance System — a feature flag backend (FastAPI + PostgreSQL + Redis) with a React admin dashboard.

**Current status:** Milestone 1 (Days 1–6) — Foundation. Boolean flags can be created, listed, updated, deleted, and evaluated. The dashboard supports creating, editing, and viewing flags against the live API, with an environment switcher and full error handling.

---

## Project Structure

```
feature-flag-system/
├── backend/          FastAPI + PostgreSQL + Redis
│   ├── app/
│   │   ├── main.py             App entrypoint, CORS, health check, global error handler
│   │   ├── database.py         SQLAlchemy engine/session setup
│   │   ├── models.py           SQLAlchemy models (6 core tables)
│   │   ├── schemas.py          Pydantic request/response schemas
│   │   ├── evaluation_engine.py  Core flag evaluation logic
│   │   ├── redis_client.py     Redis connection
│   │   └── routers/flags.py    Flag CRUD + /evaluate endpoint
│   ├── tests/                  Unit tests for the evaluation engine
│   ├── create_tables.py        Creates all tables from the models
│   ├── requirements.txt
│   └── .env.example
└── dashboard/        React (Vite) admin dashboard
    └── src/
        ├── pages/               Flags, Flag Detail, Environments, Audit Log
        ├── components/          Sidebar, Navbar (env switcher), Flag form modal, shared Dropdown
        ├── constants/           Shared environment id/name/color mapping
        └── context/             Environment selection context
```

## Backend — Setup & Run

1. **Install dependencies**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # edit .env with your actual PostgreSQL and Redis connection strings
   ```
   You need a running PostgreSQL instance and a running Redis instance (locally, via Docker, or a hosted service).

3. **Create the database tables**
   ```bash
   python create_tables.py
   ```

4. **Seed the three environments** (development, staging, production).
   The dashboard assumes environment IDs `1 = development`, `2 = staging`, `3 = production` (a proper Environment API arrives in Day 10 / Milestone 2). Seed them once:
   ```bash
   python -c "
   from app.database import SessionLocal
   from app import models
   db = SessionLocal()
   for name in ['development', 'staging', 'production']:
       db.add(models.Environment(name=name))
   db.commit()
   "
   ```

5. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```
   - API root: http://localhost:8000/
   - Interactive docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health (reflects Postgres + Redis connectivity — make sure Redis is running before a demo, otherwise this one endpoint will report "unhealthy" even though every flag/CRUD/evaluate endpoint works fine without it)

6. **Run the tests**
   ```bash
   pytest tests/ -v
   ```

## Frontend — Setup & Run

```bash
cd dashboard
npm install
npm run dev
```
The dashboard runs at http://localhost:5173 and expects the backend API at http://localhost:8000 (CORS is already configured for this origin in `main.py`).

## API Endpoints (Milestone 1)

| Method | Path              | Description                          |
|--------|-------------------|---------------------------------------|
| GET    | `/health`         | Reports PostgreSQL and Redis connectivity |
| GET    | `/`               | API root / welcome message            |
| POST   | `/flags/`         | Create a flag                         |
| GET    | `/flags/`         | List flags (optionally `?environment_id=`) |
| GET    | `/flags/{flag_id}`| Get a single flag by its database ID  |
| PUT    | `/flags/{flag_id}`| Update a flag                         |
| DELETE | `/flags/{flag_id}`| Delete a flag                         |
| POST   | `/flags/evaluate` | Evaluate a flag for a given key/environment/user context |

> Note: the original task plan referenced `GET/PUT /flags/{key}`. Since a flag's `key` is only unique *within* an environment (not globally), this implementation addresses flags by their database `id` instead, which is unambiguous. Functionally equivalent.

## Flag Fields

| Field | Required? | Notes |
|---|---|---|
| `key` | Yes | Non-empty string, unique per environment |
| `environment_id` | Yes | Must reference an existing environment |
| `type` | No (defaults to `boolean`) | One of `boolean`, `string`, `number` |
| `default_value` | No (defaults to `false`) | The fallback value returned when the flag is disabled, or when no targeting rule matches (Milestone 2) |
| `enabled` | No (defaults to `false`) | Master on/off switch for the flag's logic |
| `description` | No | Optional human-readable notes |
| `owner_team` | No | Optional metadata; not used in evaluation logic |

## Error Handling

- Expected errors (flag not found, duplicate key, invalid environment, invalid input) return `400`/`404`/`422` with a clear `detail` message.
- Any unexpected error (e.g. a database hiccup) is caught by a global exception handler in `main.py` and returns a clean `500` JSON response instead of crashing the server or leaking a stack trace.
- Every `db.commit()` in the flags router is wrapped in try/except with a rollback, so a database error can't corrupt session state or crash a request.
- On the frontend, all API calls check the response status before trusting the response body, so a failed request shows a clear message (with a retry option on the flags list) instead of silently failing or crashing the page. Validation errors (422) are parsed into a readable sentence rather than shown as raw error objects.