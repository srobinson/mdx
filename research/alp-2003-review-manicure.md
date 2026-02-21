---
title: ALP-2003 Scoped Override Review for Manicure
type: research
tags: [manicure, alp-2003, code-review, overrides, tracks]
summary: ALP-2003 scopes prompt overrides by run and track, and the reviewed implementation is accepted.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-25
updated: 2026-04-25
---

## Executive Summary

ALP-2003 scopes Manicure prompt overrides by `(run_id, track_id)` so parent and subagent edits do not leak across tracks. Review found the implementation complete and accepted across backend storage, request classification, paused flow propagation, API routes, and frontend override calls.

## Project Metadata

- Language: Python 3.13 backend, TypeScript React frontend
- Backend framework: FastAPI, Pydantic, mitmproxy addon hooks
- Frontend framework: React, TanStack Query, Vite, Vitest, Biome
- Build and verification: `uv`, `ruff`, `mypy`, `pnpm`, `tsc`, `vitest`
- Branch: `nancy/ALP-1847`
- Reviewed commits: `aecbfb1 feat(api): scope overrides by track`, `41106c8 test(api): simplify override test imports`

## Architecture

ALP-2003 builds on ALP-2002 track classification. The main path is now:

1. `addon_handlers.handle_http_request` and `handle_codex_websocket_message` pass `get_settings().run_id` into `run_pipeline` and store the returned assignment in flow metadata.
2. `request_pipeline.run_pipeline` classifies the request before applying overrides, chooses `(run_id, track_id)` scope, and applies only that scope's overrides.
3. `flow_state.RequestFlowState` persists `track_assignment` so exchange persistence does not classify the same request again.
4. `exchange_recorder._persist_track_assignment` reuses the stored assignment and only observes the response when available.
5. `pause_session` carries scope fields into `PausedFlow` and paused SSE payloads.
6. `api/v1/overrides.py` accepts `run_id` and `track_id` query params and updates paused previews only for the matching scope.
7. `BreakpointEditor` derives an `OverrideScope` from the paused flow and `useOverrides` includes that scope in query keys and API calls.

## Key Patterns

- `OverrideStore` keeps no-arg compatibility while internally storing overrides and enabled state per normalized scope. See `api/src/manicure/override_state.py:30-102`.
- `TrackManager.record_exchange` now delegates to `classify_request` plus `observe_response`, preserving ALP-2002 behavior while allowing pre-response override scoping. See `api/src/manicure/track_manager.py:65-85`.
- Flow metadata is the handoff point between live request mutation and later exchange persistence. See `api/src/manicure/flow_state.py:27-131`.
- Frontend cache keys include scope, preventing one paused track from seeing another track's overrides. See `www/src/hooks/useOverrides.ts:21-74`.

## Detailed Findings

### Backend scoped store

`OverrideStore` now normalizes scope with `root_scope` and `normalize_scope`, stores overrides as `dict[OverrideScope, OrderedDict[OverrideKey, Override]]`, and stores disabled state per scope. Reads and writes accept `scope` while preserving legacy no-arg calls. This satisfies the ALP-2003 isolation model.

Relevant code: `api/src/manicure/override_state.py:14-102`.

### Pipeline applies overrides to the classified track

`run_pipeline` now returns `(curated_ir, audit, track_assignment)`. When a `run_id` exists, it calls `TrackManager.classify_request`, computes `(run_id, track_assignment.track_id)`, and applies only `store.get_all(scope=scope)`. Disabled state is also scoped.

Relevant code: `api/src/manicure/request_pipeline.py:60-86`.

### Persistence does not double classify

`_persist_track_assignment` reuses `request_state.track_assignment` and calls `observe_response` for the response side. This avoids reassigning a request to a different track after overrides or pause flow handling.

Relevant code: `api/src/manicure/exchange_recorder.py:136-151`, `api/src/manicure/codex/exchange.py:91-99`, `api/src/manicure/codex/exchange.py:232-240`.

### Paused flow API and SSE carry scope

`PausedFlow` includes run and track fields, `pause_session._paused_event_payload` emits them, and `breakpoint_routes.get_paused_flow` returns them. Re-audit computes the paused flow scope before applying overrides.

Relevant code: `api/src/manicure/breakpoint.py:24-49`, `api/src/manicure/pause_session.py:109-161`, `api/src/manicure/api/v1/breakpoint_routes.py:230-239`.

### Override API is scoped

GET, PATCH, DELETE, and toggle accept `run_id` and `track_id`, normalize them into an `OverrideScope`, and update only that scope. Paused preview updates search for a matching paused flow when an explicit scope is provided.

Relevant code: `api/src/manicure/api/v1/overrides.py:50-161`.

### Frontend sends paused scope

`BreakpointEditor` derives `{ run_id, track_id }` from `pausedFlow` and passes it into `useOverrides`. The hook includes scope in the query key and API calls. SSE parsing stores track fields on paused flows and live exchange entries.

Relevant code: `www/src/components/editor/BreakpointEditor.tsx:41-48`, `www/src/hooks/useOverrides.ts:21-74`, `www/src/hooks/useExchangeStream.ts:155-209`.

## Verification

Focused verification:

- `cd api && uv run pytest src/manicure/test_override_state.py src/manicure/test_request_pipeline.py src/manicure/api/v1/test_overrides.py src/manicure/api/v1/test_breakpoint.py src/manicure/test_track_manager.py` -> 62 passed
- `pnpm --dir www test src/hooks/useExchangeStream.test.tsx src/components/editor/BreakpointEditor.test.tsx` -> 48 passed
- `pnpm --dir www typecheck` -> passed
- `cd api && uv run ruff check ... && uv run mypy ...` -> passed

Full verification:

- `cd api && uv run pytest` -> 701 passed
- `cd api && uv run ruff format --check src/` -> 160 files already formatted
- `cd api && uv run ruff check src/` -> all checks passed
- `cd api && uv run mypy src/` -> success, no issues in 161 source files
- `pnpm --dir www lint` -> passed
- `pnpm --dir www typecheck` -> passed
- `pnpm --dir www test` -> 21 files, 254 tests passed

## Dependencies

- FastAPI query parameter handling for scoped override APIs
- Pydantic models for IR, audit, paused flow responses, and storage index entries
- mitmproxy flow metadata for carrying `TrackAssignment` through request, breakpoint, and persistence phases
- TanStack Query for scoped override caching

## Relevance to Helioy

This pattern is useful for Helioy multi-agent tooling generally: classify work into track scope before mutation, persist that scope on the live object, and avoid recomputing identity later. It gives agent-specific control surfaces without global leakage.

## Open Questions

None for ALP-2003 acceptance. Future work may define explicit cross-track or run-wide override semantics if users need a deliberate global override mode.

## Review Decision

LGTM ALP-2003.
