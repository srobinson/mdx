---
title: Transcript Canvas Slice 8 — Real Resource Viewers (frontend)
type: sessions
tags: [frontend, transport-matters, transcript-canvas, react, viewers, xss, react-query]
summary: Replaced slice-5 placeholder shells with 6 real resource viewers consuming the slice-7 resource-content endpoint; dependency-free XSS-safe markdown; ExchangeDetail decoupled from legacy route state.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Summary

Slice 8 of the Transport Matters transcript canvas (PR #58, branch `feat/transcript-canvas-slice-8`, sha `b0368a7`). Wired the placeholder resource pane state machine to a real fetch of `GET /api/sessions/{id}/resources/{rid}` and built real viewers for the `ResourceContentResponse` union. Built via hybrid orchestration: foundation/contract solo, 4 mechanical viewers fanned out to parallel subagents, markdown + exchange kept under direct control, then an adversarial Codex peer review.

## Architecture Decisions

- **6 viewer files, not 8.** The backend union has 6 discriminable `kind`s (`text|image|binary|json|exchange-redirect|missing`). The spec's 8 UX viewers collapse: `tool-output` has no backend discriminator (it is `text`/`json` + copy controls); `native-record` is `json` + a `native-record` provenance label. Shared primitives (`JsonTree`, `CodeText`, `CopyButton`) keep both DRY. Selection lives in a pure `resolveResourceContent()` (`resourceState.ts`), unit-tested in isolation.
- **ResourcePane orchestrator.** Fetches via a `useResourceContent` react-query hook, then renders either a stable `ResourcePaneState` (loading/missing/too-large/...) or a viewer. Viewers are pure prop components (`{ content }`), so their tests need no query provider; the fetch/state logic is tested once at the pane level.
- **Missing-reason mapping.** 7 backend reasons → 8 existing pane states. Reasons without a dedicated state (`uncorrelated`) reuse `missing` and render the backend `message` via a new optional `messageOverride` on `ResourcePaneStateView` (refactored `StateBody` to an `errorContent` map). Never a generic toast.
- **XSS-safe markdown, dependency-free.** Hand-rolled `renderMarkdown` builds React elements only — never `dangerouslySetInnerHTML`, never an HTML string. Raw HTML in source becomes escaped React text (inert by construction). `safeHref` allow-lists `http/https/mailto/tel`, rejects control chars and dangerous schemes. Codebase invariant preserved: zero `dangerouslySetInnerHTML`.
- **Exchange decouple (acceptance 7).** `ExchangeDetail` gained optional `onMissing` (default preserves the legacy `uiStore.setSelectedId(null)`) + `initialTab`. Single prod call-site (`routeLayout.tsx`) and existing tests untouched; the canvas passes a no-op so a reused exchange pane never mutates legacy route state. `initialView`→tab mapping in the viewer.
- **Provenance.** Aligned `provenance.tsx` `ProvenanceKind` to the backend's 6 canonical strings (`raw-bytes`→`raw-provider-debug`) and made it an alias of the API type, removing a duplicate union.
- **CSS.** Co-located per viewer, imported centrally in `main.tsx` (slice-5 convention). Zero `index.css` diff (asserted).

## Performance Notes

No perf regression work. Build clean (`vite build` ~180ms, 645 modules). react-query dedupes the resource fetch per pane; viewers are not lazy (small).

## Deviations from Spec

- **Wire is camelCase, not snake_case.** My initial spec-correction claimed snake_case (from reading the Pydantic field names). WRONG: the response models extend `TimelineModel` (`alias_generator=_to_camel`), so the endpoint serializes camelCase (`mediaType`, `tooLarge`, `exchangeId`, ...), confirmed by `test_session_resource_content.py`. A Codex peer review caught this as a BLOCKER (snake_case types would read `undefined` at runtime; tests passed only because fixtures matched the wrong types). Fixed to camelCase across types + viewers + fixtures. The spec's *original* camelCase union was correct.
- `subagent-timeline` stays on the placeholder (not in the slice-8 viewer list).

## Open Items

- Evidence drawer (acceptance 9) and projection persistence (slice 9) are out of scope.
- Markdown renderer is a deliberate CommonMark *subset* (no tables, nested lists, reference links, autolinks). Sufficient for transcript content; revisit if richer docs appear.
- Image viewer pans a zoomed image via scroll; no drag-pan yet.
