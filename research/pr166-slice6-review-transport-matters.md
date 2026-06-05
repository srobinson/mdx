---
title: PR#166 Spaces Slice 6 review findings for Transport Matters
type: research
tags: [transport-matters, pr166, spaces, slice6, review, www, canvas]
summary: Initial review found two issues; delta re-review at 093d1ab confirmed both resolved and signed off PR#166.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

## Executive Summary

PR#166 implements Spaces Slice 6 for the React canvas surface: minted canvas identity, worktree rooted pane refs, per canvas persistence, launcher Space and Worktree scopes, and run API re-keying. The initial review withheld sign off for two high confidence issues; the 093d1ab delta re-review confirmed both were resolved and signed off the PR.

## Project Metadata

- Project: `transport-matters`
- Area reviewed: `www/`, React 18, TypeScript, zustand, TanStack Query, vitest, Playwright e2e
- Branch reviewed: `spaces/slice6-www-canvas`
- Head reviewed: `3e27c2c6e63f2b91e546d5037d82c80182efe856`
- Base: `main@70493a4e206a3d037392997e09fbf483bcc71f0e`
- PR: `#166`, open, non draft, CI green on six checks
- Worktree state before verdict: pristine, `git status --short` empty
- Structural index: `.fmm.db` present, fmm used for topology and symbol outlines

## Architecture

Slice 6 affects the browser canvas layer:

- `www/src/session-canvas/model/canvasStore.ts` now owns `canvasId`, `spaceId`, `defaultWorktreeId`, canvas switching, one time legacy import, and per canvas rehydrate.
- `www/src/session-canvas/model/paneRecords.ts` makes terminal and captured run refs worktree rooted, with `captured-run.sessionId` persisted as a future resume anchor.
- `www/src/session-canvas/persistence/canvasCacheStorage.ts` namespaces localStorage by `canvasId` and imports the legacy single canvas key once.
- `www/src/session-canvas/persistence/canvasPanePersistence.ts` drops invalid refs while preserving valid siblings and pruning orphan rects.
- `www/src/session-canvas/launcher/commandModel.ts`, `useCommandCenter.ts`, `useLauncherRows.ts`, and `useSpaces.ts` add Space and Worktree scopes and `select-worktree` commands.
- `www/src/api.ts` adds `/v1/spaces` and `/v1/spaces/{spaceId}/worktrees`, re-keys run types to `spaceId` and `worktreeId`, and sends `worktreeId` for captured run creation.

## Key Patterns

- Canvas persistence is now cache keyed by `canvasId`, not a single global `transport-matters-canvas` blob.
- Worktree identity is the launcher and run spawn boundary. Paths are display data, not emitted identity.
- The route switcher has a narrow existing contract: `navigateToRoute(path)` accepts a path and preserves the current query string itself. Callers must not pass a path that already contains query parameters.
- The local AGENTS limit treats files above 700 LOC as a hard stop before adding code, including tests.

## Detailed Findings

### Blocker: changed test file exceeds the hard 700 LOC limit

`www/src/session-canvas/lab/canvasLabStore.test.ts` is now 716 lines. PR#166 adds Slice 6 changes to this already oversized file at line 26, line 238, and line 306. The project instruction is explicit: files already over 700 lines must be refactored before new code is added, with no exceptions.

Evidence:

- `wc -l www/src/session-canvas/lab/canvasLabStore.test.ts` returned `716`.
- `git diff main..origin/spaces/slice6-www-canvas -- www/src/session-canvas/lab/canvasLabStore.test.ts` shows three PR additions in that file.
- fmm outline shows the file at 716 LOC, with large test groups such as `describe canvasLabStore captured runs` at lines 187 to 445.

Recommended fix: split the canvas lab store tests by behavior, such as terminal, captured run, framing, close, expand, and fit to content, then keep each file below 700 LOC before reapplying the worktree ref fixture additions.

### Major: `select-worktree` corrupts URLs when current canvas already has query params

`www/src/session-canvas/components/CanvasSurface.tsx` lines 111 to 116 build a full path with query params and pass it to `navigateToRoute`:

- Reads current `window.location.search`
- Sets `space_id` and `worktree_id`
- Calls `navigateToRoute(`${window.location.pathname}?${params.toString()}`)`

`www/src/session-canvas/components/RouteSwitcher.tsx` lines 47 to 50 define `navigateToRoute(path)` as a path only helper. It appends the existing query string with `window.location.assign(`${path}${window.location.search}`)`.

Failure mode:

1. Current URL is `/canvas?space_id=s&worktree_id=old`.
2. User selects a new worktree.
3. `CanvasSurface` passes `/canvas?space_id=s&worktree_id=new` to `navigateToRoute`.
4. `navigateToRoute` appends the old query, producing `/canvas?space_id=s&worktree_id=new?space_id=s&worktree_id=old`.
5. On reload, `parseCanvasLaunchContext` reads a corrupted `worktree_id` value.
6. The canvas `defaultWorktreeId` can become invalid, so subsequent captured run spawns target the wrong worktree id.

Recommended fix: either add a separate helper for full URL assignment or make the `select-worktree` case update location directly with a properly constructed URL. Preserve `navigateToRoute` as path only unless all callers are adjusted and tested. Add a regression that starts with an existing `/canvas?...` query, selects a worktree, and asserts the assigned URL has exactly one `?` and the new `worktree_id` value.

### Delta re-review at 093d1ab: resolved and signed off

Follow-up request reviewed only the fix delta from `3e27c2c` to `origin/spaces/slice6-www-canvas@093d1ab39b87392b6a9ad0966a1b00dd7085c6fb`. The worktree was pristine before and after review.

Resolution evidence:

- LOC blocker resolved: `www/src/session-canvas/lab/canvasLabStore.test.ts` is now 445 LOC and `www/src/session-canvas/lab/canvasLabStore.capturedRuns.test.ts` is 275 LOC; a script over all changed delta files returned `over_700=[]`.
- Worktree switch URL bug resolved: `www/src/session-canvas/components/CanvasSurface.tsx:119-135` now uses `window.history.replaceState` with `worktreeSwitchUrl(...)` instead of passing a query-bearing path to `navigateToRoute`.
- `www/src/session-canvas/route.ts:52-64` defines `worktreeSwitchUrl`, which sets `space_id` and `worktree_id`, deletes `canvas_id`, and returns a single clean query string.
- `www/src/session-canvas/route.test.ts:102-128` regresses the single `?` behavior and verifies `parseCanvasLaunchContext` reads clean `spaceId` and `worktreeId`.
- Focused verification: `cd www && pnpm vitest run src/session-canvas/route.test.ts src/session-canvas/lab/canvasLabStore.test.ts src/session-canvas/lab/canvasLabStore.capturedRuns.test.ts` passed, 3 files and 47 tests.

Bus verdict sent to `transport-matters:general:1:4.1`: `review: clean ... I sign off on PR#166 Slice 6 as currently filed`.

## Dependencies

Critical dependencies touched by the review:

- `zustand` persist middleware for canvas and captured run state.
- `@tanstack/react-query` for Space listing via `useSpaces`.
- Browser `localStorage` for per canvas cache and legacy import.
- FastAPI backend DTOs from `api/src/transport_matters/api/v1/space_routes.py` and `api/src/transport_matters/api/v1/run_routes.py`, serialized in camelCase.

## Relevance to Helioy

These findings protect the Spaces migration boundary. The URL bug would make worktree rooted runs unreliable in the browser canvas, and the LOC violation bypasses the repo level maintainability guard that keeps future autonomous work tractable.

## Open Questions

- After fixes land, rerun the same review against the new head and confirm the branch remains pristine before any sign off.
- Verify whether `listRuns` query params in `www/src/api.ts` should use camelCase `spaceId` and `worktreeId` for consistency with the backend aliases. This was not included in the one sentence verdict because the primary current blockers were sufficient to withhold sign off.
