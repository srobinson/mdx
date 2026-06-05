---
title: Activity Postgres ingest scout for Transport Matters
type: research
tags: [transport-matters, activity, postgres, session-store, lifecycle]
summary: Activity can derive status from Postgres raw transcript records, but run lifecycle needs a new durable session store table and notify payload.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Executive Summary

Transport Matters already persists complete transcript records into the Postgres session store. The Activity product plane should read `"event".raw` plus lifecycle rows from Postgres; it should not read transcript files or depend on normalized IR alone.

## Project Metadata

- Language: Python 3.14 capture plane, TypeScript pnpm workspace product plane.
- Python dependencies: FastAPI, Pydantic, mitmproxy, psycopg, Alembic, Typer.
- Node baseline: pnpm 10.8.1, Node >=20.19.0, TypeScript, Vite, Vitest.
- Build system: Hatchling for Python packaging; pnpm workspace for frontend packages.

## Architecture

The capture plane tails transcript files through `api/src/transport_matters/index/tailer.py` `TranscriptTailer` and `_plan_ingest_records`. Each complete record is passed to a transcript adapter for optional normalized IR, then to `api/src/transport_matters/session/ingest.py` `build_event`.

The store boundary is Postgres. `build_event` writes TURN rows with `EventRow.raw=dict(record)`; `_meta_event` writes META rows with the same raw payload when an adapter returns `None`. `api/migrations/versions/0001_session_store_foundation.py` creates table `"event"` with `raw jsonb NOT NULL`; `api/src/transport_matters/session/dao_statements.py` `INSERT_EVENT_SQL` writes that column.

The notify path is `api/src/transport_matters/session/writer.py` `SessionWriter._commit_batch` to `pg_notify`, then `api/src/transport_matters/session/listen.py` `SessionEventListener` and `SessionEventHub` for Python SSE.

## Key Patterns

- Raw and IR are separate. IR can be incomplete for Activity while raw remains the source of truth.
- Codex lifecycle records are stored as META rows because `CodexAdapter.normalize` only normalizes `response_item` records.
- Postgres NOTIFY is a handle, not the data payload. Clients should use it to query records by session and seq range.

## Detailed Findings

### Raw completeness

`api/src/transport_matters/index/tailer.py` `_plan_ingest_records` appends a write for every `CompleteRecord` unless `TailCursor.skip_until_user_text` is active and the replay anchor has not been reached. `api/src/transport_matters/session/ingest.py` `build_event` and `_meta_event` preserve `raw=dict(record)`.

A verification script passed synthetic status records through `_plan_ingest_records` and `build_event` and asserted `EventRow.raw == record` for 5 Claude records and 8 Codex records. Claude markers survived as TURN rows: user turn open, tool use, tool result, `stop_reason=end_turn`, `AskUserQuestion`, `is_error`, and usage. Codex `response_item` function call records survived as TURN rows; Codex `event_msg` `task_started`, `task_complete`, `turn_aborted`, and `token_count` survived as META rows.

The one raw mutation found before Postgres is `api/src/transport_matters/session/dao_rows.py` `strip_decoded_nuls`, which removes decoded `\x00` from strings and string keys before JSONB insert. The listed Activity markers do not depend on that byte.

### Notify contract

`SessionWriter._commit_batch` emits on channel `tm_events` using `_notify_payload`: `type=session_events`, `session_id`, `run_id`, `count`, `first_seq`, and `last_seq`. `SessionEventListener._listen_forever` runs `LISTEN tm_events`; `parse_notify_payload` validates the type and seq bounds. External Node clients can consume this with `node-postgres` `LISTEN tm_events` and parse the JSON payload.

The current Python hub projects only `session_id`, `first_seq`, and `last_seq` into `SessionEventSignal`; external Postgres listeners still receive the full payload.

### Lifecycle home

Current durable tables hold sessions and transcript events, not runs. `"session"` has `run_id`, workspace identity, space/worktree ids, provider, harness, native session id, owner, and timestamps. `"event"` has `session_id`, `seq`, `run_id`, provider, harness, `ts`, and `raw`. Runtime runs live in memory under `api/src/transport_matters/run_manager.py` `RunManager._runs` as `ManagedRun`; detached launch facts also exist in tier 1 files.

The cheapest correct Activity lifecycle home is a new Postgres session store table such as `run_lifecycle_event`, because RunStarted can exist before the first transcript event or session upsert. It should be written at launch registration, at `RunManager._teardown_run` for canvas exits, and from `CapturedRunLease.close` for detached exits with idempotency across double close paths.

## Dependencies

Critical dependencies are psycopg for Postgres LISTEN/NOTIFY and JSONB writes, Alembic for schema changes, FastAPI for existing session SSE routes, and pnpm/TypeScript for the future product plane service.

## Relevance to Helioy

This confirms the two plane rule: Python remains the capture and store writer, while Activity belongs in TypeScript and consumes stable Postgres records. The next Helioy reuse seam is the session store notify pattern, not filesystem tailing.

## Open Questions

- Exact lifecycle table name and uniqueness key.
- Whether lifecycle notifications reuse `tm_events` with a new type or use a dedicated channel.
- How detached `CapturedRunLease.close` should access an async Postgres writer without adding database coupling to the lease model.
