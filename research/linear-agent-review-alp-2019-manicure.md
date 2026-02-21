---
title: Linear Agent Review for ALP 2019 Manicure Subagent Anchoring
type: research
tags: [linear, agent-review, manicure, alp-2019, execution-order]
summary: Agent review found ALP 2019 issues are mostly ready, but ALP 2039 needs scope correction and the proposed order should change to reduce rework.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Ran the Linear Agent Review Step for ALP 2019 Todo issues, including backend, frontend, and execution order review. The issue set is mostly executable, but ALP 2039 is a cross stack contract change with missing live stream scope, ALP 2028 likely closes Won't Do, and the proposed order writes flat anchor tests before the planned nested `spawn_anchor` shape.

## Project Metadata

- Project: `manicure`
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- Backend: Python 3.12 plus FastAPI, Pydantic, mitmproxy, uv, pytest, mypy, ruff
- Frontend: React 19, TypeScript 5.9, Vite 8, TanStack React Query, TanStack Virtual, Zustand, Vitest, Playwright, pnpm 10
- fmm: `.fmm.db` exists, but some files in the target worktree were stale or missing from the fmm view. Direct inspection was used after fmm orientation for `www/src/components/exchangeListRows.ts` and current anchor fields.

## Architecture

ALP 2019 spans the track assignment pipeline and the ExchangeList projection pipeline.

Backend flow:

1. `api/src/manicure/track_manager.py::TrackManager.observe_response` assigns response local `spawn_order` during tool use observation at lines 104 to 128.
2. `api/src/manicure/track_manager.py::TrackManager._assignment` returns anchor fields from the stored `TrackRecord` at lines 398 to 408.
3. `api/src/manicure/track_manager.py::assignment_index_fields` projects track assignment fields into `IndexEntry` construction at lines 418 to 431.
4. `api/src/manicure/codex/exchange.py::_persist_codex_provisional_exchange` persists `assignment_index_fields(track_assignment)` before setting `state.provisional_exchange_id` at lines 100 to 133.

Frontend flow:

1. `www/src/types.ts` exposes flat optional anchor fields on `ExchangeTrackStub` and `IndexEntry` at lines 35 to 55.
2. `www/src/hooks/useExchanges.ts::adoptAnchor` currently uses coalescing, so later non null data can lose to earlier null data at lines 46 to 51.
3. `www/src/components/exchangeListRows.ts::projectTrack` groups children by `track_spawn_exchange_id`, sorts sibling buckets, and appends orphan children at lines 46 to 87.

## Key Patterns

- Anchor data is currently stored as three flat fields: `track_spawn_exchange_id`, `track_spawn_tool_use_id`, and `track_spawn_order`.
- `spawn_order` should remain response local. It only disambiguates sibling spawns anchored to the same parent exchange. Cross response chronology is represented by distinct anchor exchange IDs and exchange order.
- `ExchangeTrack` can stay flat as a runtime tree node even if API wire types move to nested `spawn_anchor`.
- Test fixture work should happen before schema shape changes, so the nested shape is rewritten once.

## Detailed Findings

### Execution order

Reject the user's proposed order as final. It is close, but it creates unnecessary rework.

Recommended order:

1. ALP 2030: Document `spawn_order` semantics across multi response track spawns.
2. ALP 2036: Share `makeEntry` test fixture across ExchangeList tests.
3. ALP 2039: Nest spawn anchor fields as `SpawnAnchor` on `IndexEntry`.
4. ALP 2032: Tighten anchor field optionality between `IndexEntry` and `ExchangeTrack`.
5. ALP 2035: Extract emit track assignment anchors helper.
6. ALP 2029: Add spawn anchor coverage to disk cache backfill tests, against final nested shape.
7. ALP 2031: Surface diagnostic when subagent anchor falls outside fetched window.
8. ALP 2033: Document depth semantics for nested inline subagent rows.
9. ALP 2034: Replace DOM selector assertions in ExchangeList tests with row projection assertions.
10. ALP 2038: Convert `exchangeListRows.test.ts` to table driven cases.
11. ALP 2037: Convert `test_track_manager_lifecycle.py` to table driven cases.
12. ALP 2028: Verify or close provisional Codex anchor persistence.

Rationale:

- ALP 2029 before ALP 2039 writes tests against flat fields, then rewrites them for `spawn_anchor`.
- ALP 2031 before ALP 2036 touches `exchangeListRows.test.ts` before the shared fixture exists.
- ALP 2037 before ALP 2039 and ALP 2035 table drives tests that currently assert flat anchor fields.
- ALP 2032 should stay adjacent to ALP 2039 because both touch `adoptAnchor`.
- ALP 2034 followed by ALP 2038 is good. Keep that adjacency.

### ALP 2039 scope correction

ALP 2039 is not ready as written unless it is treated as full stack. It must include:

- `api/src/manicure/storage/base.py::IndexEntry`
- `api/src/manicure/track_manager.py::TrackAssignment`
- `api/src/manicure/track_manager.py::assignment_index_fields`
- `api/src/manicure/exchange_recorder.py::emit_exchange`
- `api/src/manicure/codex/exchange.py`
- `api/src/manicure/codex/exchange_derivation.py`
- `www/src/types.ts::IndexEntry`
- `www/src/types.ts::ExchangeTrackStub`
- `www/src/hooks/useExchanges.ts::adoptAnchor`
- `www/src/hooks/useExchangeStream.ts::isValidExchangeEvent`
- `www/src/hooks/useExchangeStream.ts::useExchangeStream`
- `www/src/hooks/useExchangeStream.test.tsx`

The missing live stream path is important. Fetched rows can work through `buildExchangeTrackTree`, but live SSE exchange events also construct `IndexEntry`. If `useExchangeStream` keeps reading flat fields, live anchored rows regress.

### ALP 2028 likely Won't Do

The audit premise does not hold in the inspected worktree. `api/src/manicure/codex/exchange.py::_persist_codex_provisional_exchange` calls `_persist_track_assignment(..., exchange_id=exchange_id)`, spreads `assignment_index_fields(track_assignment)` into `IndexEntry`, and persists before `state.provisional_exchange_id` is set. See lines 100 to 133. `assignment_index_fields` includes all current anchor fields at `api/src/manicure/track_manager.py` lines 418 to 431.

Suggested comment:

> Verified in `api/src/manicure/codex/exchange.py::_persist_codex_provisional_exchange`: provisional persistence already calls `_persist_track_assignment` with the provisional `exchange_id`, writes `assignment_index_fields(track_assignment)` into `IndexEntry`, and persists before `state.provisional_exchange_id` is set. `api/src/manicure/track_manager.py::assignment_index_fields` includes `track_spawn_exchange_id`, `track_spawn_tool_use_id`, and `track_spawn_order`. The audit premise does not reproduce. Closing Won't Do.


### ALP 2028 verification update

Verified on 2026-04-27 and updated Linear. The audit premise does not reproduce. A Linear comment was added to ALP 2028 and the issue was moved to `Canceled`. Targeted checks passed:

- `uv run pytest src/manicure/test_track_manager.py::test_codex_reference_trace_assigns_subagent_by_agent_id_and_closes_on_wait src/manicure/test_track_manager.py::test_codex_fan_out_continuation_routes_to_correct_subagent -q`
- `uv run pytest src/manicure/storage/test_disk.py::TestAppendAndReadIndex::test_track_fields_round_trip -q`

### ALP 2030 decision

Choose response local semantics. `spawn_order` resets in `TrackManager.observe_response` at `api/src/manicure/track_manager.py` lines 112 to 128. That is correct for ordering sibling spawns emitted by the same response and same `track_spawn_exchange_id`. Cross response chronology comes from different exchange anchors.

### ALP 2031 wording fix

Add diagnostics to the row projection, not to the track model:

- Add `meta?: { orphanAnchor: true; missingAnchorId: string }` to the `track` row variant in `www/src/components/exchangeListRows.ts`.
- Emit row metadata in all environments.
- Gate only `console.warn` behind `import.meta.env.DEV`.
- Do not warn or mark metadata for legacy child tracks with no anchor.
- Avoid conflicting test instructions. Either assert one narrow warn case, or rely on row metadata for test coverage.

### ALP 2032 wording fix

After ALP 2039, `adoptAnchor` should operate on nested `spawn_anchor`. The rule should state that every non null source field overwrites the existing field, including non null over non null if that is intentional. Add tests for stub then entry, entry then stub, and conflicting non null values if overwrite is intended.

### ALP 2034 and ALP 2038

Keep ALP 2034 before ALP 2038. ALP 2034 should remove duplicate ordering assertions from `ExchangeList.test.tsx` only when equivalent row projection coverage exists in `exchangeListRows.test.ts`. ALP 2038 should use compact scenario builders or tuple cases rather than tables of full entry arrays.


### Linear issue update pass

Applied on 2026-04-27 after ALP 2028 was canceled. Updated Linear descriptions for ALP 2030, ALP 2039, ALP 2032, ALP 2035, ALP 2029, ALP 2031, ALP 2033, ALP 2034, ALP 2038, and ALP 2037. ALP 2036 already had the needed fixture scope, so only blocker relations were added.

Encoded blocker relations:

- ALP 2036 blocks ALP 2039, ALP 2031, and ALP 2038.
- ALP 2039 blocks ALP 2032, ALP 2035, and ALP 2029.
- ALP 2030 blocks ALP 2037.
- ALP 2031 blocks ALP 2038.
- ALP 2034 blocks ALP 2038.

## Dependencies

Suggested Linear relations:

- ALP 2036 blocks ALP 2039.
- ALP 2036 blocks ALP 2031.
- ALP 2036 blocks ALP 2038.
- ALP 2039 blocks ALP 2032.
- ALP 2039 blocks ALP 2035.
- ALP 2039 blocks ALP 2029.
- ALP 2030 blocks ALP 2037.
- ALP 2031 blocks ALP 2038.
- ALP 2034 blocks ALP 2038.
- ALP 2028 should be related, not blocking, unless verification finds a real durability gap.

## Relevance to Helioy

This review tightens Nancy execution order for a parent issue with many small, interdependent sub issues. The most important reusable pattern is to run fixture consolidation and API contract changes before broad test cleanup, then table drive tests after schema churn settles.

## Open Questions

- Should ALP 2039 be split into backend contract and frontend mirror issues, or kept as one full stack issue?
- Should ALP 2035 merge into ALP 2039, or remain a separate cleanup immediately after the nested shape lands?
- Should ALP 2033 merge into ALP 2031 to reduce Nancy overhead?
- Do you want these findings posted to Linear as parent and child comments, or should they remain in research docs until reviewed?
