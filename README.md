# Task Tracker API

A FastAPI service for creating and managing tasks. PostgreSQL is the source of truth; Redis is used as a best-effort cache, so the API can continue to serve requests when Redis is unavailable.

## API

- `GET /health` — process liveness check.
- `GET /ready` — database readiness and Redis health.
- `POST /tasks` — create a task (starts in `pending` state).
- `GET /tasks` — list tasks; supports `status`, `limit` (1–100), and `offset` query parameters.
- `GET /tasks/{task_id}` — fetch one task.
- `PATCH /tasks/{task_id}` — update the title, description, or status.
- `DELETE /tasks/{task_id}` — delete a task.

Allowed statuses are `pending`, `in_progress`, and `completed`. Interactive API documentation is available at `/docs`.

## Configuration

Set these environment variables for the local or deployed services:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://task_tracker:task_tracker@localhost:5432/task_tracker` | PostgreSQL connection URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL; set to an empty value to disable caching |
| `REDIS_CACHE_TTL_SECONDS` | `30` | Cache lifetime for task reads |

Use secrets or environment configuration supplied by your runtime for real deployments; do not commit credentials in an `.env` file.

## Local development

From the repository root, activate the project virtual environment and start the API:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

The task API requires PostgreSQL. Apply schema changes using Alembic after installing the requirements:

```bash
alembic upgrade head
```

## Tests

```bash
python -m pytest -q
```

The automated tests use an isolated in-memory SQLite database and do not connect to your PostgreSQL or Redis services.
