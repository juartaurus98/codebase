# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Python Production Code Standards

You are a senior Python engineer. You MUST follow these standards proactively
on every code change, without waiting for the user to ask. If you detect a
violation in existing code you touch, fix it or flag it explicitly.

## Commands

```bash
# Install dependencies
poetry install

# Run dev server (hot-reload)
poetry run uvicorn app.main:app --reload --port 8000

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

# Database migrations (postgres backend only)
poetry run alembic upgrade head
poetry run alembic revision --autogenerate -m "description"
poetry run alembic downgrade -1

# Run full stack (app + Kafka + Zookeeper)
docker-compose up --build
```

## Architecture

This is a FastAPI service with a **hexagonal / clean architecture**. Dependencies
always point inward: `api → services → repositories → db/infra`. Nothing in
`services/` or `repositories/` may import from `api/`.

### Layer map

```
app/
├── main.py                 FastAPI app factory + lifespan (DB init, Kafka flush)
├── core/                   Zero-dependency foundation: config, logging, exceptions
├── schemas/                Pydantic I/O models only — no logic
├── models/                 SQLAlchemy ORM models (Postgres only)
├── db/                     Engine setup, async session factory, Alembic env
│   └── migrations/         Versioned schema migrations — only path to change schema
├── services/               Business logic; injected with IRepository via constructor
│   ├── llm_base.py         LLMService Protocol (GeminiService + OpenAIService satisfy it)
│   ├── gemini_service.py   Google Gemini via google-genai SDK; stores client in __init__
│   └── openai_service.py   OpenAI chat completions; stores client in __init__
├── repositories/           I/O only — no business logic
│   ├── base.py             IRepository[T] Protocol (save / get_by_id / list_all)
│   ├── sql/                PostgresEventRepository (AsyncSession)
│   ├── nosql/              MongoEventRepository (AsyncIOMotorDatabase)
│   └── cache/              RedisEventRepository (Redis[str])
├── kafka/                  Module-level producer singleton; consumer with retry + DLQ
├── prompts/                Versioned YAML prompt registry
├── middleware/             RequestLoggingMiddleware: injects request_id + Kafka audit
├── api/
│   ├── deps.py             All FastAPI Depends factories live here
│   └── v1/endpoints/       Thin HTTP handlers — call service, return BaseResponse[T]
└── utils/                  Shared helpers (generate_request_id)
```

### Key patterns

**Multi-backend repository.** `IRepository[T]` (`repositories/base.py`) is a
structural `Protocol`. Three implementations exist: `PostgresEventRepository`,
`MongoEventRepository`, `RedisEventRepository`. `deps.py::get_event_repository`
reads `settings.db_backend` and returns the correct implementation. Services
depend only on the protocol, never on a concrete class.

**Dependency injection via `deps.py`.** All FastAPI `Depends` factories live in
`app/api/deps.py`. `*Dep` type aliases (`EventServiceDep`, `GeminiServiceDep`, …)
are `Annotated[T, Depends(factory)]` — import the alias, not the factory, in
endpoints.

**Singleton infrastructure.** Kafka producer (`kafka/producer.py`), Redis client
(`repositories/redis_client.py`), and Gemini/OpenAI clients (stored as
`self._client` in each service) are all created once per process. Never
instantiate these inside a request handler or service method.

**structlog context vars.** `RequestLoggingMiddleware` calls
`structlog.contextvars.bind_contextvars(request_id=...)` at request start. Every
subsequent log call in that request automatically includes `request_id` — do not
pass it explicitly to logger calls.

**Response envelope.** All successful responses return `BaseResponse[T]` from
`schemas/base.py`. All errors return `ErrorResponse`. Exception → HTTP mapping is
in `main.py`'s `AppException` handler; domain exceptions live in `core/exceptions.py`.

**Prompt registry.** Add a prompt at
`app/prompts/registry/<name>/<version>.yaml`. Fields: `name`, `version`,
`description`, `model`, `author`, `created_at`, `variables` (list), `template`
(uses `{variable}` syntax), `metadata`. Render via `PromptRegistry.render(name,
version, variables_dict)`. Templates are cached in memory for the process
lifetime.

**Migrations only via Alembic.** Never use `Base.metadata.create_all` in
production. All schema changes go through `alembic revision --autogenerate` +
`alembic upgrade head`. The Alembic env is at `app/db/migrations/env.py`.

### Testing approach

`tests/conftest.py` provides three fixtures used across the suite:

- `reset_kafka_singleton` (autouse) — tears down the Kafka producer between tests
- `mock_producer` — patches `get_producer` with a `MagicMock`
- `client` — `TestClient(create_app())` with Kafka mocked; use for endpoint tests

`asyncio_mode = "auto"` is set in `pyproject.toml` — all `async def` test
functions run automatically without a decorator.

---

## 1. Code Style & Convention (PEP 8)

- Follow PEP 8 strictly. Use `black` formatting (line length 88) and `isort`
  for imports. If these tools are not configured, suggest adding them.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes,
  `UPPER_SNAKE_CASE` for constants, `_leading_underscore` for internal use.
- Type hints are MANDATORY for all public functions, methods, and class
  attributes. Use `from __future__ import annotations` when needed.
- Run `ruff` or `flake8` mentally before proposing code. No unused imports,
  no shadowed variables, no mutable default arguments.
- Docstrings: Google style. Every public module, class, and function gets a
  docstring.

## 2. Design Principles

### SOLID
- **S**ingle Responsibility: one class/function = one reason to change.
- **O**pen/Closed: extend via inheritance/composition, not by editing
  stable code.
- **L**iskov Substitution: subclasses must honor the parent contract.
- **I**nterface Segregation: prefer small `Protocol` / `ABC` over fat
  interfaces.
- **D**ependency Inversion: depend on abstractions (Protocol, ABC), inject
  dependencies via constructor — never instantiate concrete infrastructure
  inside business logic.

### DRY
- Extract repeated logic into functions, decorators, or base classes.
- BUT do not over-abstract: wait for the third repetition (Rule of Three)
  before extracting, unless duplication is clearly harmful.

### KISS
- Prefer straightforward code over clever code. If a junior dev cannot read
  it in 30 seconds, simplify.
- Cyclomatic complexity per function should stay under 10. Flag anything
  above.

### YAGNI
- Do not add parameters, config flags, abstractions, or "future hooks" that
  are not required by a current concrete use case.
- Delete dead code immediately. Do not comment it out.

### Clean Code (Robert Martin)
- Functions: short (ideally under 20 lines), do one thing, descriptive name.
- No magic numbers — use named constants.
- Avoid boolean flag parameters; split into two functions instead.
- Errors via exceptions, not return codes. Catch specific exceptions, never
  bare `except:`.
- Comments explain *why*, not *what*. Code should be self-documenting for
  the *what*.

## 3. Documentation Requirements

You MUST proactively maintain these artifacts. When code changes affect
them, update them in the same change set.

### README.md
Every project root has one. Required sections:
- Project name + one-line description
- Problem it solves / context
- Quick start (install, run, test) — copy-pasteable commands
- Architecture overview (1 paragraph + link to deeper docs)
- Configuration (env vars, with defaults)
- How to contribute / dev setup
- License

### API Documentation (OpenAPI / Swagger)
- For any HTTP API: maintain `openapi.yaml` (or auto-generate via FastAPI's
  built-in schema, drf-spectacular, etc.).
- Every endpoint documents: summary, description, request schema, response
  schema, error responses, auth requirements.
- When adding/changing an endpoint, update the spec in the same commit.

### Inline Comments
- Required for: non-obvious algorithms, workarounds for external bugs,
  performance-critical sections, regulatory/business reasons for unusual
  logic.
- Format: explain *why* and link to issue/ticket if relevant.
- Forbidden: comments that restate the code (`i += 1  # increment i`).

### ADR (Architecture Decision Records)
Location: `docs/adr/NNNN-short-title.md` (zero-padded sequence).

Trigger an ADR when you make or propose:
- A new framework, database, or major library
- A change to layering / module boundaries
- An auth/security model decision
- A data model migration affecting multiple services
- Any decision that is hard to reverse

Template (use exactly):
```
ADR NNNN: <Title>

Status: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
Date: YYYY-MM-DD
Deciders: <names or roles>

Context
What is the problem? What constraints exist?

Decision
What did we decide? Be specific.

Consequences
Positive: ...
Negative: ...
Neutral: ...

Alternatives Considered
Option A — rejected because ...
Option B — rejected because ...
```

When you propose an ADR-worthy change in code, ALSO draft the ADR file and
ask the user to review before committing.

## 4. Proactive Behavior

On every task, BEFORE writing code:
1. Read relevant existing files to understand current style and architecture.
2. State briefly: which standards apply, which files you will touch, whether
   an ADR is needed.
3. If the request conflicts with these standards (e.g., user asks for a
   shortcut that violates SOLID), surface the trade-off and ask before
   proceeding.

After writing code:
1. Self-review against this checklist:
   - [ ] PEP 8 + type hints + docstrings
   - [ ] SOLID / DRY / KISS / YAGNI not violated
   - [ ] Layer boundaries respected
   - [ ] README / OpenAPI / ADR updated if needed
   - [ ] Tests added or updated
2. Report what you changed and any standards-related follow-ups.

## 5. When in doubt
Ask. Better one clarifying question than 200 lines of wrong code.
