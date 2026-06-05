---
title: Transport Matters www separation Phase 1 groom
type: sessions
tags: [frontend, transport-matters, separation, www]
summary: Implemented and review-hardened the Phase 1 grooming slice for the Transport Matters www separation plan.
status: active
source: frontend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

## Summary

Implemented Phase 1 grooming from `~/.mdx/projects/tm-sep-proposal.md` v5 on branch `sep/p1-groom` and opened PR #186. The initial implementation landed at `4bb3f90`; review round 1 fixes landed at `c49bb1b`.

The slice renames the legacy inspector route, moves desktop host chrome out of `RootShell`, scopes theme token mounting to canvas routes, unifies repeated canvas store transition logic, deduplicates inspector local state helpers and audit mutation detection, removes dead keybinding formatting code, prunes stale CSS, and adds an import graph boundary test for the two current session canvas to inspector breaches.

Review round 1 restored the server-provided channel badge color without Tailwind token coupling, switched theme token application to a pre-paint layout effect, made dock close removal functional after lifecycle hooks, fixed stop sequence sync keys, hardened import graph resolution, trimmed desktop bridge exports, added close-disabled coverage, added chrome unmount and query cache cleanup, and completed the `isRecord` dedup.

## Architecture Decisions

- `RootShell` now only selects route components and uses a neutral suspense fallback. Desktop drag chrome and the channel badge are mounted through `host/mountWindowChrome()`.
- `useThemeTokens()` is mounted by `SessionCanvasRoute` and `CanvasLabRoute`, not by the shared root shell. It now uses `useLayoutEffect` so canvas theme tokens apply before the first painted canvas frame.
- `desktopHost.ts` exposes only host detection and dropped file path resolver helpers used by production code. The raw bridge accessor and test-only path helper are private or removed.
- `paneAffordances.ts` centralizes shared dock close policy. It owns the `closeDisabled` guard and commits removal through functional store updates after lifecycle hooks run.
- `useSyncedLocalValue()` centralizes the synced local override pattern used by sampling, thinking, and editable override hooks. Sampling stop sequences pass a JSON sync key so distinct arrays with the same joined display text still reset local edits.
- `testSupport/importGraph.ts` holds shared import graph test plumbing, local import resolution, test support filtering, source parse memoization, and dirent-backed file walking.

## Performance Notes

No runtime performance optimization was targeted. The split reduces inspector route startup side effects by avoiding canvas theme token writes from `RootShell`. The import graph test helper now memoizes parsed source and import lists, reducing repeated AST work during boundary tests.

## Deviations from Spec

No intentional deviations. The existing consensus document was marked stale outside the repo at `~/.mdx/projects/tm-ui-sep-consensus.md`.

## Open Items

- The new session canvas boundary test intentionally pins the two existing inspector imports as known breaches for a later separation phase.
- `just check` still reports the pre-existing biome warnings for `pane-dock.css` and `commandModel.test.ts` while exiting successfully.

## Verification

- `pnpm --dir www exec vitest run src/host/ChannelBadge.test.tsx src/host/mountWindowChrome.test.tsx src/hooks/useThemeTokens.test.tsx src/rootShell.test.tsx src/session-canvas/model/paneAffordances.test.ts src/session-canvas/model/canvasStore.test.ts src/session-canvas/lab/canvasLabStore.capturedRuns.test.ts src/components/editor/SamplingSection.render.test.tsx src/session-canvas/importGraphBoundary.test.ts src/session-canvas/labBoundary.test.ts src/desktopHost.test.ts src/components/detail/mutations.test.ts src/session-canvas/lab/canvasLabStore.persistence.test.ts`
- `pnpm --dir www exec tsc -b`
- `just check`
- `just test`
- `git diff --check`
- `fmm generate && fmm validate`
