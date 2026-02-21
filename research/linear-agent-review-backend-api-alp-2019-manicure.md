---
title: Linear Agent Review for ALP-2019 Backend/API Issues
type: research
tags: [manicure, linear, backend, api, spawn-anchors, agent-review]
summary: Review found ALP-2028 is already handled, ALP-2030 should choose response-local spawn order semantics, and ALP-2039 should be split or made explicitly cross-stack.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed backend and API follow-up issues under ALP-2019 in `manicure-worktrees/nancy-ALP-2019`. The backend spawn anchor path is mostly ready, but ALP-2028 should close as Won't Do, ALP-2030 needs the response-local decision written into the issue, and ALP-2039 needs clearer split or cross-stack scope before Nancy executes it.

## Project Metadata

- Project: Manicure, a context control plane for Claude Code and Codex traffic.
- Backend: Python 3.12 or newer, FastAPI, Pydantic, mitmproxy, uv.
- Frontend: Vite 8, React 19, TypeScript, pnpm 10.8.1.
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`.
- fmm: `.fmm.db` exists and `fmm validate` reports the worktree index is up to date. The MCP fmm server resolved relative paths against a different checkout, so final findings use direct read-only inspection of the requested worktree after the required fmm orientation step.

## Architecture

- `api/src/manicure/track_manager.py` owns track classification. `TrackAssignment`, `TrackRecord`, and `PendingSpawn` carry flat spawn anchor fields today. `TrackManager.observe_response` assigns `spawn_order` per response and `_assignment` projects `TrackRecord` anchor state into `TrackAssignment`.
- `api/src/manicure/codex/exchange.py` persists Codex provisional and finalized exchanges. `_persist_codex_provisional_exchange` calls `_persist_track_assignment` with `exchange_id`, builds `IndexEntry`, spreads `assignment_index_fields`, then writes via `_persist_exchange` before setting the provisional state id.
- `api/src/manicure/exchange_recorder.py` persists generic HTTP exchanges and emits SSE exchange payloads. `emit_exchange` includes the flat anchor fields.
- `api/src/manicure/storage/base.py` exposes `IndexEntry` with flat `track_spawn_exchange_id`, `track_spawn_tool_use_id`, and `track_spawn_order` fields.
- `www/src/types.ts` currently mirrors those fields on `IndexEntry` and `ExchangeTrackStub`; the runtime `ExchangeTrack` remains flat.

## Key Patterns

- Durable storage uses `DiskStorageBackend.persist_exchange`, which writes exchange artifacts and rewrites `index.jsonl` atomically enough for index recovery.
- `assignment_index_fields` is already the canonical helper for storage projection. SSE projection still has repeated open-coded unpacking in `codex/exchange.py` and `exchange_recorder.py`.
- The UI sorts siblings by `track_spawn_order` only within the same `track_spawn_exchange_id`. Distinct response anchors already provide natural chronological order through exchange ordering.

## Detailed Findings

### ALP-2028

Recommendation: close as Won't Do.

Verified `_persist_codex_provisional_exchange` persists the assignment before finalization. The path calls `_persist_track_assignment(..., exchange_id=exchange_id)`, spreads `assignment_index_fields(track_assignment)` into `IndexEntry`, writes via `_persist_exchange`, then sets `state.provisional_exchange_id`. `assignment_index_fields` includes all three spawn anchor fields in this worktree.

Suggested Linear comment:

> Verified in `api/src/manicure/codex/exchange.py::_persist_codex_provisional_exchange`: provisional persistence already calls `_persist_track_assignment` with the provisional `exchange_id`, writes `assignment_index_fields(track_assignment)` into `IndexEntry`, and persists before `state.provisional_exchange_id` is set. `api/src/manicure/track_manager.py::assignment_index_fields` already includes `track_spawn_exchange_id`, `track_spawn_tool_use_id`, and `track_spawn_order`. The audit premise does not reproduce. Closing Won't Do.

### ALP-2029

Recommendation: ready if flat fields stay for this iteration. If ALP-2039 lands first, update ALP-2029 to nested `spawn_anchor` or merge the coverage into ALP-2039.

The target file exists and currently covers cache creation backfill only. `api/src/manicure/storage/test_disk.py` has flat anchor round-trip coverage, but `test_disk_cache_backfill.py` does not. The issue is testable and small. The main dependency risk is churn from ALP-2039 changing the storage shape.

Suggested description change if kept after ALP-2039:

> Replace references to `track_spawn_exchange_id`, `track_spawn_tool_use_id`, and `track_spawn_order` with `spawn_anchor`. Assert populated `SpawnAnchor` and `spawn_anchor=None` survive the `DiskStorageBackend` cache reload path in `api/src/manicure/storage/test_disk_cache_backfill.py`.

### ALP-2030

Recommendation: decide response-local semantics and keep this as documentation plus possibly one regression.

`TrackManager.observe_response` resets `spawn_order` per response. That is correct for the current UI contract because sibling sorting only needs to disambiguate multiple spawns under the same `track_spawn_exchange_id`. A parent track spawning again in a later response gets a different exchange anchor, so natural exchange order gives the cross-response chronology. Track-local monotonic counters would add persistence and replay complexity without solving a current ordering gap.

Suggested description change:

> Decision: `track_spawn_order` is response-local. It orders sibling spawns emitted from the same parent response and the same `track_spawn_exchange_id`. Cross-response chronology is represented by the distinct `track_spawn_exchange_id` anchors and exchange ordering. Add docstrings or inline comments on `TrackManager.observe_response`, `_register_anthropic_spawn`, and `_register_codex_spawn`. Add a regression only if the frontend currently misorders two child tracks anchored to two different parent exchanges.

### ALP-2035

Recommendation: keep, but execute after ALP-2039 or rewrite to the final shape.

The repeated SSE unpacking exists in `api/src/manicure/codex/exchange.py` and `api/src/manicure/exchange_recorder.py`. `assignment_index_fields` already covers storage projection. If ALP-2039 lands first, the new helper should probably project a `TrackAssignment` into the final wire shape for emit payloads, not reproduce the flat fields.

Suggested description change:

> Land after ALP-2039. Extract the helper against the final `SpawnAnchor` shape. Keep `assignment_index_fields` focused on `IndexEntry` construction unless ALP-2039 deliberately replaces it with a shared projection helper.

### ALP-2037

Recommendation: defer until functional and schema issues are stable.

The target file exists and is 509 lines. It has repeated lifecycle setup and is a reasonable cleanup. It is not required for ALP-2019 acceptance and can create merge churn against `track_manager.py` tests while ALP-2030 and ALP-2039 are unsettled. The current description is testable, but line-count targets should be secondary to preserving scenario names and assertions.

Suggested description change:

> Execute after ALP-2030 and ALP-2039. Preserve named behavioral scenarios as case names. Do not change `TrackManager` behavior. Line count reduction is a non-goal if it conflicts with readability or coverage.

### ALP-2039

Recommendation: split, or mark explicitly cross-stack and block downstream work.

The issue is larger than the title. `SpawnAnchor` on backend `IndexEntry` is a schema change. `ExchangeTrackStub` exists in `www/src/types.ts`, so that part is frontend type mirror work. The issue also touches `TrackAssignment`, write sites, SSE payload shape, Codex derived artifacts, disk storage tests, and frontend `adoptAnchor`. If Nancy dispatches this as backend-only, it will either break TypeScript consumers or leave an inconsistent API contract.

Suggested split:

1. Backend/API contract issue: add `SpawnAnchor` in `api/src/manicure/storage/base.py`, update `IndexEntry`, `TrackAssignment`, `assignment_index_fields`, `emit_exchange`, `codex/exchange.py`, `exchange_recorder.py`, `codex/exchange_derivation.py`, and backend storage tests.
2. Frontend mirror issue: update `www/src/types.ts`, `www/src/hooks/useExchangeStream.ts`, `www/src/hooks/useExchanges.ts::adoptAnchor`, and fixtures/tests to unwrap `spawn_anchor` into runtime `ExchangeTrack`.

If kept as one issue, add explicit acceptance that backend API responses, SSE exchange events, frontend types, and frontend tests all switch in the same change.

## Dependency Recommendations

Recommended execution graph:

1. ALP-2028: verify and close Won't Do.
2. ALP-2030: record response-local semantics before more work depends on the meaning of `spawn_order`.
3. ALP-2039: after ALP-2036, before ALP-2032 and ALP-2035. Split or make cross-stack.
4. ALP-2029: merge into ALP-2039 or execute after ALP-2039 against `spawn_anchor`.
5. ALP-2035: after ALP-2039, extracting helpers against the final shape.
6. ALP-2037: last, as cleanup only.

Linear currently shows no encoded blocker relations for the reviewed backend/API issues. Add blocker relations later if Linear edits are allowed.

## Dependencies

Critical dependencies touched by the reviewed work:

- Pydantic models in `api/src/manicure/storage/base.py` define the API wire schema.
- `DiskStorageBackend` controls durable index JSON loading and recovery.
- FastAPI list and detail endpoints return `IndexEntry` directly.
- SSE payloads are emitted by `api/src/manicure/exchange_recorder.py::emit_exchange`.
- Frontend TypeScript mirrors the backend wire shape in `www/src/types.ts`.

## Relevance to Helioy

ALP-2019 improves causal inspection of multi-agent runs, which is directly relevant to Helioy's orchestration and review workflows. The main design lesson is to model spawn anchors as a single contract that spans in-memory track management, persisted index rows, SSE events, and frontend projection.

## Open Questions

- Should ALP-2039 be executed atomically as cross-stack work, or split with a temporary compatibility bridge?
- Should `emit_exchange` move to nested `spawn_anchor` immediately with storage, or should SSE compatibility be preserved for one release?
- Should cache backfill anchor tests live in ALP-2029 or become part of ALP-2039 acceptance?
