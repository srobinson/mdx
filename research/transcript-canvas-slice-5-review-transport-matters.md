---
title: Transcript Canvas Slice 5 Review for Transport Matters
type: research
tags: [transport-matters, transcript-canvas, pr-54, code-review, frontend]
summary: PR #54 implements placeholder panes but misses the subagent title field required by the accepted SubagentRef contract.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Executive Summary

PR #54 (`feat/transcript-canvas-slice-5`, head `a45b928ce42b8df84ad1aa05c58d3dd03206de7a`) adds placeholder panes for resource, subagent timeline, and provider exchange refs. The implementation is mostly within the requested frontend slice, but review found one blocker: the frontend subagent ref omits `title`, so placeholder panes cannot carry the accepted child session title from the timeline contract.

## Project Metadata

- Project: `transport-matters`
- Area: `www/src/session-canvas`
- Language: TypeScript and React
- Build system: `pnpm`, `tsc -b`, Vite, Vitest, Biome
- fmm status: indexed. `fmm_list_files` reported 550 files and 86,996 LOC across `api/`, `www/`, and `desktop/`.
- PR: #54, branch `feat/transcript-canvas-slice-5`

## Architecture

Slice 5 extends the session canvas viewer registry rather than wiring real content fetchers. The registry owns placeholder pane ids, titles, viewer selection, and default rectangles in `www/src/session-canvas/viewers/registry.tsx:50-99`. The placeholder renderer consumes `PaneContentRef` through `PlaceholderPaneRef` in `www/src/session-canvas/viewers/placeholder/PlaceholderPane.tsx:5-9`, renders a registry supplied pane title via `pane.title`, and displays ref identity rows in `www/src/session-canvas/viewers/placeholder/PlaceholderPane.tsx:76-108`.

Resource pane states are scaffolded as a discriminated union in `www/src/session-canvas/viewers/placeholder/paneState.tsx:16-24`. `ResourcePaneStateView` wraps every state in `PaneStateFrame`, preserving provenance and action affordances in `www/src/session-canvas/viewers/placeholder/paneState.tsx:97-121`.

## Key Patterns

- Viewer registry stays the dedupe and title source. `PlaceholderPane` reads `pane.title` rather than computing a heading locally (`PlaceholderPane.tsx:80-82`).
- Placeholder panes avoid real data dependencies. Reviewed imports in `www/src/session-canvas/viewers/placeholder/*` are limited to React types, pane model types, pane state, and provenance.
- State errors are pane local UI, not toasts. `PaneStateFrame` always renders provenance plus optional actions before the state body (`paneState.tsx:80-91`).

## Detailed Findings

### Blocker: subagent pane refs omit `title`

The accepted SubagentRef contract includes `title` in both backend code and spec:

- `api/src/transport_matters/session/timeline_models.py:99-105`
- `NOTES/transcript-canvas-ui-backend.md:198-204`

The frontend pane ref omits the field:

- `www/src/session-canvas/model/paneRecords.ts:28-37`

The registry therefore fabricates a subagent title from the id:

- `www/src/session-canvas/viewers/registry.tsx:61-65`

The new tests also construct subagent refs without `title`:

- `www/src/session-canvas/viewers/placeholder/PlaceholderPane.test.tsx:32-40`
- `www/src/session-canvas/viewers/registry.test.ts:11-18`

Impact: real child session titles from the timeline payload cannot reach the canvas pane. This violates the review contract that the subagent placeholder reads the new `subagentId/sessionId/parentSessionId/parentSeq/title` shape.

Suggested fix: add `title: string` to the `subagent-timeline` branch of `PaneContentRef`, use it in registry title generation, and update placeholder plus registry tests to assert the title is carried from the ref.

### Clean checks

- Placeholder viewer covers `subagent-timeline`, `resource`, and `provider-exchange` in `www/src/session-canvas/viewers/registry.tsx:90-99`.
- Resource pane states cover loading, ready, missing, too large, binary unsupported, outside workspace, permission denied, and debug unavailable in `www/src/session-canvas/viewers/placeholder/paneState.tsx:16-24`.
- Provenance labels cover the six frontend spec labels in `www/src/session-canvas/viewers/placeholder/provenance.tsx:7-23`.
- Provider exchange placeholder does not import query clients, API helpers, route state, or exchange detail components.
- `www/src/index.css` has no diff relative to `main`.
- Reviewed frontend code paths contain no `virtual-sidechain` reference.

## Dependencies

Relevant frontend dependencies exercised by the changed code:

- React for component rendering and `ReactNode` types.
- Vitest and Testing Library for placeholder and state tests.
- Vite and TypeScript for build and type gates.
- Biome for linting.

## Relevance to Helioy

This review preserves the transcript canvas data contract between backend timeline projection and frontend pane refs. The title field matters because subagent panes are child session surfaces, not anonymous virtual sidechains, and the UI needs to carry the operator meaningful child session labels without inventing them from ids.

## Verification

- Read live `gh pr diff 54` and spec slices from `NOTES/transcript-canvas-ui-frontend.md:50-54`, `192-220`, and `276-281`.
- Ran `cd www && pnpm lint && pnpm typecheck && pnpm test`. Observed `Checked 236 files`, `73 passed (73)`, `476 passed (476)`, `EXIT=0`.
- Ran `cd www && pnpm build`. Observed `✓ built`, `EXIT=0`.
- Wrote actionable review findings to `review-slice-5.md`.
- Sent bus reply: `review done: 1 blockers 0 majors`.

## Open Questions

- Should `NOTES/transcript-canvas-ui-frontend.md:50-54` be updated to include `title` on the `subagent-timeline` `PaneContentRef`, matching the backend SubagentRef contract? The current review treated the backend contract and orchestrator instruction as authoritative.
