---
title: Frontend Review for Nancy ALP-2019
type: research
tags: [nancy, alp-2019, frontend, review, manicure]
summary: Read-only review of www branch changes found no blockers, with concerns around pending track stub wiring and visual coverage for anchored ExchangeList behavior.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Review Agent B inspected the `www/` diff for branch `nancy/ALP-2019` against `main`. The frontend changes are broadly sound and targeted tests, typecheck, and targeted Biome checks pass. No blocker was found.

## Project Metadata

- Area: `www/` React 19, TypeScript, Vite, TanStack Query, TanStack Virtual, Zustand, Vitest, Playwright visual tests.
- Branch scope inspected: ExchangeList, `exchangeListRows`, `useExchangeStream`, `useExchanges`, SamplingSection extraction, visual fixtures and snapshots.
- Changed frontend footprint: 43 `www/` files, 4,616 insertions, 3,011 deletions.

## Architecture

- `www/src/hooks/useExchanges.ts` now builds tracks with nested `spawn_anchor` support and sorts exchanges newest first.
- `www/src/components/exchangeListRows.ts` projects `ExchangeTrack[]` into virtualized track and exchange rows, anchoring subagent tracks near the parent exchange that spawned them.
- `www/src/components/ExchangeList.tsx` consumes projected rows and renders virtualized `TrackHeader` and `ExchangeTurnCard` rows.
- `www/src/hooks/useExchangeStream.ts` parses `spawn_anchor` from SSE exchange events and updates both live and history caches.
- `www/src/components/editor/SamplingSection.tsx` delegates state and row rendering to `useSamplingOverrides`, `useThinkingOverrides`, and `SamplingRows`.

## Detailed Findings

### Blockers

None found.

### Concerns

1. Pending track stubs are only test wired. `ExchangeList` can accept `trackStubs`, but production `App` always passes the prebuilt `trackTree` from `useExchanges` and never passes stubs. Because `ExchangeList` prefers `trackTree` over `buildExchangeTrackTree(exchanges, trackStubs)`, pending stub rendering is not reachable from the current app wiring. Relevant paths: `www/src/components/ExchangeList.tsx:154-157`, `www/src/app.tsx:178-186`, `www/src/components/ExchangeList.trackTree.test.tsx:73-164`, `www/src/components/exchangeListRows.test.ts:224-238`.
2. Orphan anchor metadata is produced but not rendered. `projectAnchoredRows` attaches `OrphanAnchorMeta` for missing anchors and logs only in dev, but `ExchangeList` passes only `track`, `depth`, and handlers into `TrackHeader`. If missing anchors are user relevant, this will not be visible in production UI. Relevant paths: `www/src/components/exchangeListRows.ts:74-88`, `www/src/components/exchangeListRows.ts:116-118`, `www/src/components/ExchangeList.tsx:201-214`.
3. Visual fixture split preserves exports but does not visually exercise the new anchored ExchangeList behavior. Current visual specs cover app bar, paused header, and exchange detail panels; `mockExchanges` has no `run_id`, `track_id`, `parent_track_id`, or `spawn_anchor`. Relevant paths: `www/tests/visual/*.spec.ts`, `www/tests/visual/fixtures/exchanges.ts:6-126`, `www/src/visualFixtures.test.ts:12-19`.

### Positives

- Anchored row projection is extracted into a pure, focused module with good matrix coverage for Claude and Codex anchors, fan out, nested tracks, missing anchors, collapse, depth, row keys, and per track turn numbering.
- SSE cache updates now carry `spawn_anchor` through live and history cache paths, with validation tests for present and omitted anchors.
- Race handling in `useExchangeStream` is covered for matching forwarding flow, different paused flow, missing flow id, and stale `paused_tokens`.
- SamplingSection extraction substantially reduces component size while retaining behavioral tests across render, commits, resets, thinking, display, and effort.
- Typecheck, targeted Vitest, and targeted Biome passed.

## Verification

- `pnpm exec vitest run src/components/exchangeListRows.test.ts src/hooks/useExchanges.test.ts src/hooks/useExchangeStream.forwarding.test.tsx src/hooks/useExchangeStream.pausedTokens.test.tsx src/hooks/useExchangeStream.race.test.tsx src/hooks/useExchangeStream.validation.test.tsx src/components/ExchangeList.test.tsx src/components/ExchangeList.ordering.test.tsx src/components/ExchangeList.trackTree.test.tsx src/components/editor/SamplingSection.render.test.tsx src/components/editor/SamplingSection.commits.test.tsx src/components/editor/SamplingSection.providerExtras.test.tsx src/components/editor/SamplingSection.reset.test.tsx src/components/editor/SamplingSection.thinking.test.tsx src/visualFixtures.test.ts` in `www/`: 15 files passed, 126 tests passed.
- `pnpm typecheck` in `www/`: passed.
- `git diff --name-only main...HEAD -- www | rg '\.(ts|tsx)$' | rg -v 'SamplingSection\.test\.tsx|useExchangeStream\.test\.tsx' | sed 's#^www/##' | (cd www && xargs pnpm exec biome check)` from repo root: checked 33 files, no fixes applied.
- `git status --short`: clean.

## Recommended Follow Ups

1. If pending subagent headers before first exchange are part of ALP-2019 acceptance, wire `pausedFlow` or another stub source into `App` and `useExchanges`, then add an integration test that exercises the production path.
2. Decide whether orphan anchor metadata should be visible. If yes, pass row metadata into `TrackHeader` and add a small UI indication. If no, keep it internal and avoid exporting unused row metadata.
3. Add one visual spec or fixture variant with parent and anchored child exchanges so snapshot churn validates the new ExchangeList layout, not only unrelated top chrome and detail panels.

## Relevance to Helioy

The branch improves Nancy's multi agent timeline readability by making subagent exchanges appear at their spawn point, which aligns with Helioy's focus on structured context and agent orchestration traces.

## Open Questions

- What component should own pending `ExchangeTrackStub` production: `useExchanges`, `App`, or a selector derived from `pausedFlow`?
- Should missing spawn anchors be an operator visible diagnostic, or is the dev console warning sufficient?
