---
title: Transcript Canvas Slice 5 — Placeholder Panes
type: sessions
tags: [frontend, transport-matters, transcript-canvas, slice-5, react, css-colocation]
summary: Real placeholder panes for the 3 new PaneContentRef kinds, 8-state + provenance scaffold, co-located CSS, zero index.css diff.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Summary

Slice 5 of the transcript-canvas UI. Replaced the minimal slice-3 `PlaceholderPane`
stub with real placeholder components for the three new `PaneContentRef` kinds:
`subagent-timeline`, `resource`, `provider-exchange`. Stable shells only — no real
viewers (slice 8), no resource content endpoint/fetching (slices 6-7), no backend.

Branch `feat/transcript-canvas-slice-5`, sha `a45b928`, PR #54. www gate green
(lint, typecheck, test 476/476, build). Zero `index.css` diff.

## Architecture Decisions

- **Three modules, one parameterized pane.** `provenance.tsx` (six provenance kinds
  + label map + `<ProvenanceLabel>`), `paneState.tsx` (8-state union + shared
  `<PaneStateFrame>` + `<ResourcePaneStateView>`), `PlaceholderPane.tsx` (ref→identity
  derivation + the registry-rendered component). One `PlaceholderPane` switches over
  ref kind rather than three near-duplicate components (DRY).
- **Shared shell preserves provenance + actions.** `PaneStateFrame` always renders
  the provenance label and the actions bar, and sets `role="alert"` for error-tone
  states and `aria-busy` for loading. This is the structural guarantee that pane
  errors never collapse into generic toasts (spec "Resource Pane States" L205-206).
- **`ready` uses a children slot.** The 8-state view carries no content payload for
  `ready`; slices 6-8 pass real viewer content as `children`. Keeps the scaffold free
  of premature content modeling (YAGNI).
- **Registry keeps title/size/dedupe.** Per slice 3, the viewer registry owns pane id,
  title, and default rect. `PlaceholderPane` consumes `pane.title`; it does not
  recompute titles.
- **provider-exchange shell-only, proven by test.** Its test renders without a
  `QueryClientProvider`; a placeholder that queried exchange detail or coupled to
  legacy route state would throw. That is the regression guard for spec L189-190.
- **CSS co-location.** Per the locked slice-5 decision, new pane CSS lives in a
  co-located `placeholder-pane.css` imported once in `main.tsx` (mirrors the
  `canvas.css` extraction). Chose a new file over growing `canvas.css` (508 LOC, near
  the 700-line refactor threshold) so the resource-pane feature line (slices 6-8) has
  its own home. `index.css` untouched — any diff there is a slice blocker.

## Performance Notes

No optimization work. Scaffold is static render, no fetching. Build output unchanged
in shape; new placeholder code rides in the SessionCanvasRoute chunk.

## Deviations from Spec

None. The `ready` state holding no payload (content via `children`) is an
implementation detail consistent with "slices 6-8 fill content."

The "assert ZERO index.css diff" test requirement is satisfied as a git-level
invariant (`git diff --stat -- src/index.css` empty) rather than a vitest test, since
a unit test reading a sibling stylesheet would be brittle. Verified in the gate.

## Open Items

- Slices 6-7: resource content endpoint → map response to `ResourcePaneState`; wire
  `PaneAction.onActivate` handlers (retry, load preview, open externally, reveal path).
- Slice 8: real viewers render through `ResourcePaneStateView`'s `ready` children slot;
  set provenance from the resolver instead of the per-kind default in
  `placeholderProvenance`.
- Provenance defaults in `placeholderProvenance` are scaffold guesses
  (subagent→native-record, resource→captured, exchange→structured-wire); slices 6-8
  should drive provenance from real resolver data.
