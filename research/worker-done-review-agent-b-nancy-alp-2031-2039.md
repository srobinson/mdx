---
title: Worker Done Review Agent B for Nancy ALP-2031, ALP-2032, and ALP-2039
type: research
tags: [nancy, manicure, linear-review, spawn-anchor, exchange-list, sse, storage]
summary: Review Agent B found ALP-2031, ALP-2032, and ALP-2039 acceptable with no Linear defects filed.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed Worker Done issues ALP-2031, ALP-2032, and ALP-2039 in the current `nancy/ALP-2019` worktree. All three pass acceptance review for accuracy, quality, DRY, and tests. No Linear comments were added because no actionable defects were found.

## Project Metadata

- Project: Manicure, under Nancy ALP-2019 worktree.
- Backend: Python 3.12 plus, FastAPI, Pydantic, pytest, mypy.
- Frontend: React 19, TypeScript 5.9, Vite, TanStack Query, Vitest.
- Structural index: `.fmm.db` present at repo root.

## Detailed Findings

### ALP-2031: Surface diagnostic when subagent anchor falls outside fetched window

Status: Pass.

Evidence:

- `www/src/components/exchangeListRows.ts:60-90` splits anchored children into valid anchors, missing anchor diagnostics, and legacy anchorless orphans.
- `www/src/components/exchangeListRows.ts:75-80` emits `console.warn` only under `import.meta.env.DEV` and includes `trackId`, `missingAnchorId`, and `parentTrackId`.
- `www/src/components/exchangeListRows.ts:82-88` attaches `meta: { orphanAnchor: true, missingAnchorId }` to rows whose anchor falls outside the fetched exchange window.
- `www/src/components/exchangeListRows.test.ts:290-302` preserves the existing fallback test name and asserts orphan metadata.
- `www/src/components/exchangeListRows.test.ts:304-323` verifies the dev warning payload.
- `www/src/components/exchangeListRows.test.ts:325-342` verifies anchorless legacy child tracks do not receive metadata or warnings.

Quality notes:

- The split is minimal and keeps legacy orphan behavior separate from missing anchor diagnostics.
- No duplicate projection logic was introduced.

### ALP-2032: Tighten anchor field optionality between IndexEntry and ExchangeTrack

Status: Pass.

Evidence:

- `www/src/hooks/useExchanges.ts:41-55` rewrites `adoptAnchor` to read nested `SpawnAnchor | null | undefined` and assign every non null field directly to the flat runtime `ExchangeTrack` fields.
- `www/src/hooks/useExchanges.ts:43-45` documents the ordering and stale null rule.
- `www/src/types.ts:75-79` documents that runtime tracks remain flat while wire rows use nested `spawn_anchor`.
- `www/src/hooks/useExchanges.ts:100-124` applies the same helper to stubs and index entries.
- `www/src/hooks/useExchanges.test.ts:147-249` covers same anchor stability and p0 to p1 correction cases across stub and entry combinations.

Quality notes:

- The helper removes the previous asymmetric `??=` behavior.
- No new abstraction beyond the existing helper was introduced.

### ALP-2039: Nest spawn anchor fields as SpawnAnchor on IndexEntry

Status: Pass.

Evidence:

- Backend model: `api/src/manicure/storage/base.py:102-128` defines `SpawnAnchor` and nests `spawn_anchor` on `IndexEntry`.
- Backend assignment: `api/src/manicure/track_manager.py:24-50` stores `spawn_anchor` on `TrackAssignment`; `api/src/manicure/track_manager.py:464-475` emits nested `spawn_anchor` through `assignment_index_fields`.
- Backend SSE: `api/src/manicure/exchange_recorder.py:80-121` emits `spawn_anchor` as object or null and omits flat top level keys.
- HTTP and Codex persistence paths use `assignment_index_fields`: `api/src/manicure/exchange_recorder.py:213-249`, `api/src/manicure/codex/exchange.py:103-149`, and `api/src/manicure/codex/exchange.py:241-285`.
- Codex rewrite and finalize paths preserve and re emit the nested anchor: `api/src/manicure/codex/exchange.py:448-474`, `api/src/manicure/codex/exchange_derivation.py:391-423`.
- Frontend wire types: `www/src/types.ts:35-67` defines `SpawnAnchor` and nests it on `ExchangeTrackStub` and `IndexEntry`; `ExchangeTrack` remains flat at `www/src/types.ts:69-82`.
- Frontend SSE parsing: `www/src/hooks/useExchangeStream.ts:123-138` parses nested `spawn_anchor`; `www/src/hooks/useExchangeStream.ts:220-240` stores it on `IndexEntry`.
- Storage migration: `api/src/manicure/storage/disk.py:44-88` drops legacy cache roots containing flat anchor keys on startup.
- Storage tests: `api/src/manicure/storage/test_disk.py:230-271` verifies nested dump shape, null round trip, and invalid negative order; `api/src/manicure/storage/test_disk_cache_backfill.py:186-228` verifies cache reload for populated and null `spawn_anchor`.
- SSE tests: `api/src/manicure/test_exchange_recorder_emit.py:143-187` verifies nested payload and explicit null default.

Quality notes:

- The implementation centralizes backend persistence and emit unpacking through `assignment_index_fields`, reducing duplicate field mapping.
- Retained `TrackAssignment.track_spawn_*` properties are compatibility conveniences for existing tests and callers, not wire contract leakage.

## Verification

Commands run from `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`:

```bash
pnpm --dir www test -- src/components/exchangeListRows.test.ts src/hooks/useExchanges.test.ts src/hooks/useExchangeStream.validation.test.tsx
```

Result: 33 test files, 298 tests passed.

```bash
pnpm --dir www typecheck
```

Result: passed.

```bash
cd api && uv run pytest src/manicure/storage/test_disk.py src/manicure/storage/test_disk_cache_backfill.py src/manicure/test_exchange_recorder_emit.py src/manicure/test_track_manager_lifecycle.py src/manicure/test_track_manager_codex.py src/manicure/test_track_manager_anthropic.py
```

Result: 54 tests passed.

```bash
cd api && uv run mypy src/manicure/storage/base.py src/manicure/storage/disk.py src/manicure/storage/disk_helpers.py src/manicure/track_manager.py src/manicure/exchange_recorder.py src/manicure/codex/exchange.py src/manicure/codex/exchange_derivation.py
```

Result: success, no issues found in 7 source files.

## Dependencies

- ALP-2039 provides the nested `spawn_anchor` wire shape used by ALP-2032.
- ALP-2031 builds on the ExchangeList row projection logic and shared fixtures from ALP-2036.

## Relevance to Helioy

This review confirms the ALP-2019 spawn anchor contract is now expressed as one typed unit across storage, SSE, and frontend wire rows, while preserving a flat runtime tree node for rendering. This is a good pattern for Helioy code that crosses persistence, event, and UI boundaries: group semantic wire fields, then unwrap exactly once at the runtime projection boundary.

## Open Questions

None for this review.
