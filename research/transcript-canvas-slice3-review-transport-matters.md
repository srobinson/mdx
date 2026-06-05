---
title: Transcript Canvas Slice 3 Review for Transport Matters
type: research
tags: [transport-matters, session-canvas, code-review, helioy-bus, react, typescript]
summary: PR #52 slice 3 mostly implements registry owned pane dedupe, but leaves PaneContentRef wider than the four kind spec contract.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Executive Summary

PR #52, branch `feat/transcript-canvas-slice-3`, was reviewed at head `0a8049a65745a8940942bbf80f1279828256e154` against `NOTES/transcript-canvas-ui-frontend.md`. The implementation moves pane id, size, renderer selection, shell, and default titles into the viewer registry, but the exported frontend `PaneContentRef` still includes the internal `session-picker` kind, which conflicts with the slice 3 four kind transcript content contract.

## Project Metadata

- Language: TypeScript and React in `www/`.
- Framework and build: Vite, React, TypeScript project references.
- Test runner: Vitest.
- Tooling: Biome lint, `pnpm` scripts.
- fmm status: fmm index was available and used for file topology, outlines, symbol reads, and dependency context.
- Verified commands:
  - `cd www && pnpm lint`: 230 files checked, exit 0.
  - `cd www && pnpm typecheck`: exit 0.
  - `cd www && pnpm test`: 70 files passed, 461 tests passed, exit 0.
  - `cd www && pnpm build`: exit 0.

## Architecture

Slice 3 expands the session canvas pane model and centralizes viewer responsibilities:

- `www/src/session-canvas/model/paneRecords.ts:28-46` defines `PaneContentRef`.
- `www/src/session-canvas/model/paneRecords.ts:90-98` defines `ViewerRegistration`, including `paneId`, `title`, `defaultRect`, and `render`.
- `www/src/session-canvas/viewers/registry.tsx:70-100` registers session picker, transcript chat, and placeholder viewers.
- `www/src/session-canvas/viewers/registry.tsx:115-135` exports registry owned `paneIdForRef`, `titleForRef`, `rectForRef`, `viewerIdForRef`, and `renderPaneContent`.
- `www/src/session-canvas/model/canvasStore.ts:98-108` normalizes spawn refs, dedupes through the registry pane id, and focuses existing panes.
- `www/src/session-canvas/model/spawn.ts:14-19` maps the legacy `{ kind: "session" }` ref to `{ kind: "session-timeline" }`.

Data flow is now: spawn request, legacy normalization, registry pane id lookup, existing pane check, registry title and default rect, pane record creation, then registry selected rendering through `CanvasSurface` at `www/src/session-canvas/components/CanvasSurface.tsx:33-59`.

## Key Patterns

- Registry owned dedupe uses pane id as the dedupe key, which matches the spec direction at `NOTES/transcript-canvas-ui-frontend.md:61-71`.
- Legacy ref compatibility is constrained to the spawn boundary through `SpawnablePaneRef` at `www/src/session-canvas/model/paneRecords.ts:52-55` and `normalizeRef` at `www/src/session-canvas/model/spawn.ts:14-19`.
- Placeholder rendering is minimal glue for slice 3. `www/src/session-canvas/viewers/placeholder/PlaceholderPane.tsx:13-20` lets new pane kinds resolve through the registry without pulling full slice 4 resource, subagent, or provider exchange viewers forward.

## Detailed Findings

### Major: PaneContentRef is wider than the spec contract

The spec defines exactly four `PaneContentRef` kinds at `NOTES/transcript-canvas-ui-frontend.md:50-54`: `session-timeline`, `subagent-timeline`, `resource`, and `provider-exchange`. The implementation includes those four but also keeps `{ kind: "session-picker"; owner: "local" }` in the exported `PaneContentRef` at `www/src/session-canvas/model/paneRecords.ts:28-30`.

The registry also treats `session-picker` as a `PaneContentRef` viewer registration at `www/src/session-canvas/viewers/registry.tsx:70-79`, and the registry test includes it as a `PaneContentRef` case at `www/src/session-canvas/viewers/registry.test.ts:7-9`. That leaves the public content ref contract wider than the slice 3 spec. The cleaner shape is to split the internal picker ref from the four item transcript content refs, then compose them only where the canvas needs the session picker.

### Minor: duplicate open focus test is vacuous

The implementation correctly focuses an existing pane when a duplicate ref is opened at `www/src/session-canvas/model/canvasStore.ts:101-104`. The test at `www/src/session-canvas/model/canvasStore.test.ts:41-50` opens the same resource twice, but never moves focus away after the first open. Because the first open already focuses `resource:abc:r1`, the test would still pass if the duplicate path stopped calling `focusPane`. A stronger test should focus the picker, or open another pane, before reopening the resource.

### Delta verification at 51aff70

The fix round at `51aff705d910835d70af24e5d5181b38690d8401` resolves both prior findings. `PaneContentRef` is now exactly the four transcript content kinds at `www/src/session-canvas/model/paneRecords.ts:28-45`, while `PickerPaneRef` and `CanvasPaneRef` split session picker chrome out of transcript content at `www/src/session-canvas/model/paneRecords.ts:48-51`. The registry now resolves `CanvasPaneRef`, so the picker remains renderable through `www/src/session-canvas/viewers/registry.tsx:109-118`.

The new contract test pins the shape: `www/src/session-canvas/model/paneRecords.contract.test.ts:9-17` asserts the four kind union and excludes `session-picker`, while `www/src/session-canvas/model/paneRecords.contract.test.ts:19-22` verifies the picker remains part of `CanvasPaneRef`. The dedupe focus test now moves focus away at `www/src/session-canvas/model/canvasStore.test.ts:46-50` before reopening the resource at `www/src/session-canvas/model/canvasStore.test.ts:52-56`, so it would fail if the duplicate path stopped refocusing the existing pane.

Delta verification commands observed:

- `git diff 0a8049a 51aff70` for the fix round.
- `cd www && pnpm typecheck`: exit 0.
- `cd www && pnpm test -- src/session-canvas/model/paneRecords.contract.test.ts src/session-canvas/model/canvasStore.test.ts src/session-canvas/viewers/registry.test.ts`: 71 files passed, 464 tests passed, exit 0.
- Final PR head check: `51aff705d910835d70af24e5d5181b38690d8401`.

## Dependencies

- `zustand` backs the canvas store in `www/src/session-canvas/model/canvasStore.ts`.
- React provides viewer rendering in `www/src/session-canvas/viewers/registry.tsx` and pane components.
- Vitest tests cover store behavior, normalization, registry ids, and transcript chat rendering.
- Existing canvas engine APIs provide pane ids, world rects, layout nodes, focus, and viewport updates.

## Relevance to Helioy

Transport Matters is the wire level observability and session history layer for Little Organs coding agents. The slice 3 architecture moves toward a reusable viewer registry that can support transcript, resource, subagent, and provider evidence panes with deterministic spatial memory. The remaining type boundary issue matters because Helioy canvas protocols need a precise content ref contract before later slices add real resource viewers and backend resource refs.

## Open Questions

- Should `session-picker` become a separate `CanvasInternalPaneRef`, with `PaneRecord` storing a composed canvas ref type while transcript opening APIs expose only the four spec refs?
- Should `spawnPane` keep a title override, or should session summary title resolution move into a registry aware title adapter to satisfy registry ownership more strictly?
