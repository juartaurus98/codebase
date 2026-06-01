# ADR 0001: Multi-Backend Database Support

**Status**: Accepted  
**Date**: 2026-06-01  
**Deciders**: Development Team

## Context

The FastAPI service initially used Redis exclusively for event persistence via the `EventRepository` class. Redis served as both cache and persistent store, which works well for smaller deployments but has limitations:

- **No schema versioning**: Changes to data structure require manual coordination
- **Limited query capabilities**: Redis lacks complex querying, joins, and indexing
- **Scalability concerns**: Redis is primarily single-node (clusters are complex)
- **Operational overhead**: No built-in migration tooling or data consistency guarantees

The service needed to support:
1. Multiple storage backends for flexibility (PostgreSQL for traditional SQL, MongoDB for document-based, Redis for caching)
2. Schema versioning and migrations (essential for production)
3. Type-safe data persistence with proper ORM abstractions
4. Gradual migration path from Redis-only to multi-backend without breaking changes

## Decision

We have adopted a **multi-backend repository pattern** with the following architecture:

### 1. **Repository Abstraction Layer**
   - Created `IRepository[T]` Protocol defining the persistence interface
   - Three concrete implementations:
     - **PostgreSQL**: Uses SQLAlchemy ORM with Alembic migrations
     - **MongoDB**: Uses Motor (async PyMongo) for schemaless documents
     - **Redis**: Renamed to cache-only repository (for sessions/caching, not persistence)
   
   This follows the Dependency Inversion Principle — business logic (EventService) depends on `IRepository` abstraction, not concrete implementations.

### 2. **Database Layer**
   - **ORM Models** (`app/models/events.py`): SQLAlchemy models define PostgreSQL schema
   - **Alembic Migrations**: Track schema versions sequentially (0001_create_events_table, etc.)
   - **Connection Management** (`app/db/session.py`): Async session factory and lifecycle management
   - **Database Base** (`app/db/base.py`): Shared SQLAlchemy DeclarativeBase

### 3. **Configuration & Dependency Injection**
   - Extended `Settings` with `db_backend` selector and connection URLs for each database
   - Factory function `get_repository()` selects backend based on `db_backend` setting
   - FastAPI Depends() injects appropriate repository at request time

### 4. **Migration Strategy**
   - PostgreSQL: Alembic handles schema migrations (up/down versioning)
   - MongoDB: Schemaless, no migrations needed (documents are flexible)
   - Redis: Cache-only, no persistence migrations
   - Phase 1 (now): Setup infrastructure, all backends coexist
   - Phase 2 (future): Dual-write pattern for gradual data migration
   - Phase 3 (future): Cutover to new backend, deprecate old

## Consequences

### Positive
- ✅ **Schema Versioning**: PostgreSQL migrations provide production-grade schema management
- ✅ **Flexibility**: Switch backends via environment variable (no code changes)
- ✅ **Type Safety**: SQLAlchemy ORM provides compile-time type checking
- ✅ **Gradual Migration**: Can run multiple backends simultaneously, migrate data safely
- ✅ **Extensibility**: New backends can be added without modifying existing code (Open/Closed principle)
- ✅ **SOLID Compliance**: Single Responsibility, Dependency Inversion properly applied
- ✅ **Production Ready**: Alembic migrations, connection pooling, async everywhere

### Negative
- ❌ **Complexity**: More code, more moving parts (3 repository implementations vs 1)
- ❌ **Learning Curve**: Team must learn SQLAlchemy, Alembic, MongoDB patterns
- ❌ **Testing Burden**: Integration tests needed for each backend (3x test coverage)
- ❌ **Operational Overhead**: 3 databases to deploy and maintain in Docker Compose

### Neutral
- 🟡 **Storage Duplication**: Data might be replicated across backends during Phase 2 migration
- 🟡 **Configuration**: More environment variables to manage (POSTGRES_URL, MONGODB_URL, etc.)

## Alternatives Considered

### Alternative 1: Single ORM (SQLAlchemy Only)
**Rejected because**: 
- Abandons flexibility; if PostgreSQL becomes unsuitable later, migration is painful
- NoSQL workloads poorly suited to SQL schema
- Loses option to leverage MongoDB's document flexibility

### Alternative 2: Redis-Only (Status Quo)
**Rejected because**:
- No schema versioning or production migrations
- Limited query capabilities (no JOINs, complex filters)
- Single-node scalability ceiling
- Risk of data loss if not backed up properly

### Alternative 3: Data Layer Abstraction Over ORM
**Rejected because**:
- Over-engineering; the Protocol approach is sufficient
- Adds unnecessary indirection
- Harder to generate migrations from abstract schemas

## Implementation Notes

- **Versioning**: Migrations use `NNNN_description` format (e.g., `0001_create_events_table.py`)
- **Async-First**: All repositories and connections use async/await patterns
- **Error Handling**: Connection errors and missing data raise typed exceptions (NotFoundError, etc.)
- **Testing**: Integration tests verify each backend independently in test environments
- **Documentation**: README includes backend selection guide and migration runbook

## References

- `pyproject.toml`: SQLAlchemy, asyncpg, alembic, motor, pymongo dependencies
- `app/db/migrations/versions/0001_create_events_table.py`: Initial PostgreSQL migration
- `app/repositories/base.py`: IRepository Protocol definition
- `app/core/config.py`: Backend selection and connection URL configuration
- `alembic.ini`: Alembic configuration for async SQLAlchemy
