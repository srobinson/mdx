---
title: Session Store Postgres Foundation
type: sessions
tags: [backend, transport-matters, session-store, postgres, settings, ci]
summary: Implemented slice 1 Postgres session foundation, settings.toml config, and round 2 CI plus review fixes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Summary

Implemented Transport Matters session store slice 1 on branch `feat/session-1-pg-foundation`, latest commit `af2afc4`, PR #34.

Scope is foundation only. No ingest, tailer, FastAPI, SSE, render, fork, share, or backfill wiring was added.

Key decisions:

- `event` identity is `(session_id, seq)`.
- Provider native ids remain attributes, not keys.
- Session native uniqueness is scoped by `(owner, run_id, provider, native_session_id)`.
- The Alembic baseline is forward only because the Postgres store is durable.
- Database configuration is explicit. There is no silent built in database URL.
- Runtime DB URL resolution is env over `settings.toml`: `TRANSPORT_MATTERS_DATABASE_URL` then `[database] url`.
- Test DB URL resolution is `TRANSPORT_MATTERS_TEST_DATABASE_URL`, then `TRANSPORT_MATTERS_DATABASE_URL`, then `[database] test_url`, then `[database] url`.
- Compose binds local Postgres to `127.0.0.1:${TRANSPORT_MATTERS_DOCKER_PG_PORT:-55432}:5432`.
- GitHub Actions backend tests use a `postgres:17` service and point `TRANSPORT_MATTERS_TEST_DATABASE_URL` at the `postgres` maintenance database.

Round 2 review fixes in `af2afc4`:

- Added Postgres services to `.github/workflows/ci.yml` `backend-test` and `.github/workflows/release.yml` backend gate.
- Kept inline artifact decode code and added focused tests for Claude base64, Codex data URL, and invalid base64.
- Added explicit `kind = 'turn'` filters for DAO IR and text search.
- Added sync and async pool plus transaction lifecycle smoke tests.
- Made the Alembic script template scaffold forward only downgrades.
- Excluded `transport_matters/session/testing.py` from wheels while keeping migrations packaged.
- Removed unused `config.py` env key re-exports.
- Added settings `extra="forbid"` ValidationError coverage.
- Clarified env override fields versus TOML source fields in `Settings`.

## API Contract

No public HTTP API was added in this slice.

Internal DAO contract added:

```typescript
interface SessionRow {
  sessionId: string;
  provider: string;
  cli?: string | null;
  runId: string;
  cwd: string;
  workspaceSlug: string;
  workspaceHash: string;
  nativeSessionId?: string | null;
  minted: boolean;
  sourceDescriptor?: Record<string, unknown> | null;
  homeDir?: string | null;
  owner: string;
  status: "active" | "completed" | "archived";
  title?: string | null;
  parentSessionId?: string | null;
  forkedAtSeq?: number | null;
  startedAt: string;
  createdAt?: string | null;
  updatedAt?: string | null;
}

interface EventRow {
  sessionId: string;
  seq: number;
  kind: "turn" | "meta";
  nativeTurnId?: string | null;
  parentNativeId?: string | null;
  parentSeq?: number | null;
  runId: string;
  provider: string;
  cli: string;
  role?: string | null;
  isSidechain: boolean;
  ts?: string | null;
  model?: string | null;
  raw: Record<string, unknown>;
  ir?: Record<string, unknown> | null;
  sourcePath?: string | null;
  sourceLine?: number | null;
  searchText?: string | null;
}

interface SettingsToml {
  database?: {
    url?: string;
    test_url?: string;
  };
}
```

## Database Changes

Added Alembic baseline `0001_session_store`:

- `session`
- `event`
- `artifact`
- `event_artifact`

Indexes and constraints:

- `session_native_uq` partial unique index on `(owner, run_id, provider, native_session_id)`.
- `session_parent_ix` for fork lineage.
- `event_native_ix` for provider native turn lookup.
- `event_ir_gin` for JSONB containment search.
- `event_fts_gin` over generated `content_tsv`.
- `event_artifact` composite foreign key to `(session_id, seq)`.

Migration packaging:

- Alembic files live under `api/migrations/`.
- Source distribution and wheel include migration files.
- Wheel excludes `transport_matters/session/testing.py`.

## Security Considerations

- SQL access is parameterized through psycopg3.
- JSONB values use psycopg `Jsonb` adaptation.
- Test database creation uses `psycopg.sql.Identifier` for database names.
- GitHub CI uses an isolated Postgres service for no skip session tests.
- Artifact foundation stores inline bytes by value and hashes bytes with blake2b 256.
- Inline artifact decode rejects invalid base64 and unrecognized data URLs.
- No filesystem artifact capture was enabled.
- Missing database config raises actionable guidance instead of connecting to a guessed host.
- No public endpoint, auth surface, CORS change, or rate limiting change was introduced.

## Performance Notes

- psycopg3 sync and async connection helpers are available.
- Pool defaults are configurable through settings, default min `1`, max `10`.
- Query tests prove JSONB GIN containment and generated tsvector FTS behavior.
- DAO search now constrains eval and learn reads to `kind = 'turn'`.
- All new Python files are below 700 lines. The largest new file is `session/dao.py` at 326 lines.

Verification:

- `TRANSPORT_MATTERS_DOCKER_PG_PORT=55432 docker compose up -d postgres`, healthy.
- `TRANSPORT_MATTERS_DATABASE_URL=postgresql://tm:tm@localhost:55432/transport_matters uv run alembic upgrade head && uv run alembic current`, reached `0001_session_store (head)`.
- `TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres .venv/bin/python -m pytest src/transport_matters/session/test_artifacts.py src/transport_matters/session/test_foundation.py src/transport_matters/test_config.py`, `24 passed in 1.07s`.
- `TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci`, `1237 passed in 9.08s`, `EXIT=0`.
- `uv build`, successful sdist and wheel, `EXIT=0`.
- Wheel check: `transport_matters/session/testing.py=False`, `transport_matters/session/artifacts.py=True`, `migrations/versions/0001_session_store_foundation.py=True`.
- `git diff --check`, no output.
- `.github/workflows/ci.yml` and `.github/workflows/release.yml` parse as valid YAML.
- GitHub PR checks for `af2afc4` all passed in run `27057531149`: `backend · lint`, `backend · test`, `frontend`, and `backend · package`.

## Open Items

- Wire ingest, tailer durable ack, and runtime injection remain later slices.
- FastAPI read routes, SSE listen bridge, render, fork, share, import, export, and backfill remain later slices.
- Real provider fork resume fixtures are still required before the fork slice merges.
