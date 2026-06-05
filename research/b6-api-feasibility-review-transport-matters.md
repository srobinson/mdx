---
title: Transport Matters B6 API Feasibility Review
type: research
tags: [transport-matters, b6, api, review, sessions, runs]
summary: B6 curated API is feasible, but `/api/sessions` must migrate as a full route family before old routes are deleted.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Executive Summary

The B6 curated API direction is feasible against the current `transport-matters` architecture at HEAD `16b95d7`. The main finding is a rollout sequencing issue: `/api/sessions` is already a transcript route family with list, events, streams, timeline, and resources, so deleting it after only moving session list/read surfaces would break active frontend panes.

A detailed verifier memo was also written to `~/.mdx/projects/tm-b6-review-feasibility-codex.md` and the orchestrator was notified on the `b6-api-review` bus thread.

# Project Metadata

- Language and stack: Python 3.14 FastAPI backend, React 19 TypeScript frontend, Vite, Zustand, TanStack Query, Postgres via psycopg, mitmproxy.
- Package files: `api/pyproject.toml` declares Python `>=3.14`, FastAPI, Pydantic, psycopg, Alembic, Typer, and mitmproxy. `www/package.json` declares React 19, Vite 8, TypeScript 5.9, Vitest, Playwright, Biome, Zustand, and xterm.
- Size: fmm indexed 758 files and 114,335 LOC, with 370 backend files and 374 frontend files.
- API mount: the app includes the current API router at `/api` in `api/src/transport_matters/main.py:202`; `session_routes` and `run_routes` are included in `api/src/transport_matters/api/v1/router.py:23` and `api/src/transport_matters/api/v1/router.py:27`.
- fmm status: fmm is available and indexed this checkout.

# Architecture

Transport Matters currently exposes mechanism shaped route families under `/api`. Run routes are owned by `api/src/transport_matters/api/v1/run_routes.py`, backed by `RunManager` in `api/src/transport_matters/run_manager.py`. Session routes are owned by `api/src/transport_matters/api/v1/session_routes.py`, backed by the Postgres session package under `api/src/transport_matters/session/`.

The spawn path is:

1. `create_run` accepts `POST /api/runs` in `api/src/transport_matters/api/v1/run_routes.py:284-295`.
2. `_spawn_request` converts the HTTP body into `SpawnRun` in `api/src/transport_matters/api/v1/run_routes.py:233-244`.
3. `RunManager.spawn` prepares and starts the captured run in `api/src/transport_matters/run_manager.py:237-305`.
4. `_captured_request` builds `CapturedRunRequest` in `api/src/transport_matters/run_manager.py:389-416`.
5. `prepare_captured_run` creates launch facts and managed session descriptors in `api/src/transport_matters/captured_run.py:155-277`.
6. The addon registers transcript cursors and `SessionWriter` writes session rows and events through `api/src/transport_matters/addon_runtime.py:86-104`, `api/src/transport_matters/session/ingest.py:62-80`, and `api/src/transport_matters/session/writer.py:107-163`.

# Key Patterns

- Frontend API calls are centralized in small client modules: run calls in `www/src/api.ts`, session list in `www/src/session-canvas/api/sessionClient.ts`, session events in `www/src/session-canvas/api/sessionEvents.ts`, and resource content in `www/src/session-canvas/api/resourceContent.ts`.
- The current backend route family layout does not align with the future product noun layout. `/api/sessions` already covers transcript events, streams, timelines, and resources.
- Session lineage support partly exists in the storage layer. `parent_session_id` and `forked_at_seq` exist in the database, Pydantic models, binding model, ingest, and upsert SQL, but continuation is not wired through run creation yet.

# Detailed Findings

## Q1, blast radius and rollout safety

`/api/runs` production blast radius is compact:

- `POST /api/runs`: `www/src/api.ts:398-409`.
- `DELETE /api/runs/{id}`: `www/src/api.ts:412-419`.
- `GET /api/runs`: `www/src/api.ts:461-473`; fmm reports no production callers of `listRuns`.
- `WS /api/runs/{id}/terminal`: `www/src/session-canvas/viewers/terminal/terminalSocket.ts:67-75`.
- Lifecycle callers: `www/src/session-canvas/model/capturedRunStore.ts:99-149` and `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:40-68`.

`/api/runs` can migrate in one PR if the terminal websocket route moves with create, delete, get, and list. `deleteRun` ignores the response body, so returning a curated Run from DELETE should not disturb the current UI.

`/api/sessions` has wider active production use:

- Session list and raw `SessionSummary`: `www/src/session-canvas/api/sessionClient.ts:3-23` and `www/src/session-canvas/api/sessionClient.ts:38-52`.
- Picker and launch resolution: `www/src/session-canvas/viewers/session-picker/SessionPickerPane.tsx:7-74`, `www/src/session-canvas/hooks/useLaunchSession.ts:9-26`, and `www/src/session-canvas/SessionCanvasRoute.tsx:14-28`.
- Event backlog and SSE: `www/src/session-canvas/api/sessionEvents.ts:39-69`.
- SSE gap backfill: `www/src/session-canvas/stream/useSessionEventStream.ts:42-79`.
- Transcript UI: `www/src/session-canvas/viewers/transcript-chat/TranscriptChatPane.tsx:10-55`.
- Resource content: `www/src/session-canvas/api/resourceContent.ts:107-135` and `www/src/session-canvas/viewers/resource/ResourcePane.tsx:33-47`.

Backend session endpoints confirm the same family shape: list at `api/src/transport_matters/api/v1/session_routes.py:128-156`, events at `159-179`, timeline at `182-213`, resources at `216-240`, event SSE at `256-271`, and timeline SSE at `274-289`.

Finding: the proposal should change build order language. Move `/api/sessions` only after list, single get, events, event stream, timeline, timeline stream, and resources have a `/v1` equivalent and frontend consumers are repointed. If the work is split, keep a temporary compatibility alias for old session family routes until every consumer moves.

## Q2, continuation seam

Continuation is feasible at the existing spawn seam without a new durable subsystem, but current code lacks the needed plumbing.

Already present:

- `session.parent_session_id` and `session.forked_at_seq` with a paired null check: `api/migrations/versions/0001_session_store_foundation.py:36-42`.
- Binding fields for lineage: `api/src/transport_matters/index/adapters/base.py:42-43`.
- Ingest persistence: `api/src/transport_matters/session/ingest.py:77-78`.
- Upsert SQL support: `api/src/transport_matters/session/dao_statements.py:68-97`.

Missing:

- `CreateRunRequest` has no `continueFromSessionId` or continuation field at `api/src/transport_matters/api/v1/run_routes.py:70-77`.
- `SpawnRun` has no continuation field at `api/src/transport_matters/run_manager.py:108-127`.
- `_launch_run_context` carries no lineage into adapter binding at `api/src/transport_matters/addon_runtime.py:67-83`.
- `_register_owned_cursor` preserves only `minted` and `source_descriptor` at `api/src/transport_matters/addon_runtime.py:96-100`.
- `register_session_cursor` rebinds and carries only `minted` and `source_descriptor` at `api/src/transport_matters/index/tailer.py:438-469`, so parent and fork values would be dropped unless the seam is extended.
- An absence probe found no continuation field names in the spawn path: `rg continueFromSessionId|continuationId|continuation_id|continue_from_session_id ... -> 0`.

Required additions: request payload field, owner scoped parent lookup, last visible seq calculation from the event table, lineage propagation through spawn or cursor registration, and Postgres sourced context priming. Product direction excludes native CLI resume from this path.

## Q3, `homeDir` droppable

The curated Session can drop `homeDir`.

- Backend `SessionSummary` exposes `home_dir` at `api/src/transport_matters/api/v1/session_routes.py:51-79`.
- Frontend `SessionSummary` declares `home_dir` at `www/src/session-canvas/api/sessionClient.ts:3-23`.
- A frontend absence probe found no production reader outside the type and test utilities: `rg 'home_dir|homeDir' www/src`, excluding `sessionClient.ts` and `testUtils.tsx`, returned 0 hits.
- Launch scoped home data still exists in the launch path: `Settings.agent_home_dir` at `api/src/transport_matters/config.py:98-102`, `_spawn_request` at `api/src/transport_matters/api/v1/run_routes.py:233-244`, and captured run preparation at `api/src/transport_matters/captured_run_context.py:94-114`.
- Backfill uses owned launch facts instead of the DB session row when reconstructing bindings: `api/src/transport_matters/session/backfill.py:132-154`.

Conclusion: no relaunch, resume, or launch consumer reads persisted `SessionSummary.home_dir`. Keep launch provenance internally. Expose structured debug provenance later if needed.

## Q4, computed turn counts

Count data exists and can be computed at read time.

- Events carry `seq`, `kind`, `role`, and `is_sidechain`: `api/migrations/versions/0001_session_store_foundation.py:58-83`.
- The primary key `(session_id, seq)` bounds per session event scans: `api/migrations/versions/0001_session_store_foundation.py:80-82`.
- Parent linkage and fork point live on session rows: `api/migrations/versions/0001_session_store_foundation.py:36-42`.
- Existing child session summary SQL already aggregates child event min and max: `api/src/transport_matters/session/dao_statements.py:202-212`.

Current API does not compute these fields. `SessionSummary` has no counts at `api/src/transport_matters/api/v1/session_routes.py:51-79`, and `list_sessions` returns plain summaries at `api/src/transport_matters/api/v1/session_routes.py:128-156`.

Recommendation: compute counts in the B6 session projection query, grouped across the listed page. `turnCount` can count visible current session turn events. `inheritedTurnCount` can count visible parent turn events up to `forked_at_seq`. Latency risk is low for realistic session sizes if implemented as grouped SQL, with a partial index reserved for measured need.

## Q5, canvas layout cut

Cutting canvas layout from B6 is correct.

- Backend absence probe: `rg canvas-layout|canvas_layout|canvasKey|canvas_key|PersistedCanvasState api/src -> 0`.
- `PersistedCanvasState` is a frontend local persistence type at `www/src/session-canvas/persistence/canvasPanePersistence.ts:36-38`.
- The canvas store persists through frontend storage options at `www/src/session-canvas/model/canvasStore.persistence.ts:18-26` and `www/src/session-canvas/model/canvasStore.ts:288`.
- Transcript panes only need session ids: `www/src/session-canvas/model/canvasStore.ts:253-262`.

A backend canvas layout store can belong to the desktop context later, keyed by workspace and canvas id.

# Dependencies

Critical dependencies for this review:

- FastAPI and Pydantic for current route and response models.
- Postgres, psycopg, and Alembic for session store state, event queries, and migrations.
- React, Zustand, and TanStack Query for frontend pane state and API consumption.
- fmm for code structure, symbol reads, and caller impact.

# Relevance to Helioy

This finding protects the B6 seam that can later serve Lilo and other Helioy components. The key implementation principle is route family migration: Transport Matters can keep a single `/v1` namespace without preserving parallel public APIs, while still avoiding a broken intermediate state for active desktop transcript panes.

# Open Questions

- Define the exact visible turn predicate for `turnCount` and `inheritedTurnCount`: whether meta events, sidechain turns, and subagent child sessions count.
- Decide whether `/v1/sessions/{id}/events` or `/v1/sessions/{id}/timeline` becomes the primary transcript pane source.
- Decide whether session `purpose` and `visibility` are a hard prereq for the first continuation slice or can land as a small schema slice immediately before it.
