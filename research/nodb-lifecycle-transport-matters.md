---
title: No DB lifecycle in Transport Matters
type: research
tags: [transport-matters, postgres, lifecycle, capture, tier1]
summary: Normal launches fail at session store preflight with no Postgres, while lower capture paths can still write Tier 1 if that guard is bypassed.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Executive Summary

Transport Matters now treats Postgres as required for normal launch entrypoints. The earliest normal failure is the shared session store preflight, before proxy, backend, agent, or Electron serving starts. Lower capture primitives still make Tier 1 disk storage independent from Postgres, so the wire path can survive if preflight is bypassed or the database dies after launch.

## Project Metadata

Language: Python 3.14 API, FastAPI backend, Typer CLI, psycopg pool, Alembic migrations, mitmproxy capture. Build system: Hatchling via `api/pyproject.toml`. fmm index status: `fmm validate` passed for 843 indexed files.

## Architecture

Normal `transport-matters claude`, `codex`, and desktop backend paths call `api/src/transport_matters/cli/launch_runtime.py:preflight_session_store_or_exit` before launch preparation proceeds. That preflight calls `api/src/transport_matters/session_store_preflight.py:check_session_store`, which resolves config through `api/src/transport_matters/config.py:resolve_database_url` and then probes Postgres with `psycopg.connect`.

The direct ASGI path is softer. `api/src/transport_matters/main.py:lifespan` calls `_start_session_store`; unreachable database returns no pool and leaves session routes unavailable, while a reachable store with confirmed migration failure raises. `api/src/transport_matters/addon_runtime.py:load_capture_runtime` initializes disk storage and proxy binding first, then treats session capture startup as best effort.

## Key Patterns

- Hard gate at CLI launch: `preflight_session_store_or_exit` exits 2 for missing or unreachable DB.
- Lazy pools: `session/pool.py:create_async_pool` does not connect until opened or checked out.
- Capture separation: `storage/__init__.py:init_storage`, `storage/disk.py:DiskStorageBackend.persist_exchange`, and `exchange_recorder.py:persist_http_exchange` write Tier 1 without DB calls.
- Observer failures are contained: `session/writer.py:SessionWriter._commit_batch` errors surface through commit futures, and `session/listen.py:SessionEventListener._run` reconnects after listener drops.

## Detailed Findings

Required project artifact written to `~/.mdx/projects/transport-matters-nodb-lifecycle.md` with the full seam classification. The single earliest normal no DB failure point is `api/src/transport_matters/cli/launch_runtime.py:preflight_session_store_or_exit`. Normal `transport-matters claude` cannot write Tier 1 from a no Postgres process start because it exits before the run lock, manifest, proxy, and agent. If the guard is bypassed, Tier 1 wire persistence remains possible through the disk storage path, but transcript session persistence degrades.

## Dependencies

Critical runtime dependencies involved: `psycopg[binary,pool]` for direct probes, pools, and async connections; `alembic` for migration head management; `fastapi` and `uvicorn` for the backend; `mitmproxy` for capture.

## Relevance to Helioy

This confirms the current design: Postgres is a launch prerequisite for first class operation, while Tier 1 remains the durable wire artifact substrate. Any future offline capture mode would need to move or parameterize the preflight gate, not rewrite the storage layer.

## Open Questions

Should there be an explicit documented proxy only or offline Tier 1 mode that bypasses the session store preflight, or should no DB always mean no launch in user facing commands?
