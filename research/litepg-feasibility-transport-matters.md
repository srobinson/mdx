---
title: Embedded Postgres Feasibility for Transport Matters
type: research
tags: [transport-matters, postgres, embedded-postgres, session-store, feasibility]
summary: Transport Matters can replace Docker Postgres with an app-managed bundled real Postgres, with platform wheel coverage as the largest risk.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

Transport Matters can drop the default Docker Compose Postgres dependency by introducing an embedded Postgres lease that starts before transcript capture and the FastAPI runtime. The database features in use are standard PostgreSQL 17 features, so the hard part is lifecycle, packaging, test conversion, and supported platform coverage.

## Project Metadata

- Language: Python 3.14 backend, React and Electron frontend.
- Backend framework: FastAPI, Uvicorn, Typer CLI.
- Database stack: psycopg 3, psycopg pool, Alembic, PostgreSQL 17.
- Build system: hatchling and hatch vcs through `api/pyproject.toml`; repo gates through `just`.
- fmm status: `.fmm.db` exists and `fmm validate` reported all 757 files indexed and current.

## Architecture

- `api/src/transport_matters/config.py :: Settings`, `resolve_database_url`, and `ensure_settings_scaffold` currently define database URL discovery from env or `$TRANSPORT_MATTERS_HOME/settings.toml`.
- `api/src/transport_matters/session/pool.py :: create_async_pool` centralizes psycopg pool creation from a DSN.
- `api/src/transport_matters/main.py :: lifespan` resolves the DSN, opens the pool, applies migrations, and starts `SessionEventListener`.
- `api/src/transport_matters/addon_runtime.py :: load_runtime` starts transcript capture before the web runtime, so any embedded database lease must be acquired before `load_capture_runtime`.
- `api/src/transport_matters/cli/launch_runtime.py :: preflight_session_store_or_exit` currently blocks launches if an external store is missing or unreachable.

## Key Patterns

- The existing DSN boundary is good. Keep psycopg, Alembic, and DAO code unchanged where possible by injecting a generated DSN.
- A process lifetime lease is the right abstraction. It should own start, bootstrap, DSN, status, and close.
- Capture and API must share one resolution path. Starting Postgres only inside FastAPI would miss the earlier `SessionWriter` startup.

## Detailed Findings

The requested memo is at `~/.mdx/projects/transport-matters-litepg-codebase.md`.

Core finding: `pgembed` is the best fit in the named family because it targets PostgreSQL 17 and has Python 3.14 wheels. `pgserver` is currently PostgreSQL 16.2 and lacks Python 3.14 wheels, while `pg0-embedded` currently targets PostgreSQL 18.

Transport Matters relies on standard PostgreSQL features:

- `api/src/transport_matters/session/writer.py :: SessionWriter._commit_batch` and `api/src/transport_matters/session/listen.py :: SessionEventListener._listen_forever` use LISTEN and NOTIFY.
- `api/migrations/versions/0001_session_store_foundation.py :: upgrade` defines JSONB, stored generated tsvector, and GIN indexes.
- `api/migrations/versions/0002_event_tier1_indexes.py :: upgrade` adds JSONB GIN and expression indexes.
- `api/src/transport_matters/session/migrate.py :: apply_migrations` serializes Alembic with advisory locks.
- `api/src/transport_matters/session/testing.py :: TestDb` assumes an admin DSN that can create and drop per test databases.

## Dependencies

Critical current dependencies are `psycopg[binary,pool]`, `alembic`, `fastapi`, `pydantic-settings`, `mitmproxy`, and `typer`. An embedded path would likely add `pgembed` and remove Docker from the default development and CI path.

## Relevance to Helioy

This change would make Transport Matters closer to the Helioy pre release install model: no Docker, no sudo, no global services, and a single app managed home under `~/.transport-matters`. The same lease pattern may inform other Helioy local service dependencies.

## Open Questions

- Supported platform policy needs a decision before adopting `pgembed` as the default.
- The app needs a choice between stopping Postgres on process exit and leaving it resident.
- `transport-matters db` may need explicit embedded cluster commands.
