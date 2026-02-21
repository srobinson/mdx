---
title: Branch Quality Review for nancy/ALP-2019
type: research
tags: [manicure, branch-review, nancy, alp-2019, pr-review]
summary: Parallel review found one backend merge blocker in destructive storage migration behavior, no frontend blockers, and produced a PR message for spawn anchored subagent tracks.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Branch `nancy/ALP-2019` adds spawn anchor propagation from backend track assignment through storage, SSE, frontend track tree construction, and ExchangeList row projection. Parallel review found one backend blocker: storage startup can delete the full default exchange history directory when it detects legacy flat spawn anchor fields. Frontend quality is broadly sound with test coverage, but pending track stubs, orphan anchor metadata, and visual coverage need product decisions or follow-up work.

## Project Metadata

- Project: `manicure`, a context control plane for Claude Code and Codex traffic.
- Branch: `nancy/ALP-2019`.
- Repository path: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`.
- Topology from fmm: 287 indexed files, 54,055 LOC.
  - `api/`: 177 files, 36,184 LOC.
  - `www/`: 110 files, 17,871 LOC.
- Backend: Python 3.12 plus, FastAPI, mitmproxy, pydantic, uv, pytest, ruff, mypy.
- Frontend: React 19, Vite 8, TypeScript 5.9, pnpm, Vitest, Playwright, Biome.
- fmm signal: `.fmm.db` exists in the worktree.

## Architecture Reviewed

### Backend

Primary reviewed files:

- `api/src/manicure/track_manager.py`
- `api/src/manicure/storage/base.py`
- `api/src/manicure/storage/disk.py`
- `api/src/manicure/exchange_recorder.py`
- `api/src/manicure/codex/exchange.py`
- `api/src/manicure/codex/exchange_derivation.py`

Key flow:

1. `TrackManager.observe_response` records Anthropic `Agent` and Codex `spawn_agent` tool calls and captures spawn anchors with response scoped `spawn_order` at `api/src/manicure/track_manager.py:132`.
2. `TrackManager._assignment` projects stored track fields into nested `SpawnAnchor` at `api/src/manicure/track_manager.py:436`.
3. `assignment_index_fields` centralizes persisted and emitted track fields at `api/src/manicure/track_manager.py:464`.
4. `IndexEntry` carries `spawn_anchor` through storage at `api/src/manicure/storage/base.py:102` and `api/src/manicure/storage/base.py:126`.
5. `emit_exchange` includes `spawn_anchor` in SSE payloads at `api/src/manicure/exchange_recorder.py:98`.
6. Codex provisional, final, and rewrite paths thread assignment fields into emitted rows in `api/src/manicure/codex/exchange.py` and `api/src/manicure/codex/exchange_derivation.py`.

### Frontend

Primary reviewed files:

- `www/src/types.ts`
- `www/src/hooks/useExchangeStream.ts`
- `www/src/hooks/useExchanges.ts`
- `www/src/components/exchangeListRows.ts`
- `www/src/components/ExchangeList.tsx`
- `www/src/components/editor/SamplingSection.tsx`
- `www/src/components/editor/useSamplingOverrides.ts`
- `www/src/components/editor/useThinkingOverrides.ts`

Key flow:

1. `SpawnAnchor` is added to frontend types at `www/src/types.ts:31`.
2. `useExchangeStream` parses nested `spawn_anchor` from SSE exchange payloads at `www/src/hooks/useExchangeStream.ts:123`.
3. `buildExchangeTrackTree` adopts anchor fields from stubs and exchange rows without overwriting known values with nulls at `www/src/hooks/useExchanges.ts:41` and `www/src/hooks/useExchanges.ts:57`.
4. `projectAnchoredRows` projects child tracks at their parent spawn exchange at `www/src/components/exchangeListRows.ts:32`.
5. `ExchangeList` delegates row projection to `projectAnchoredRows` and focuses child track clicks on the anchored parent exchange when available.

## Key Patterns

- Nested wire model: `SpawnAnchor` replaces flat top-level `track_spawn_*` fields on stored and emitted rows.
- Centralized assignment projection: `assignment_index_fields` reduces duplicated track field serialization.
- Pure UI projection: `projectAnchoredRows` makes ExchangeList ordering testable outside React.
- Test decomposition: large monolithic suites were split into focused modules for backend track management, Codex transport turns, Codex repair, ExchangeList behavior, SSE stream behavior, SamplingSection behavior, and visual fixtures.

## Detailed Findings

### Blocker

1. Destructive legacy storage handling blocks merge.

`DiskStorageBackend.__init__` calls `_drop_legacy_flat_anchor_cache()` at `api/src/manicure/storage/disk.py:44`. That helper scans `index.jsonl` for legacy flat spawn anchor keys and calls `shutil.rmtree(self._root, ignore_errors=True)` when it finds one at `api/src/manicure/storage/disk.py:64`. The default root is `~/.manicure/exchanges` at `api/src/manicure/storage/disk.py:38`, which is persistent exchange history, not a disposable cache.

The behavior is protected by tests in `api/src/manicure/storage/test_disk.py:274-303`, where a sibling exchange directory is removed. Replace this with non-destructive migration or tolerant legacy loading before merge.

Recommended fix criteria:

- Legacy top-level `track_spawn_*` fields migrate into nested `spawn_anchor`.
- Unrelated exchange artifact directories survive.
- Malformed rows do not trigger broad deletion.
- New rows continue to persist nested `spawn_anchor` only.

### Frontend concerns

1. Pending track stubs are test covered but not production wired.

`ExchangeList` accepts `trackStubs`, but production `App` passes `trackTree` from `useExchanges` and does not pass stubs. If acceptance requires pending child track headers before first exchange arrival, that behavior is unreachable in the current app wiring.

Relevant files:

- `www/src/components/ExchangeList.tsx:154-157`
- `www/src/app.tsx:178-186`
- `www/src/components/ExchangeList.trackTree.test.tsx:73-164`
- `www/src/components/exchangeListRows.test.ts:224-238`

2. Orphan anchor metadata is generated but not rendered.

`projectAnchoredRows` creates `OrphanAnchorMeta` and warns in development when an anchor is outside the fetched exchange window, but `ExchangeList` does not pass that metadata into `TrackHeader`. This is acceptable if console diagnostics are enough. If operators should see orphan anchor state, this needs UI wiring.

Relevant files:

- `www/src/components/exchangeListRows.ts:74-88`
- `www/src/components/exchangeListRows.ts:116-118`
- `www/src/components/ExchangeList.tsx:201-214`

3. Visual fixtures do not cover anchored ExchangeList layout.

The visual fixture split is cleaner, but current Playwright visual specs cover chrome, paused header, and detail panels. `mockExchanges` lacks `run_id`, `track_id`, `parent_track_id`, and `spawn_anchor`, so refreshed snapshots do not lock the new anchored ExchangeList behavior.

Relevant files:

- `www/tests/visual/*.spec.ts`
- `www/tests/visual/fixtures/exchanges.ts:6-126`
- `www/src/visualFixtures.test.ts:12-19`

### Positives

- Backend spawn anchor modeling is cleaner as nested `SpawnAnchor` in `api/src/manicure/storage/base.py:102-107`.
- `assignment_index_fields` reduces drift between persistence and SSE emission in `api/src/manicure/track_manager.py:464-475`.
- Codex finalization reuses stored entry fields when emitting, which helps preserve `spawn_anchor` consistently.
- `exchangeListRows.ts` is a good frontend extraction with focused matrix coverage for fan out, nested anchors, missing anchors, collapse, depth, stable keys, and turn numbering.
- `useExchangeStream` carries `spawn_anchor` into live and history caches and has validation coverage for present and omitted anchors.
- SamplingSection extraction reduces mixed responsibility in the main component and preserves behavior through focused test suites.

## Verification

Local coordinator commands run:

```bash
cd api
uv run pytest src/manicure/test_track_manager_core.py src/manicure/test_track_manager_lifecycle.py src/manicure/test_track_manager_anthropic.py src/manicure/test_track_manager_codex.py src/manicure/storage/test_disk_cache_backfill.py src/manicure/codex/test_transport_turn_derivation.py src/manicure/test_exchange_recorder_emit.py
```

Result: 33 passed in 0.35s.

```bash
cd www
pnpm exec vitest run src/hooks/useExchanges.test.ts src/components/exchangeListRows.test.ts src/components/ExchangeList.trackTree.test.tsx src/hooks/useExchangeStream.validation.test.tsx src/components/editor/SamplingSection.thinking.test.tsx src/components/editor/SamplingSection.commits.test.tsx
```

Result: 6 files passed, 63 tests passed.

Backend review agent verification:

- 49 targeted backend tests passed in 0.44s.
- 66 storage and API tests passed in 0.56s.
- Ruff check passed for changed backend files.
- `git diff --check main...HEAD -- api` passed.

Frontend review agent verification:

- 15 frontend test files passed, 126 tests passed.
- `pnpm typecheck` passed.
- Biome check passed for changed TypeScript and TSX files.
- `git status --short` was clean.

## PR Message Draft

Title:

```text
feat: anchor subagent tracks at spawn exchanges
```

Body:

```markdown
## Summary

* Persist and emit subagent spawn anchors through the backend exchange pipeline.
* Render subagent tracks inline at the exchange that spawned them in `ExchangeList`.
* Add regression coverage for Claude and Codex spawn ordering, nested subagents, missing anchors, SSE propagation, and storage round trips.
* Split large backend, frontend, and visual fixture test files into focused modules.

## Details

### Backend

* Adds a nested `SpawnAnchor` model on `IndexEntry` with `track_spawn_exchange_id`, `track_spawn_tool_use_id`, and `track_spawn_order`.
* Updates `TrackManager` to capture spawn anchors while observing Anthropic `Agent` and Codex `spawn_agent` tool calls.
* Threads `exchange_id` into track assignment and response observation paths so child tracks can point back to the exchange that spawned them.
* Emits `spawn_anchor` in exchange SSE payloads and persists it through HTTP, Codex provisional, Codex finalized, and Codex rewrite flows.
* Adds storage and track manager coverage for nested spawn anchors.

### Frontend

* Adds `SpawnAnchor` to frontend types and parses nested anchors from live SSE exchange events.
* Updates `buildExchangeTrackTree` to adopt anchor fields from stubs and exchange rows without erasing known values with stale nulls.
* Extracts `projectAnchoredRows` from `ExchangeList` so row projection is testable outside React rendering.
* Places child tracks at their spawn anchor when the parent exchange is in the fetched window.
* Keeps legacy and missing anchor fallback behavior for old or partial data.

### Test organization

* Splits backend suites for track manager, Codex transport turns, and Codex repair behavior.
* Splits frontend suites for SamplingSection, useExchangeStream, ExchangeList, and row projection behavior.
* Splits visual fixtures into focused modules and refreshes Darwin snapshots.

## Testing

* Backend targeted tests passed.
* Frontend targeted tests passed.
* Frontend typecheck passed.
* Backend ruff check passed.
* Biome check passed for changed frontend files.

## Reviewer notes

* Do not merge until legacy flat spawn anchor handling is non-destructive. Current storage startup behavior can delete `~/.manicure/exchanges` when it detects legacy flat anchor fields.
* Review ExchangeList ordering and selection carefully because child tracks now project around the spawning exchange.
* Decide whether pending track stubs and orphan anchor metadata should be user visible in production.
* Add one visual fixture that includes parent and anchored child exchanges so snapshots cover the new layout.
```

## Dependencies

Critical dependencies touched indirectly:

- Backend: pydantic models for storage contracts, FastAPI SSE payload consumers, mitmproxy flow persistence paths, pytest coverage.
- Frontend: React, TanStack Query cache updates, TanStack Virtual row rendering, Vitest, Playwright snapshots, Biome, TypeScript.

## Relevance to Helioy

This branch improves Manicure as a Codex and Claude session inspector by making subagent causality visible at the exchange that spawned each child track. That strengthens Helioy workflows that depend on reconstructing multi-agent task topology from captured traffic.

## Open Questions

1. Should legacy flat spawn anchor rows be migrated in place or tolerated lazily during index load?
2. Should orphan anchors be shown to operators or remain development-only console diagnostics?
3. Should pending subagent stubs be wired from `pausedFlow` or another live source?
4. Should visual snapshots include anchored ExchangeList cases before merge?
5. Should full `just test`, `just check`, backend mypy, and visual tests run before final PR approval?
