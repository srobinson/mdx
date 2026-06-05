---
title: Transport Matters www/ separation Phase 2 — sever canvas→inspector leaks
type: sessions
tags: [frontend, transport-matters, separation, canvas, ark-ui, bem, boundary]
summary: Built ArkExchangeViewer (canvas-owned, read-only, Ark+BEM), extracted lib/contentBlocks, flipped the import boundary to zero canvas→inspector; PR#187
status: active
source: frontend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

# Summary

Executed Phase 2 of the www/ separation plan v5 on `sep/p2-sever` (30f8dd9, PR#187, base 37b16bf). Both canvas→inspector leaks are severed: `ProviderExchangeResourceViewer → components/ExchangeDetail` and `TranscriptMessage → components/detail/ContentBlocks`. The boundary test now enforces zero cross-imports instead of pinning known breaches. Gates `just check && just test` green from repo root.

# Architecture Decisions

- **Replace, do not wrap.** `ProviderExchangeResourceViewer` was a 48-line wrapper around `ExchangeDetail` plus a `toDetailTab` mapping. `ArkExchangeViewer` replaces it outright; `registry.tsx` and `ResourcePane.tsx` render it directly. No forwarding shim left behind.
- **Fork presentation, share data.** The viewer reuses everything outside `components/`: `fetchExchange`, `exchangeKey`, `useMeta`, `lib/formatting`, `lib/contentBlocks`, and canvas primitives (`JsonTree`, `CopyButton`, `TranscriptBlock` — newly exported). Presentation (header, Ark tabs with readouts, panels, telemetry chips) is a deliberate fork per the locked decision.
- **Placement.** Viewer lives in `session-canvas/viewers/resource/` so the cssColocation guard covers its stylesheet; `exchange-viewer.css` was rewritten as the viewer's full BEM sheet.
- **Fullscreen preserved.** The desktop Escape-order contract (palette → dock → fullscreen) clicks "Open inspect fullscreen" on the exchange pane. Fullscreen is a view affordance, not an editor one; kept it as a BEM overlay driven by `hooks/useFullscreen` (canvas-side keybinding engine). Omitted: editor sections, override diffing, export, Edited marker, store imports.
- **contentBlocks single path.** `blockKey`/`blockSummary` moved to `lib/contentBlocks.ts`; all five importers repointed, no re-export kept, so P4's core move is a one-line path rewrite.

# Performance Notes

No sync-path weight added: the viewer ships in the canvas graph that already loads `@ark-ui/react`; no new dependencies.

# Deviations from Spec

- Brief said "repoint TranscriptMessage + ContentBlocks"; I also repointed InspectTab, MessagesSection, BlockRow (they imported the same symbols from ContentBlocks) to keep one import path — spec-consistent (helpers are core-bound in P4).
- Brief's read-only bar ("no editor, no breakpoint affordances") was initially read as "no fullscreen"; the Escape-order e2e proved fullscreen is part of the pane's working contract. Kept, with test coverage.

# Fix Round 1 (9f141b2)

Review found 2 Major, both inspect-panel content gaps, fixed TDD (3 RED then 24/24 GREEN):

- Curated precedence: inspect panel now renders `request_curated_ir ?? request_ir` so mutated exchanges show the payload as sent, matching the request tab, with a visible curated note in place of the inspector's override-diff treatment.
- `codex_derived_artifacts` now renders as a `DerivedArtifactsSection` (operator warnings for missing, repaired, migrated, inconsistent timelines) with the inspector's exact visibility rule; `DiagnosticRow` generalized to a structural `DiagnosticLike` shared by transport and derived-artifacts diagnostics.

# Open Items

- Visual snapshots are darwin-only local gates (CI runs no `--project=visual`); baseline regenerates with `pnpm test:visual:update`.
- Transport tab renders diagnostics + raw JSON for codex frames (content parity); a richer canvas frames list is possible polish later.
- The session-picker pane logs a "Query data cannot be undefined" console error under the canned `/v1/sessions` mock (pre-existing in the e2e fixtures, unrelated to this change).
