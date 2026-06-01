# Python Toolkit

Production-ready Python service template — FastAPI + Kafka + structured logging.

## Stack

| Component | Library |
|---|---|
| REST API | FastAPI + Uvicorn |
| Database (SQL) | SQLAlchemy + asyncpg (PostgreSQL) |
| Database (NoSQL) | Motor + pymongo (MongoDB) |
| Caching | Redis (async) |
| Migrations | Alembic (PostgreSQL schema versioning) |
| Kafka | confluent-kafka (librdkafka) |
| Config | pydantic-settings |
| Logging | structlog (JSON) |
| Dependency mgmt | Poetry |

## Quick start

```bash
# 1. Install dependencies
poetry install

# 2. Copy env template
cp .env.example .env

# 3. Run locally (requires Kafka — see Docker section)
poetry run uvicorn app.main:app --reload --port 8000
```

Endpoints:
- `GET /api/v1/health` — liveness probe
- `GET /api/v1/ready`  — readiness probe
- `GET /api/docs`       — Swagger UI

## Run with Docker Compose

```bash
# Start Kafka + app (first run builds the image)
docker-compose up --build

# Verify
curl http://localhost:8000/api/v1/health
```

## Development

```bash
# Lint + format
poetry run ruff check app tests --fix
poetry run black app tests

# Type check
poetry run mypy app --strict

# Tests with coverage
poetry run pytest

# Install pre-commit hooks (run once)
poetry run pre-commit install
```

## Project structure

```
app/
├── core/              config, logging, exceptions
├── db/                database setup (SQLAlchemy, Alembic)
│   └── migrations/    versioned schema migrations
├── models/            ORM models (SQLAlchemy)
├── schemas/           Pydantic models (API in/out)
├── services/          business logic
├── repositories/      I/O abstraction (PostgreSQL, MongoDB, Redis)
├── middleware/        request_id injection + Kafka audit
├── kafka/             producer singleton, consumer wrapper
├── prompts/           versioned YAML prompt registry
├── api/v1/            FastAPI routers + endpoints
└── utils/             shared helpers
```

## Prompt registry

Add a prompt at `app/prompts/registry/<name>/<version>.yaml`:

```yaml
name: my-prompt
version: "1.0.0"
description: What this prompt does
model: claude-sonnet-4-6
author: Your Name
created_at: "2024-01-01"
variables: [task, context]
template: |
  Do {task} given {context}.
metadata:
  tags: [v1]
  eval_score: 0.9
```

Render in code:

```python
from app.prompts.registry import PromptRegistry

registry = PromptRegistry()
text = registry.render("my-prompt", "1.0.0", {"task": "...", "context": "..."})
```

## Database Configuration

Select your persistence backend via `DB_BACKEND`:

```bash
# PostgreSQL (default, with Alembic migrations)
DB_BACKEND=postgres
POSTGRES_URL=postgresql+asyncpg://user:password@localhost:5432/python_toolkit

# MongoDB (schemaless document storage)
DB_BACKEND=mongodb
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=python_toolkit

# Redis (in-memory cache/session store only)
DB_BACKEND=redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600
```

### PostgreSQL Migrations

```bash
# Run pending migrations
poetry run alembic upgrade head

# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Rollback one version
poetry run alembic downgrade -1
```

## Deploy

The `Dockerfile` uses a multi-stage build with a non-root user.  
Set environment variables via `.env` file or k8s `ConfigMap`/`Secret`.

Key env vars:

| Variable | Default | Description |
|---|---|---|
| `DB_BACKEND` | `postgres` | `postgres` \| `mongodb` \| `redis` |
| `POSTGRES_URL` | — | PostgreSQL connection string (asyncpg driver) |
| `MONGODB_URL` | — | MongoDB connection string |
| `ENVIRONMENT` | `development` | `production` activates stricter settings |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker addresses |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `LOG_JSON` | `true` | `false` for human-readable console output |
