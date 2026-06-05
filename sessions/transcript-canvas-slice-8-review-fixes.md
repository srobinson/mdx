---
title: Transcript Canvas Slice 8 — Peer-Consensus Review Fix Round
type: sessions
tags: [frontend, transport-matters, transcript-canvas, slice-8, pr-58, vite, css, dry]
summary: Resolved PR#58 slice-8 review findings — recurrence-proof co-located viewer CSS, shared safeHref on binary href, deduped truncation note.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Three-item fix round on PR#58 (`feat/transcript-canvas-slice-8`), driven by the
peer-consensus review (`review-slice-8.md`, reviewers Claude `:5.2` + Codex
`:5.3`). Landed at commit `648deb4` (parent `b0368a7`). Each fix is backed by a
test that failed on the pre-fix state (RED) and passes after (GREEN). Full gate
green: `pnpm lint && pnpm typecheck && pnpm test && pnpm build` (537 tests, +11).

- **M1 (Major)** — `exchange-viewer.css` was authored but imported nowhere, so
  the exchange pane shipped unstyled and every gate stayed green.
- **m1 (Minor)** — binary download href skipped the scheme allowlist.
- **m2 (Minor)** — the truncation-note string was duplicated across viewers.

## Architecture Decisions

### M1 — recurrence-proof CSS co-location (not just the one import)

The review's minimal fix was "add the missing import to main.tsx." Rejected that
in favor of the orchestrator's preferred recurrence-proof shape, because
centralizing per-viewer CSS in `main.tsx` makes "forgot to wire the stylesheet"
a recurring, gate-invisible failure mode.

- Each resource viewer imports its **own** co-located CSS at the top of its
  component file (`BinaryResourceViewer.tsx → import "./binary-viewer.css"`, etc.).
- Shared primitive styles imported by the primitives that render them: `CodeText`,
  `CopyButton`, `JsonTree` each `import "./resource-primitives.css"` (Vite dedupes
  to one bundle entry).
- Removed all 6 per-viewer/primitive CSS imports from `main.tsx`; it now keeps
  only app-global CSS (`index.css`, `canvas.css`, `placeholder-pane.css`).
- New guard test `cssColocation.test.ts` scans `viewers/resource/**/*.css` and
  asserts each is imported by a co-located (`.ts/.tsx`, non-test) sibling. It
  fails for all 7 stylesheets on `b0368a7` (RED), passes after the fix.

Net property: a viewer cannot render without its styles in the module graph, so
the class of bug is structurally eliminated, not just patched once.

### m1 — shared `safeHref`

`safeHref` (scheme allowlist: http/https/mailto/tel, rejects control chars) lived
inside `markdown.tsx`. It gained a second, unrelated consumer (the binary
download action), which is the trigger to promote a helper to a shared home.
Extracted it verbatim into `primitives/safeHref.ts`; `markdown.tsx` and
`BinaryResourceViewer.tsx` both import it; updated `markdown.test.tsx`'s import.
`BinaryResourceViewer` now computes `safeHref(content.downloadUrl)` and degrades
an unsafe/missing URL to the existing disabled-button affordance.

### m2 — shared `TruncationNote`

Extracted the duplicated note into `primitives/TruncationNote.tsx`: a
`TRUNCATION_NOTE` constant (canonical wording) plus a `TruncationNote` component
taking `className` (viewers style with their own co-located class) and an
optional `message` (markdown overrides it to "source truncated"). Used by the
text/json/markdown viewers.

## Performance Notes

No perf work. One incidental bundle improvement: because viewer CSS moved from
the entry (`main.tsx`) to component modules in the lazily-loaded canvas chunk,
the viewer styles now emit into the route chunk CSS (`SessionCanvasRoute-*.css`)
instead of `index-*.css`. They are route-scoped, no longer loaded on the legacy
`app` route. Bundle-level proof of the M1 fix: `canvas-exchange` occurrences in
the built CSS went 0 → 1; `canvas-binary ×7` and `canvas-md__ ×21` preserved.

## Deviations from Spec

None. The orchestrator offered a preferred path (co-locate) and an acceptable
alternative (keep main.tsx + guard test); implemented the preferred path, which
also satisfies the alternative's guard-test requirement. The `safeHref`
extraction (touching `markdown.tsx` + `markdown.test.tsx`) is slightly beyond the
literal 3-file scope but is the DRY-correct way to share one guard between two
viewers; behavior unchanged (markdown safeHref tests still pass from the new import path).

## Open Items

- None blocking. The "Noted, not pressed" item in the review (`resourceState.ts:74`
  passing the backend message for all missing reasons) was explicitly out of scope
  and left as-is pending confirmation it is intentional enrichment.
