# Python Toolkit

Production-ready Python service template — FastAPI + Kafka + multi-backend persistence + structured logging + versioned LLM prompts.

Use this as a starting point for any new Python microservice. The template is
opinionated about code structure, error handling, and observability so you can
focus on business logic from day one.

## Stack

| Component | Library |
|---|---|
| REST API | FastAPI + Uvicorn |
| Database (SQL) | SQLAlchemy 2 async + asyncpg (PostgreSQL) |
| Database (NoSQL) | Motor + pymongo (MongoDB) |
| Caching / session | Redis async (hiredis) |
| Migrations | Alembic |
| Messaging | confluent-kafka (librdkafka) |
| LLM — Google | google-genai (Gemini) |
| LLM — OpenAI | openai SDK |
| Config | pydantic-settings |
| Logging | structlog (JSON) |
| Dependency mgmt | Poetry |
| Code quality | ruff + black + mypy strict + pre-commit |
| CI | GitHub Actions (lint → typecheck → test → SonarQube) |

## Quick start

```bash
# 1. Install dependencies
poetry install

# 2. Copy env template and fill in secrets
cp .env.example .env

# 3. Run locally (requires Kafka — see Docker section below)
poetry run uvicorn app.main:app --reload --port 8000
```

Key endpoints:
- `GET /api/v1/health` — liveness probe
- `GET /api/v1/ready` — readiness probe (Redis + Kafka)
- `GET /api/docs` — Swagger UI
- `POST /api/v1/events` — create event
- `GET /api/v1/events/{id}` — get event

## Run with Docker Compose

```bash
# Start app + Kafka + Zookeeper
docker-compose up --build

# Verify
curl http://localhost:8000/api/v1/health
```

## Architecture overview

The service follows **hexagonal (clean) architecture**. Dependencies always
point inward: `api → services → repositories → infrastructure`. The active
persistence backend (`postgres`, `mongodb`, or `redis`) is selected at runtime
via `DB_BACKEND` — all three implement the same `IRepository[T]` Protocol so
services are backend-agnostic. Every HTTP request is assigned a `request_id`
by `RequestLoggingMiddleware`, which is bound to the structlog context so all
log entries within the request carry it automatically. Domain exceptions in
`app/core/exceptions.py` map to HTTP status codes in the FastAPI exception
handler — business logic never returns error codes or touches HTTP directly.

See `docs/adr/` for architecture decision records.

## Database configuration

Select the persistence backend via `DB_BACKEND`:

```bash
# PostgreSQL (default) — run migrations before first start
DB_BACKEND=postgres
POSTGRES_URL=postgresql+asyncpg://user:password@localhost:5432/python_toolkit
poetry run alembic upgrade head

# MongoDB
DB_BACKEND=mongodb
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=python_toolkit

# Redis
DB_BACKEND=redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600
```

### Alembic migrations (PostgreSQL only)

```bash
# Apply all pending migrations
poetry run alembic upgrade head

# Generate a new migration from ORM model changes
poetry run alembic revision --autogenerate -m "short description"

# Rollback one step
poetry run alembic downgrade -1
```

## LLM services

Both `GeminiService` and `OpenAIService` satisfy the `LLMService` Protocol.
They look up prompts from the registry, render them with variables, and call
the respective API.

```python
from app.api.deps import GeminiServiceDep, OpenAIServiceDep

# In a FastAPI endpoint:
async def my_endpoint(gemini: GeminiServiceDep) -> ...:
    result = await gemini.generate_async("my-prompt", "1.0.0", {"key": "value"})
    return result.text
```

Required env vars:

```bash
# Google Gemini
GEMINI_API_KEY=your-key
GEMINI_DEFAULT_MODEL=gemini-2.0-flash   # optional
GEMINI_TIMEOUT_SECONDS=60               # optional

# OpenAI
OPENAI_API_KEY=your-key
OPENAI_DEFAULT_MODEL=gpt-4o             # optional
OPENAI_TIMEOUT_SECONDS=60              # optional
```

## Prompt registry

Add a versioned prompt at `app/prompts/registry/<name>/<version>.yaml`:

```yaml
name: my-prompt
version: "1.0.0"
description: What this prompt does
model: gemini-2.0-flash
author: Your Name
created_at: "2024-01-01"
variables: [task, context]
template: |
  Do {task} given {context}.
metadata:
  tags: [v1]
```

Render in code:

```python
registry.render("my-prompt", "1.0.0", {"task": "summarise", "context": "..."})
```

Templates are cached in memory for the process lifetime. Adding a new version
requires a process restart.

## Development

```bash
# Lint + auto-fix
poetry run ruff check app tests --fix
poetry run black app tests

# Type check (strict)
poetry run mypy app --strict

# Run all tests with coverage (must stay ≥ 80%)
poetry run pytest

# Run a single test file
poetry run pytest tests/unit/test_kafka_producer.py -v

# Run a single test by name
poetry run pytest tests/unit/test_prompts.py::test_render_raises_on_missing_variable -v

# Install pre-commit hooks (run once after cloning)
poetry run pre-commit install
```

## Code quality & CI

The CI pipeline runs: `ruff` → `black --check` → `mypy --strict` → `pytest --cov` → SonarQube scan.

**SonarQube** is configured in `sonar-project.properties`. It reads the
`coverage.xml` report produced by `pytest-cov`. To generate it locally:

```bash
poetry run pytest --cov=app --cov-report=xml
```

Then upload via the SonarQube scanner or let CI handle it.

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `DB_BACKEND` | `postgres` | `postgres` \| `mongodb` \| `redis` |
| `POSTGRES_URL` | — | asyncpg connection string |
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DATABASE` | `python_toolkit` | MongoDB database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `REDIS_CACHE_TTL` | `3600` | Default TTL in seconds |
| `ENVIRONMENT` | `development` | `production` enables stricter settings |
| `DEBUG` | `false` | Enables SQLAlchemy query logging |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker addresses |
| `KAFKA_AUDIT_TOPIC` | `audit.requests` | Topic for HTTP audit log |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `LOG_JSON` | `true` | `false` for human-readable console output |
| `GEMINI_API_KEY` | — | Required to use GeminiService |
| `GEMINI_DEFAULT_MODEL` | `gemini-2.0-flash` | Default Gemini model |
| `OPENAI_API_KEY` | — | Required to use OpenAIService |
| `OPENAI_DEFAULT_MODEL` | `gpt-4o` | Default OpenAI model |

## Deploy

The `Dockerfile` uses a multi-stage build with a non-root user. Pass
configuration via a `.env` file, k8s `ConfigMap`, or `Secret`. Run
`alembic upgrade head` as an init container before the app starts when using
the PostgreSQL backend.

## Contributing

1. Branch from `main`, name it `feat/...` or `fix/...`.
2. Run `poetry run pre-commit install` once after cloning.
3. All PRs must pass CI (lint + typecheck + tests ≥ 80% coverage).
4. For architecture-changing decisions, add an ADR in `docs/adr/` — see
   existing records for the template.

## License

MIT
