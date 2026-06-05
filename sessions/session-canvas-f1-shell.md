---
title: Session Canvas F1 Shell Implementation
type: sessions
tags: [frontend, transport-matters, session-canvas, f1]
summary: Implemented the F1 session canvas route and folded PR review fixes for API fallback, transcript mapping, SSE gap backfill, and stress measurement.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the F1 session canvas shell in the isolated `canvas-f1` worktree and folded the PR review fixes. The `/canvas` route lazy loads as the desktop entry while legacy `/` remains available. The canvas includes a content agnostic DOM layout engine, floating pane chrome, session picker, launched run auto resolver, transcript backlog and SSE stream handling, IR to chat mapping, and a measured stress harness at `/canvas?stress=1`.

Review fixes added after PR feedback:

- `SpaStaticFiles` now keeps unknown `/api/*` paths as JSON 404 responses and still serves SPA fallback for non API, non asset paths.
- Transcript meta events now render a metadata lane item from event fields instead of being dropped when `ir` is null.
- Turn events with empty `parts` now render `search_text` when available.
- The extractor contract is now exposed as `mapSessionEventToChatItems`.
- SSE live gaps now request bounded backfill, merge missing events, and clear the gap marker after the reducer has a contiguous sequence.
- The stress route now wires `FrameMeter` around spawn, close, focus, drag, resize, pan, and zoom operations, with a Playwright perf spec.

## Architecture Decisions

- Added `www/src/engine/**` as a reusable layout engine boundary. It owns `PaneNode`, viewport state, pan, zoom, motion envelope, and frame level move or resize behavior. It does not import session, transcript, wire, or viewer modules.
- Added `www/src/session-canvas/**` as the feature boundary. It owns `PaneRecord`, viewer registry, Zustand canvas state, launch resolution, session API hooks, transcript reducer, and viewer implementations.
- Kept `PaneNode` geometry only and joined it to `PaneRecord` inside `CanvasSurface`, outside the engine.
- Used TanStack Query for session list and transcript backlog. UI state remains in the canvas store.
- Implemented one EventSource per transcript pane. Reconnect closes the old source and reopens with `last_seq` from the highest observed event. Gap handling performs a bounded `from_seq` to `to_seq` backfill before appending the skipped live event.
- Added route level code splitting in `www/src/main.tsx` so the canvas and legacy app load as separate chunks.
- Added FastAPI SPA fallback through `SpaStaticFiles` so `/canvas` hard loads resolve to `index.html` without masking missing asset, or API paths.
- Updated desktop renderer URL helpers and tests so hosted desktop loads `/canvas` by default.

## Performance Notes

Verification build was run to a temp out dir during the initial F1 pass:

```text
pnpm exec vite build --outDir /tmp/tm-canvas-f1-build --emptyOutDir
```

Largest gzipped chunk after route splitting was `app-xjSRIMzp.js` at 106.65 kB. The session canvas route chunk was 53.33 kB gzip. The temp build completed successfully.

The stress harness now records frame deltas through `FrameMeter` and exposes the last action, frame count, p95 frame, and max frame on the route. Pane frames also use CSS containment and `will-change` to reduce layout and paint cost during motion.

Verified gates after the review fixes:

```text
cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci
# 1146 passed in 16.05s

cd www && pnpm lint && pnpm typecheck && pnpm test
# 61 files passed, 407 tests passed

cd www && pnpm exec playwright test --project=perf
# 1 passed
```

## Deviations from Spec

- The in app Browser connector was unavailable during the initial F1 pass, so route verification used local headless Playwright.
- The perf spec uses a bounded CI threshold for p95 frame delta rather than the local ideal target. The route still reports actual p95 and max frame values for local inspection.
- Transcript thinking expansion is collapsed by default through native `details`. Persisting per block expansion in shared UI state remains a small F2 hardening item.

## Open Items

- F2 should add full tiling mode, focus rails, resize keyboard semantics, and persistence decisions.
- F2 should decide whether to promote stress results into a persisted CI artifact.
- Merge reconciliation is expected for `desktop/src/*` because the CLI track touches the same desktop seam on a separate branch.
